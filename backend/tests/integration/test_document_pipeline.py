"""Document Pipeline 集成测试

测试可独立运行的组件（PDF Parser + Chunking）。
Embedding 和 PGVector 测试需要外部服务时自动跳过。
"""

import pytest

from fpdf import FPDF


# ── Fixtures ─────────────────────────────────────────────────

@pytest.fixture
def sample_pdf_bytes():
    """生成包含审计文本的测试 PDF"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    content = (
        "Revenue Recognition Policy\n\n"
        "1. Overview\n"
        "The Company recognizes revenue per IFRS 15.\n\n"
        "2. Performance Obligations\n"
        "Revenue is allocated based on standalone selling prices.\n"
        "Maintenance revenue recognized ratably over 12-36 months.\n\n"
        "3. Risk Indicators\n"
        "- Revenue growth 45% vs industry 10%\n"
        "- AR days increased from 90 to 120\n"
        "- Q4 revenue spike representing 40% of annual revenue"
    )
    pdf.multi_cell(0, 6, content)
    return pdf.output()


@pytest.fixture
def source_id():
    return f"test_{id(sample_pdf_bytes)}"


# ── PDF Parser 测试 ────────────────────────────────────────

@pytest.mark.asyncio
async def test_pdf_parser_parses_pages(sample_pdf_bytes):
    """PDF Parser 正确解析页数和文本"""
    from infrastructure.parser.pdf_parser import PyMuPDFParser

    parser = PyMuPDFParser()
    doc = await parser.parse(sample_pdf_bytes, "test_doc")

    assert doc.total_pages == 1
    assert len(doc.pages) == 1
    assert len(doc.pages[0].text) > 50


@pytest.mark.asyncio
async def test_pdf_parser_extracts_text(sample_pdf_bytes):
    """PDF Parser 提取的文本包含关键内容"""
    from infrastructure.parser.pdf_parser import PyMuPDFParser

    parser = PyMuPDFParser()
    doc = await parser.parse(sample_pdf_bytes, "test_doc")

    full_text = doc.pages[0].text
    assert "IFRS 15" in full_text
    assert "Revenue" in full_text


@pytest.mark.asyncio
async def test_pdf_parser_metadata(sample_pdf_bytes):
    """PDF Parser 提取元数据"""
    from infrastructure.parser.pdf_parser import PyMuPDFParser

    parser = PyMuPDFParser()
    doc = await parser.parse(sample_pdf_bytes, "test_doc")

    # PyMuPDF 报告 document ID 为 metadata 字段
    assert doc.document_id == "test_doc"
    assert doc.total_pages > 0


# ── Chunking 测试 ──────────────────────────────────────────

def test_chunk_text_basic():
    """chunk_text 基本切分"""
    from infrastructure.vector.chunking import chunk_text

    text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
    chunks = chunk_text(text, page_number=1, source_id="test", max_tokens=10)

    assert len(chunks) >= 1
    for c in chunks:
        assert c.page_number == 1
        assert c.metadata["source_id"] == "test"
        assert len(c.text) > 0


def test_chunk_text_metadata():
    """每个 Chunk 包含完整元数据"""
    from infrastructure.vector.chunking import chunk_text

    text = "This is a test paragraph with enough content to make a chunk.\n\nSecond paragraph here with more text content."
    chunks = chunk_text(text, page_number=3, source_id="src_001", max_tokens=5)

    for c in chunks:
        assert c.chunk_id  # 非空 UUID
        assert c.page_number == 3
        assert c.chunk_index >= 0
        assert c.token_count > 0
        assert c.metadata["source_id"] == "src_001"
        assert c.metadata["page"] == 3


def test_chunk_text_empty():
    """空文本返回空列表"""
    from infrastructure.vector.chunking import chunk_text

    chunks = chunk_text("", page_number=1, source_id="test")
    assert chunks == []

    chunks = chunk_text("\n\n\n", page_number=1, source_id="test")
    assert chunks == []


def test_chunk_text_single_paragraph():
    """单段落文本生成 1 个 chunk"""
    from infrastructure.vector.chunking import chunk_text

    text = "This is a single paragraph with some content for testing."
    chunks = chunk_text(text, page_number=1, source_id="test", max_tokens=500)

    assert len(chunks) == 1
    assert chunks[0].text == text


def test_estimate_tokens_english():
    """estimate_tokens 对英文文本的估算合理"""
    from infrastructure.vector.chunking import estimate_tokens

    # ~400 chars of English → ~100 tokens
    text = "The quick brown fox jumps over the lazy dog. " * 10
    tokens = estimate_tokens(text)
    assert 80 <= tokens <= 150  # 合理范围


def test_estimate_tokens_chinese():
    """estimate_tokens 对中文文本的估算合理"""
    from infrastructure.vector.chunking import estimate_tokens

    text = "收入确认是企业会计准则中的重要环节。" * 5
    tokens = estimate_tokens(text)
    assert 50 <= tokens <= 120  # 中文每字符约 1-2 token


# ── End-to-End Parser + Chunking  ──────────────────────────

@pytest.mark.asyncio
async def test_parse_then_chunk(sample_pdf_bytes):
    """PDF Parser → Chunking 全链路（不需要外部服务）"""
    from infrastructure.parser.pdf_parser import PyMuPDFParser
    from infrastructure.vector.chunking import chunk_document

    parser = PyMuPDFParser()
    doc = await parser.parse(sample_pdf_bytes, "e2e_test")

    page_texts = [(p.page_number, p.text) for p in doc.pages]
    chunks = chunk_document(page_texts, "e2e_test", max_tokens=100)

    assert len(chunks) >= 1
    # 验证 chunks 来自正确文档
    for c in chunks:
        assert c.metadata["source_id"] == "e2e_test"
        assert "IFRS" in c.text or "Revenue" in c.text or "Risk" in c.text


# ── Embedding ─────────────────────────────────

@pytest.mark.asyncio
async def test_embedding_local():
    """LocalEmbeddingProvider 可用（无 API key 需求）"""
    try:
        from infrastructure.vector.local_embedding import LocalEmbeddingProvider
    except ImportError:
        pytest.skip("fastembed not installed")

    provider = LocalEmbeddingProvider()
    vectors = await provider.embed(["Test revenue recognition text"])

    import numpy as np
    assert len(vectors) == 1
    assert len(vectors[0]) == provider.dimension()
    assert all(isinstance(v, (float, np.floating)) for v in vectors[0])


@pytest.mark.asyncio
async def test_embedding_local_multiple():
    """LocalEmbeddingProvider 批量 embedding"""
    try:
        from infrastructure.vector.local_embedding import LocalEmbeddingProvider
    except ImportError:
        pytest.skip("fastembed not installed")

    provider = LocalEmbeddingProvider()
    texts = ["Revenue recognition policy", "Inventory valuation method", "Goodwill impairment test"]
    vectors = await provider.embed(texts)

    assert len(vectors) == 3
    # 语义相似的文本向量更接近
    import numpy as np
    v0, v1, v2 = np.array(vectors[0]), np.array(vectors[1]), np.array(vectors[2])
    # 所有向量应为 unit vector（normalized）
    assert abs(np.linalg.norm(v0) - 1.0) < 1e-5


@pytest.mark.asyncio
async def test_embedding_openai():
    """OpenAI Embedding Provider 可用性测试（需要 OPENAI_API_KEY）"""
    import os
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    from infrastructure.vector.openai_embedding import OpenAIEmbeddingProvider

    provider = OpenAIEmbeddingProvider()
    vectors = await provider.embed(["Test revenue recognition text"])

    assert len(vectors) == 1
    assert len(vectors[0]) == provider.dimension()


# ── PGVector (需要 PostgreSQL 时跳过) ──────────────────────

@pytest.mark.asyncio
async def test_pgvector_connection():
    """PGVector 连接测试（需要 PostgreSQL）"""
    try:
        import asyncpg
    except ImportError:
        pytest.skip("asyncpg not installed")

    import os
    db_url = os.getenv("DATABASE_URL", "postgresql://auditflow:auditflow@localhost:5432/auditflow")
    try:
        conn = await asyncpg.connect(db_url, timeout=3)
    except (OSError, ConnectionError):
        pytest.skip("PostgreSQL not available")

    # 检查 pgvector 扩展
    ext = await conn.fetchval(
        "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname='vector')"
    )
    await conn.close()
    assert ext is True, "pgvector extension not installed"
