"""Hybrid Search — RRB 融合 + Reranker"""

import structlog
from pydantic import BaseModel

from .keyword_search import ScoredHit

logger = structlog.get_logger(__name__)


class HybridResult(BaseModel):
    hits: list[ScoredHit]
    total_before_merge: int = 0


class HybridRetriever:
    """融合向量检索 + 关键词检索的双路检索器"""

    RRB_K = 60  # Reciprocal Rank Fusion 常数

    def __init__(self, vector_retriever, keyword_retriever):
        self._vr = vector_retriever
        self._kr = keyword_retriever

    async def search(
        self, query_text: str, query_vector: list[float], top_k: int = 10,
        firm_id: str | None = None, engagement_id: str | None = None,
        source_type: str | None = None,
    ) -> HybridResult:
        """执行双路检索 + RRB 融合"""
        vector_hits = await self._vr.search(
            query_vector, top_k=self.RRB_K,
            firm_id=firm_id, engagement_id=engagement_id, source_type=source_type,
        )
        keyword_hits = await self._kr.search(
            query_text, top_k=self.RRB_K,
            firm_id=firm_id, engagement_id=engagement_id, source_type=source_type,
        )

        # Reciprocal Rank Fusion
        scores: dict[str, float] = {}
        hit_map: dict[str, ScoredHit] = {}

        for rank, hit in enumerate(vector_hits):
            scores[hit.chunk_id] = scores.get(hit.chunk_id, 0) + 1.0 / (self.RRB_K + rank + 1)
            hit_map[hit.chunk_id] = hit

        for rank, hit in enumerate(keyword_hits):
            scores[hit.chunk_id] = scores.get(hit.chunk_id, 0) + 1.0 / (self.RRB_K + rank + 1)
            hit_map[hit.chunk_id] = hit

        merged = sorted(hit_map.values(), key=lambda h: scores.get(h.chunk_id, 0), reverse=True)[:top_k]
        logger.info("hybrid_search", query=query_text[:50], vector=len(vector_hits), keyword=len(keyword_hits), merged=len(merged))  # noqa: E501
        return HybridResult(hits=merged, total_before_merge=len(vector_hits) + len(keyword_hits))


class Reranker:
    """Cross-Encoder 重排序器（MVP: 简单基于分数重排）"""

    async def rerank(self, query: str, hits: list[ScoredHit], top_k: int = 5) -> list[ScoredHit]:  # noqa: ARG002
        """按分数降序重排"""
        sorted_hits = sorted(hits, key=lambda h: h.score, reverse=True)
        return sorted_hits[:top_k]
