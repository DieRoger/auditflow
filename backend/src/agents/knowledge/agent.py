# ruff: noqa: E501
"""LLM Knowledge Agent — 基于检索的审计准则分析

从 context.document_chunks 获取检索到的文档片段，基于真实内容回答。
无 chunks 时降级到 LLM 知识。
"""
from agents.base import ToolDefinition
from agents.base_llm import LlmBaseAgent
from domain.contracts import AgentRequest, AgentResponse, Citation

KNOWLEDGE_SYSTEM = (
    "You are an audit standards expert. "
    "Analyze the provided document excerpts and extract relevant standards and requirements. "
    "Return ONLY valid JSON."
)

KNOWLEDGE_PROMPT = """Audit area: {audit_area}
Risk: {risk_context}

{chunks_section}

Return JSON:
{{"standards": [{{"standard": "standard name", "paragraph": "##", "content": "summary of requirement", "interpretation": "what this means for the audit", "source_page": page_number}}]}}"""

KNOWLEDGE_FALLBACK_PROMPT = """Audit area: {audit_area}
Risk: {risk_context}

Return JSON:
{{"standards": [{{"standard": "IFRS X.YY", "paragraph": "##", "content": "summary of requirement", "interpretation": "what this means for the audit"}}]}}"""


class LlmKnowledgeAgent(LlmBaseAgent):
    name = "knowledge_agent"
    version = "0.3.0"

    async def execute(self, request: AgentRequest) -> AgentResponse:
        audit_area = request.inputs.get("audit_area", "General")
        risk_context = str(request.context.get("risk_summary", "N/A"))[:500]

        # 检查 context 中是否有检索到的文档 chunks
        document_chunks = request.context.get("document_chunks", [])
        if document_chunks and len(document_chunks) > 0:
            # 基于检索结果
            chunks_text = "\n\n---\n\n".join(
                f"[Page {c.get('page', '?')}] {c.get('content', '')[:800]}"
                for c in document_chunks
            )
            chunks_section = f"Document excerpts:\n\n{chunks_text}\n\nBase your analysis on these excerpts. Cite the page number for each standard."
            prompt = KNOWLEDGE_PROMPT.format(
                audit_area=audit_area,
                risk_context=risk_context,
                chunks_section=chunks_section,
            )
            system = KNOWLEDGE_SYSTEM
        else:
            # 降级到 LLM 知识
            prompt = KNOWLEDGE_FALLBACK_PROMPT.format(
                audit_area=audit_area,
                risk_context=risk_context,
            )
            system = "You are an audit standards expert. Retrieve relevant ISA/IFRS standards. Return ONLY valid JSON."

        result = await self.call_llm(system, prompt)
        standards = result.get("standards", [{"standard": "ISA 315", "paragraph": "General", "content": "Risk assessment standards apply"}])

        # 构建 Citation（如有 page 信息则包含）
        citations = []
        for s in standards:
            src_page = s.get("source_page", "")
            doc_id = f"doc_{src_page}" if src_page else s.get("standard", "unknown")
            citations.append(Citation(
                claim=s.get("content", "")[:100],
                document_id=doc_id,
                excerpt=s.get("interpretation", ""),
                confidence=0.85,
                page=src_page if isinstance(src_page, int) else None,
            ))

        return AgentResponse(
            status="SUCCESS",
            result={"standards": standards},
            citations=citations,
            confidence=0.85,
            metrics={"standards": len(standards), "tokens": getattr(self, '_last_tokens', 0)},
            next_action="RISK_AGENT",
        )

    def get_tools(self):
        return [ToolDefinition(name="standard_search"), ToolDefinition(name="cross_reference")]
