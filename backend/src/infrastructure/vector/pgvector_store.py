"""PGVector VectorStore 实现."""

import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from .models import EmbeddingItem
from .store import SearchFilter, VectorStore


class PGVectorStore(VectorStore):
    """基于 PGVector 的向量存储实现

    依赖：PostgreSQL + pgvector 扩展 + HNSW 索引
    """

    def __init__(self, connection: AsyncConnection):
        self._conn = connection

    async def insert(self, items: list[EmbeddingItem]) -> None:
        for item in items:
            await self._conn.execute(
                text("""
                    INSERT INTO embedding_items
                        (id, firm_id, client_id, engagement_id,
                         source_type, source_id, content, embedding,
                         metadata, security_level, created_at)
                    VALUES (
                        :id, :firm_id, :client_id, :engagement_id,
                        :source_type, :source_id, :content, :embedding,
                        :metadata, :security_level, :created_at
                    )
                    ON CONFLICT (id) DO NOTHING
                """),
                {
                    "id": item.id,
                    "firm_id": item.firm_id,
                    "client_id": item.client_id,
                    "engagement_id": item.engagement_id,
                    "source_type": item.source_type,
                    "source_id": item.source_id,
                    "content": item.content,
                    "embedding": json.dumps(item.embedding),
                    "metadata": json.dumps(item.metadata),
                    "security_level": item.security_level,
                    "created_at": item.created_at,
                },
            )

    async def search(
        self,
        query_vector: list[float],
        top_k: int = 20,
        filters: SearchFilter | None = None,
    ) -> list[EmbeddingItem]:
        where_clauses: list[str] = []
        params: dict = {
            "query_vector": json.dumps(query_vector),
            "top_k": top_k,
        }

        if filters:
            if filters.firm_id:
                where_clauses.append("firm_id = :firm_id")
                params["firm_id"] = filters.firm_id
            if filters.engagement_id:
                where_clauses.append("engagement_id = :engagement_id")
                params["engagement_id"] = filters.engagement_id
            if filters.source_type:
                placeholders = ", ".join(f"'{s}'" for s in filters.source_type)
                where_clauses.append(f"source_type IN ({placeholders})")

        where_sql = " AND ".join(where_clauses)
        if where_sql:
            where_sql = "WHERE " + where_sql

        sql = f"""
            SELECT id, firm_id, client_id, engagement_id,
                   source_type, source_id, content,
                   1 - (embedding <=> CAST(:query_vector AS vector)) AS score,
                   metadata, security_level, created_at
            FROM embedding_items
            {where_sql}
            ORDER BY embedding <=> CAST(:query_vector AS vector)
            LIMIT :top_k
        """
        result = await self._conn.execute(text(sql), params)
        rows = result.fetchall()
        return [
            EmbeddingItem(
                id=r[0], firm_id=r[1], client_id=r[2],
                engagement_id=r[3], source_type=r[4],
                source_id=r[5], content=r[6],
                embedding=[], metadata={**(r[8] or {}), "_score": round(float(r[7]), 4)},
                security_level=r[9], created_at=r[10],
            )
            for r in rows
        ]

    async def delete_by_source(self, source_id: str) -> None:
        await self._conn.execute(
            text("DELETE FROM embedding_items WHERE source_id = :source_id"),
            {"source_id": source_id},
        )

    async def delete_by_engagement(self, engagement_id: str) -> None:
        await self._conn.execute(
            text("DELETE FROM embedding_items WHERE engagement_id = :engagement_id"),
            {"engagement_id": engagement_id},
        )
