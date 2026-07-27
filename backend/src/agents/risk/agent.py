# ruff: noqa: E501
"""Real Risk Agent — 基于检索证据的风险分析

替代 MockRiskAgent，从 context.document_chunks 获取证据，基于真实文档分析风险。
Citation 必须来自提供的 chunks，不允许 LLM 凭空生成。
"""

import json

import structlog

from agents.base import BaseAgent, ToolDefinition
from domain.artifacts import ProcedureSuggestion, RiskFindingArtifact, RiskFindingContent
from domain.contracts import AgentRequest, AgentResponse, Citation
from infrastructure.llm.models import LLMMessage

logger = structlog.get_logger(__name__)

RISK_PROMPT = """You are an expert audit risk analyst. Analyze the following audit scenario and identify risks.

Audit Area: {audit_area}
Financial Data: {financial_data}

{document_section}

Return a JSON object with this exact structure:
{{
  "risks": [{{
    "area": "Risk area name",
    "title": "Risk title",
    "severity": "HIGH|MEDIUM|LOW",
    "probability": 0.0-1.0,
    "indicators": ["indicator1", "indicator2"],
    "related_standards": ["IFRS X.YY", "ISA Z.WW"],
    "reasoning": "Brief reasoning for this risk",
    "evidence_chunk_indices": [0, 2]
  }}]
}}

CRITICAL RULES:
1. evidence_chunk_indices must list the indices (0-based) of document excerpts above that support this risk.
2. If no excerpt supports the risk, set evidence_chunk_indices to [].
3. Do NOT invent document IDs, page numbers, or citation text. Only reference chunks by index.
4. Every risk MUST have at least one evidence_chunk_index unless the risk is purely hypothetical.
"""

RISK_NO_CHUNKS_PROMPT = """You are an expert audit risk analyst. Analyze the following audit scenario and identify risks.

Audit Area: {audit_area}
Financial Data: {financial_data}

Return a JSON object with this exact structure:
{{
  "risks": [{{
    "area": "Risk area name",
    "title": "Risk title (concise, one short phrase)",
    "severity": "HIGH|MEDIUM|LOW",
    "probability": 0.0-1.0,
    "indicators": ["indicator1", "indicator2"],
    "related_standards": ["IFRS X.YY", "ISA Z.WW"],
    "reasoning": "Brief reasoning for this risk"
  }}]
}}

Examples of good risk titles:
- "Premature Revenue Recognition" (not "The company might be recognizing revenue too early")
- "Related Party Transaction Pricing" (not "Issues with pricing of related party deals")
- "Inventory Obsolescence" (not "The inventory is getting old and might need to be written down")
- "Going Concern Uncertainty" (not "The company might not survive")
- "Goodwill Impairment" (not "The goodwill on the books might be overstated due to bad performance")

Keep titles short and standardized. 3-5 words maximum. Use standard audit terminology.
"""


class LlmRiskAgent(BaseAgent):
    name = "risk_agent"
    version = "1.0.0"

    def __init__(self):
        from infrastructure.llm.deepseek_provider import DeepSeekProvider
        self._llm = DeepSeekProvider()
        self._chunks_cache: list[dict] = []

    async def execute(self, request: AgentRequest) -> AgentResponse:
        audit_area = request.inputs.get("audit_area", "Revenue Recognition")
        financial_data = request.inputs.get("financial_data", {})
        document_chunks = request.context.get("document_chunks", [])

        if document_chunks and len(document_chunks) > 0:
            self._chunks_cache = document_chunks
            doc_section = "Document excerpts:\n\n" + "\n\n---\n\n".join(
                f"[{i}] (page={c.get('page','?')}) {c.get('content','')[:600]}"
                for i, c in enumerate(document_chunks)
            ) + "\n\nBase your risk analysis on these excerpts. Reference chunks by their index (0, 1, 2...)."
            prompt = RISK_PROMPT.format(
                audit_area=audit_area,
                financial_data=json.dumps(financial_data, ensure_ascii=False),
                document_section=doc_section,
            )
        else:
            prompt = RISK_NO_CHUNKS_PROMPT.format(
                audit_area=audit_area,
                financial_data=json.dumps(financial_data, ensure_ascii=False),
            )

        llm_response = await self._llm.generate([
            LLMMessage(role="system", content="You are an audit risk analyst. Return ONLY valid JSON."),
            LLMMessage(role="user", content=prompt),
        ])

        try:
            raw = json.loads(llm_response.content)
            risks = raw.get("risks", [raw])
        except (json.JSONDecodeError, AttributeError):
            risks = [{"area": audit_area, "title": "Analysis failed", "severity": "MEDIUM",
                      "probability": 0.5, "indicators": [], "related_standards": [], "reasoning": llm_response.content[:200]}]

        risk = risks[0] if risks else {"area": audit_area, "title": "Unknown", "severity": "LOW", "probability": 0.0}
        reasoning_raw = risk.get("reasoning", "")
        if isinstance(reasoning_raw, list):
            reasoning_text = " ".join(reasoning_raw)
            reasoning_list = reasoning_raw
        else:
            reasoning_text = reasoning_raw
            reasoning_list = [reasoning_raw]

        content = RiskFindingContent(
            area=risk.get("area", audit_area),
            title=risk.get("title", "审计风险"),
            severity=risk.get("severity", "MEDIUM"),
            probability=risk.get("probability", 0.5),
            indicators=risk.get("indicators", []),
            related_standards=risk.get("related_standards", []),
            suggested_procedures=[ProcedureSuggestion(type="Inspection", target=["documents"], steps=["审查相关文档"], evidence_required=["证据"])],
            reasoning=reasoning_list,
        )

        # 构建真实 Citation：从 chunks 索引映射回真实数据
        chunk_indices = risk.get("evidence_chunk_indices", [])
        citations = []
        for idx in chunk_indices:
            if isinstance(idx, int) and 0 <= idx < len(self._chunks_cache):
                chunk = self._chunks_cache[idx]
                citations.append(Citation(
                    claim=content.title,
                    document_id=chunk.get("document_id", chunk.get("source_id", "unknown")),
                    page=chunk.get("page"),
                    chunk_id=chunk.get("chunk_id"),
                    excerpt=chunk.get("content", "")[:200],
                    confidence=chunk.get("score", 0.5),
                ))

        artifact = RiskFindingArtifact(
            artifact_id=f"risk_{request.workflow_id[:8]}",
            created_by="risk_agent",
            content=content.model_dump(),
            citations=[],
        )
        # Extra keys for evaluation framework
        detected_risks = [r.get("title", audit_area) for r in risks]
        result_dict = {
            "artifact": artifact.model_dump(),
            "risk_level": content.severity,
            "detected_risks": detected_risks,
            "severity": content.severity,
            "citation_count": len(citations),
        }
        logger.info("llm_risk_analysis", area=audit_area, severity=content.severity,
                    tokens=llm_response.usage.total_tokens, citations=len(citations))
        return AgentResponse(
            status="SUCCESS",
            result=result_dict,
            citations=citations,
            confidence=content.probability,
            metrics={"tokens": llm_response.usage.total_tokens, "model": llm_response.model, "citations": len(citations)},
            next_action="EVIDENCE_AGENT",
        )

    def get_tools(self) -> list[ToolDefinition]:
        return [ToolDefinition(name="evidence_search"), ToolDefinition(name="standard_search")]
