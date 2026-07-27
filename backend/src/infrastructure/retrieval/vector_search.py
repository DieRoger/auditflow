"""Vector Search — PGVector HNSW 向量检索"""

import json

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from .keyword_search import ScoredHit

logger = structlog.get_logger(__name__)


class VectorRetriever:
    """基于 PGVector HNSW 的向量检索器"""

    def __init__(self, connection: AsyncConnection):
        self._conn = connection

    async def search(
        self, query_vector: list[float], top_k: int = 20,
        firm_id: str | None = None, engagement_id: str | None = None,
        source_type: str | None = None,
    ) -> list[ScoredHit]:
        """向量相似度检索"""
        conditions = ["1=1"]
        params: dict = {
            "query_vector": json.dumps(query_vector),
            "limit": top_k,
        }

        if firm_id:
            conditions.append("firm_id = :firm_id")
            params["firm_id"] = firm_id
        if engagement_id:
            conditions.append("engagement_id = :engagement_id")
            params["engagement_id"] = engagement_id
        if source_type:
            conditions.append("source_type = :source_type")
            params["source_type"] = source_type

        where = " AND ".join(conditions)
        sql = f"""
            SELECT id AS chunk_id, source_type, source_id, content,
                   1 - (embedding <=> :query_vector::vector) AS score,
                   metadata
            FROM embedding_items
            WHERE {where}
            ORDER BY embedding <=> :query_vector::vector
            LIMIT :limit
        """
        result = await self._conn.execute(text(sql), params)
        rows = result.fetchall()

        logger.info("vector_search", hits=len(rows))
        return [
            ScoredHit(
                chunk_id=r[0], source_type=r[1], source_id=r[2],
                content=r[3][:500], score=float(r[4] or 0.0),
                metadata=r[5] or {},
            )
            for r in rows
        ]
