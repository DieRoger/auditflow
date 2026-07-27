"""Grounding Checker — 验证 AI Claim 是否被 Citation 支持

两层验证:
  Layer 1 — 规则检查: Citation 数量、置信度阈值（已有）
  Layer 2 — 语义判断: LLM Judge 判断 Evidence 是否真正支持 Claim（新增）
"""

import json
import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class GroundingResult(BaseModel):
    claim: str
    grounded: bool = False
    score: float = 0.0
    hallucination_risk: float = 0.0
    contradictory_evidence: list[str] = Field(default_factory=list)


class GroundingChecker:
    """Grounding 验证器

    检查 AI 输出的每条 Claim 是否有对应的 Citation 支持。
    Layer 1: 规则检查（数量 + 置信度）
    Layer 2: LLM Judge 语义判断（可选，通过 use_llm_judge=True 启用）
    """

    MIN_CITATIONS_PER_CLAIM = 1
    MIN_CONFIDENCE = 0.5

    JUDGE_PROMPT = """You are an audit evidence validator. Determine if the provided EVIDENCE supports the RISK claim.

RISK: {claim}
EVIDENCE: {evidence}

Respond with ONLY a JSON object:
{{"supports": true/false, "confidence": 0.0-1.0, "reason": "one sentence explanation"}}"""

    def __init__(self, use_llm_judge: bool = False):
        self._use_llm_judge = use_llm_judge

    async def verify(self, claim: str, citations: list) -> GroundingResult:
        """验证单个 Claim 是否被 Citation 支持"""
        # Layer 1: 规则检查
        if not citations:
            return GroundingResult(
                claim=claim, grounded=False, score=0.0,
                hallucination_risk=1.0,
                contradictory_evidence=["无任何引用"],
            )

        valid_citations = [c for c in citations if self._is_valid(c)]
        if len(valid_citations) < self.MIN_CITATIONS_PER_CLAIM:
            return GroundingResult(
                claim=claim, grounded=False, score=0.0,
                hallucination_risk=0.8,
                contradictory_evidence=["引用无效或置信度不足"],
            )

        avg_confidence = sum(
            c.get("confidence", 0) if isinstance(c, dict) else getattr(c, "confidence", 0) or 0
            for c in valid_citations
        ) / len(valid_citations)
        grounded = avg_confidence >= self.MIN_CONFIDENCE

        # Layer 2: LLM Judge 语义判断（可选）
        llm_support = 1.0
        if self._use_llm_judge and valid_citations:
            try:
                llm_support = await self._llm_judge(claim, valid_citations[0])
            except Exception:
                pass  # LLM Judge 失败不影响规则检查

        score = avg_confidence * llm_support
        grounded = score >= self.MIN_CONFIDENCE

        logger.info("grounding_check", claim=claim[:50], grounded=grounded,
                    citations=len(valid_citations), llm_score=llm_support)
        return GroundingResult(
            claim=claim,
            grounded=grounded,
            score=round(score, 4),
            hallucination_risk=round(1.0 - score, 4),
        )

    async def _llm_judge(self, claim: str, citation) -> float:
        """LLM Judge: 判断 Evidence 是否语义上支持 Claim"""
        from infrastructure.llm.deepseek_provider import DeepSeekProvider
        from infrastructure.llm.models import LLMMessage

        evidence = citation.get("excerpt", "") if isinstance(citation, dict) else getattr(citation, "excerpt", "")
        if not evidence:
            return 1.0

        provider = DeepSeekProvider()
        prompt = self.JUDGE_PROMPT.format(claim=claim[:500], evidence=evidence[:800])
        resp = await provider.generate([
            LLMMessage(role="system", content="Return ONLY valid JSON."),
            LLMMessage(role="user", content=prompt),
        ])
        try:
            result = json.loads(resp.content)
            return result.get("confidence", 0.5) if result.get("supports") else 0.0
        except (json.JSONDecodeError, AttributeError):
            return 0.5

    def _is_valid(self, citation) -> bool:
        """验证单个 Claim 是否被 Citation 支持"""
        if not citations:
            return GroundingResult(
                claim=claim, grounded=False, score=0.0,
                hallucination_risk=1.0,
                contradictory_evidence=["无任何引用"],
            )

        valid_citations = [c for c in citations if self._is_valid(c)]
        if len(valid_citations) < self.MIN_CITATIONS_PER_CLAIM:
            return GroundingResult(
                claim=claim, grounded=False, score=0.0,
                hallucination_risk=0.8,
                contradictory_evidence=["引用无效或置信度不足"],
            )

        avg_confidence = sum(
            c.get("confidence", 0) if isinstance(c, dict) else getattr(c, "confidence", 0) or 0
            for c in valid_citations
        ) / len(valid_citations)
        grounded = avg_confidence >= self.MIN_CONFIDENCE

        logger.info("grounding_check", claim=claim[:50], grounded=grounded, citations=len(valid_citations))
        return GroundingResult(
            claim=claim,
            grounded=grounded,
            score=round(avg_confidence, 4),
            hallucination_risk=round(1.0 - avg_confidence, 4),
        )

    def _is_valid(self, citation) -> bool:
        """检查单条 Citation 是否有效"""
        doc_id = getattr(citation, "document_id", None) or (isinstance(citation, dict) and citation.get("document_id"))
        return bool(doc_id)
