"""Grounding Checker — 验证 AI Claim 是否被 Citation 支持"""

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
    MVP 实现基于简单规则：检查 Citation 数量与来源。
    """

    MIN_CITATIONS_PER_CLAIM = 1
    MIN_CONFIDENCE = 0.5

    async def verify(self, claim: str, citations: list) -> GroundingResult:
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
