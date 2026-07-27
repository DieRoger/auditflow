"""Knowledge Search API — 向量检索"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    firm_id: str = "default"


@router.post("/search")
async def search_knowledge(req: SearchRequest):
    """语义检索知识库"""
    from infrastructure.vector.local_embedding import LocalEmbeddingProvider
    from sqlalchemy.ext.asyncio import create_async_engine
    from infrastructure.vector.pgvector_store import PGVectorStore
    import os

    provider = LocalEmbeddingProvider()
    vec = await provider.embed([req.query])

    db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://auditflow:auditflow@localhost:5432/auditflow")
    engine = create_async_engine(db_url)
    async with engine.connect() as conn:
        store = PGVectorStore(conn)
        results = await store.search(vec[0], top_k=req.top_k)
        items = []
        for r in results:
            meta = r.metadata or {}
            items.append({
                "score": meta.get("_score", 0),
                "source": meta.get("source", "unknown"),
                "page": meta.get("page", "?"),
                "content": r.content[:300],
            })
    await engine.dispose()

    return {"query": req.query, "results": items}
