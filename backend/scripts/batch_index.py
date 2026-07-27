"""批量索引所有 Digital PDF 到 PGVector"""
import asyncio, os, sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"), override=True)

from infrastructure.parser.pdf_parser import PyMuPDFParser
from infrastructure.vector.chunking import chunk_document
from infrastructure.vector.local_embedding import LocalEmbeddingProvider
from infrastructure.vector.models import EmbeddingItem
from sqlalchemy.ext.asyncio import create_async_engine
from infrastructure.vector.pgvector_store import PGVectorStore
from sqlalchemy import text

TARGETS = [
    ("百利科技2025年报", "../datasets/百利科技：湖南百利工程科技股份有限公司2025年年度报告全文.pdf"),
    ("坛金矿业2026年报", "../datasets/坛金矿业：2026年年报.pdf"),
    ("CAS14 收入",       "../datasets/企业会计准则第14号——收入.pdf"),
    ("CAS8 资产减值",    "../datasets/企业会计准则第8号——资产减值.pdf"),
    ("证监会处罚决定",    "../datasets/ST百利：百利科技关于收到中国证监会湖南监管局《行政处罚决定书》的公告.pdf"),
]

async def index_one(name: str, pdf_path: str) -> dict:
    source_id = f"doc_{name[:4]}_{os.urandom(4).hex()}"
    with open(pdf_path, "rb") as f:
        data = f.read()

    parser = PyMuPDFParser()
    doc = await parser.parse(data, source_id)
    texts = [(p.page_number, p.text) for p in doc.pages]
    chunks = chunk_document(texts, source_id, max_tokens=500)

    provider = LocalEmbeddingProvider()
    vectors = await provider.embed([c.text for c in chunks])

    items = [
        EmbeddingItem(
            id=c.chunk_id, firm_id="default", client_id="default",
            engagement_id="default", source_type="CLIENT_DOCUMENT",
            source_id=source_id, content=c.text, embedding=v,
            metadata={"page": c.page_number, "source": name, "file": os.path.basename(pdf_path)},
            created_at=datetime.now(),
        ) for c, v in zip(chunks, vectors)
    ]

    db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://auditflow:auditflow@localhost:5432/auditflow")
    engine = create_async_engine(db_url)
    async with engine.connect() as conn:
        store = PGVectorStore(conn)
        await store.insert(items)
        await conn.commit()
        cnt = await conn.execute(text("SELECT COUNT(*) FROM embedding_items WHERE source_id=:s"), {"s": source_id})
        stored = cnt.scalar()
    await engine.dispose()

    print(f"  {name:>16} | {doc.total_pages:>3}p → {len(chunks):>3}chunks → {stored} stored | avg {sum(c.token_count for c in chunks)//len(chunks)}tok")
    return {"name": name, "pages": doc.total_pages, "chunks": len(chunks), "stored": stored}

async def main():
    print(f"{'='*60}")
    print(f"  Batch Index — {len(TARGETS)} documents")
    print(f"{'='*60}\n")
    total = {"pages": 0, "chunks": 0, "stored": 0}
    for name, path in TARGETS:
        r = await index_one(name, path)
        total["pages"] += r["pages"]
        total["chunks"] += r["chunks"]
        total["stored"] += r["stored"]
    print(f"\n{'='*60}")
    print(f"  Total: {total['pages']} pages → {total['chunks']} chunks → {total['stored']} stored")
    print(f"{'='*60}")

asyncio.run(main())
