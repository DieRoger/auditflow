"""Keyword Search — PostgreSQL tsvector 全文检索"""

import structlog
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

logger = structlog.get_logger(__name__)


class ScoredHit(BaseModel):
    """单条检索结果"""
    chunk_id: str
    source_type: str
    source_id: str
    content: str
    score: float
    metadata: dict = {}


class KeywordRetriever:
    """基于 PostgreSQL tsvector 的关键词检索器"""

    def __init__(self, connection: AsyncConnection):
        self._conn = connection

    async def search(
        self, query_text: str, top_k: int = 20,
        firm_id: str | None = None, engagement_id: str | None = None,
        source_type: str | None = None,
    ) -> list[ScoredHit]:
        """tsvector 关键词检索"""
        conditions = ["1=1"]
        params: dict = {"query": query_text, "limit": top_k}

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
                   ts_rank(to_tsvector('simple', content), plainto_tsquery('simple', :query)) AS score,
                   metadata
            FROM embedding_items
            WHERE {where}
              AND to_tsvector('simple', content) @@ plainto_tsquery('simple', :query)
            ORDER BY score DESC
            LIMIT :limit
        """
        result = await self._conn.execute(text(sql), params)
        rows = result.fetchall()

        logger.info("keyword_search", query=query_text[:50], hits=len(rows))
        return [
            ScoredHit(
                chunk_id=r[0], source_type=r[1], source_id=r[2],
                content=r[3][:500], score=float(r[4] or 0.0),
                metadata=r[5] or {},
            )
            for r in rows
        ]
