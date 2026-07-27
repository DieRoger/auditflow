"""Document Pipeline Validation — 端到端验证 PDF → Chunk → Embedding → PGVector

用法: python -m scripts.validate_pipeline

逐步骤验证每个组件的可用性，报告 pass/fail 状态。
不新增功能，只验证已有能力。
"""

import asyncio
import json
import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"), override=True)


# ── Step Result 模型 ──────────────────────────────────────────

@dataclass
class StepResult:
    name: str
    passed: bool
    detail: str = ""
    duration_ms: int = 0
    warnings: list[str] = field(default_factory=list)


class PipelineValidator:
    def __init__(self):
        self.results: list[StepResult] = []
        self.source_id = uuid.uuid4().hex[:12]
        self.test_pdf_bytes: bytes = b""

    def record(self, name: str, passed: bool, detail: str = "", warnings: list[str] | None = None) -> StepResult:
        r = StepResult(name=name, passed=passed, detail=detail, warnings=warnings or [])
        self.results.append(r)
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")
        if detail:
            print(f"        {detail}")
        for w in (warnings or []):
            print(f"        WARN: {w}")
        return r

    # ── Step 1: 创建测试 PDF ─────────────────────────────────

    def step_create_test_pdf(self):
        """用 fpdf2 生成包含审计文本的测试 PDF"""
        try:
            from fpdf import FPDF

            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", size=12)

            # 模拟审计文档内容（全部 ASCII 安全字符）
            content = """Revenue Recognition Policy

1. Overview
The Company recognizes revenue in accordance with IFRS 15 - Revenue from Contracts with Customers.
Revenue is recognized when control of promised goods or services is transferred to customers.

2. Performance Obligations
The Company identifies performance obligations in contracts with customers.
For bundled hardware and maintenance contracts, revenue is allocated based on standalone selling prices.
Maintenance revenue is recognized ratably over the contract term (typically 12-36 months).

3. Variable Consideration
Volume discounts and rebates are estimated using the expected value method.
Estimates are constrained to the extent that it is highly probable a significant reversal will not occur.
Historical rebate rates range from 3% to 8% of gross revenue.

4. Contract Modifications
Modifications are accounted for as separate contracts when they add distinct goods/services at standalone price.
Otherwise, modifications are combined with the original contract and revenue is adjusted on a cumulative catch-up basis.

5. Significant Judgments
Management exercises significant judgment in determining standalone selling prices and estimating variable consideration.
The timing of revenue recognition for long-term construction contracts requires estimation of percentage of completion.
Changes in estimates could materially affect reported revenue in any given period.

6. Key Risk Indicators
- Revenue growth of 45% vs industry average of 10%
- Accounts receivable days increased from 90 to 120 days
- Unusual Q4 revenue spike representing 40% of annual revenue
- Multiple contract modifications in the final week of the reporting period"""

            pdf.multi_cell(0, 6, content)
            self.test_pdf_bytes = pdf.output()
            self.record(
                "Create Test PDF",
                True,
                f"Generated {len(self.test_pdf_bytes)} bytes, 1 page with audit content",
            )
        except Exception as e:
            self.record("Create Test PDF", False, str(e))

    # ── Step 2: PDF 解析 ─────────────────────────────────────

    async def step_pdf_parser(self):
        """验证 PyMuPDFParser 能正确解析 PDF"""
        if not self.test_pdf_bytes:
            self.record("PDF Parser", False, "No test PDF bytes (previous step failed)")
            return

        try:
            from infrastructure.parser.pdf_parser import PyMuPDFParser

            parser = PyMuPDFParser()
            doc = await parser.parse(self.test_pdf_bytes, self.source_id)

            checks = []
            checks.append(f"{doc.total_pages} pages")
            total_text = sum(len(p.text) for p in doc.pages)
            checks.append(f"{total_text} chars extracted")
            if doc.metadata:
                checks.append(f"metadata: {len(doc.metadata)} fields")

            passed = doc.total_pages > 0 and total_text > 100
            self.record("PDF Parser", passed, ", ".join(checks))
        except ImportError as e:
            self.record("PDF Parser", False, f"PyMuPDF not installed: {e}")
        except Exception as e:
            self.record("PDF Parser", False, str(e))

    # ── Step 3: Chunking ─────────────────────────────────────

    async def step_chunking(self):
        """验证 Chunking 能正确切分文本"""
        if not self.test_pdf_bytes:
            self.record("Chunking", False, "No test PDF bytes")
            return

        try:
            from infrastructure.parser.pdf_parser import PyMuPDFParser
            from infrastructure.vector.chunking import chunk_document

            parser = PyMuPDFParser()
            doc = await parser.parse(self.test_pdf_bytes, self.source_id)
            page_texts = [(p.page_number, p.text) for p in doc.pages]
            chunks = chunk_document(page_texts, self.source_id, max_tokens=200)

            checks = []
            checks.append(f"{len(chunks)} chunks")
            if chunks:
                avg_tokens = sum(c.token_count for c in chunks) / len(chunks)
                checks.append(f"avg {avg_tokens:.0f} tokens/chunk")
                # 验证元数据
                has_metadata = all(c.metadata.get("source_id") == self.source_id for c in chunks)
                checks.append(f"metadata: {'OK' if has_metadata else 'MISSING'}")

            passed = len(chunks) > 0
            self.record("Chunking", passed, ", ".join(checks))
        except Exception as e:
            self.record("Chunking", False, str(e))

    # ── Step 4: Embedding ────────────────────────────────────

    async def step_embedding(self):
        """验证 Embedding 是否可用（先试本地，再试 OpenAI）"""
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"), override=True)

        # 尝试本地（推荐）
        try:
            from infrastructure.vector.local_embedding import LocalEmbeddingProvider

            provider = LocalEmbeddingProvider()
            vectors = await provider.embed(["Test revenue recognition text"])

            passed = len(vectors) == 1 and len(vectors[0]) == provider.dimension()
            self.record(
                "Embedding (local)",
                passed,
                f"1 vector, dim={len(vectors[0]) if vectors else 'N/A'} (local, no API key needed)",
            )
            return
        except ImportError:
            pass  # fastembed 未安装，降级到 OpenAI
        except Exception as e:
            # 模型下载失败等
            msg = str(e)
            if "ownload" in msg or "onnection" in msg or "time" in msg:
                self.record("Embedding (local)", False,
                            f"Model download issue: {msg[:80]}",
                            warnings=["First run downloads model from HuggingFace (offline afterwards)"],
                            )
            else:
                self.record("Embedding (local)", False, msg)
            # 继续尝试 OpenAI

        # 降级到 OpenAI
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            self.record(
                "Embedding (OpenAI)", False,
                "OPENAI_API_KEY not set — install fastembed or set OPENAI_API_KEY",
                warnings=["pip install fastembed  # 推荐：本地运行，零成本"],
            )
            return

        try:
            from infrastructure.vector.openai_embedding import OpenAIEmbeddingProvider

            provider = OpenAIEmbeddingProvider()
            vectors = await provider.embed(["Test revenue recognition text"])

            passed = len(vectors) == 1 and len(vectors[0]) == provider.dimension()
            self.record(
                "Embedding (OpenAI)",
                passed,
                f"1 vector generated, dimension={len(vectors[0]) if vectors else 'N/A'}",
            )
        except Exception as e:
            self.record("Embedding (OpenAI)", False, str(e))

    # ── Step 5: PGVector Store ───────────────────────────────

    async def step_pgvector(self):
        """验证 PGVector 是否可用"""
        try:
            import asyncpg
        except ImportError:
            self.record(
                "PGVector Store", False,
                "asyncpg not installed",
                warnings=["pip install asyncpg to enable PGVector"],
            )
            return

        db_url = os.getenv("DATABASE_URL", "postgresql://auditflow:auditflow@localhost:5432/auditflow")
        try:
            conn = await asyncpg.connect(db_url, timeout=5)

            # 检查 pgvector 扩展
            ext = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname='vector')"
            )
            # 检查 embedding_items 表
            table = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='embedding_items')"
            )

            details = []
            details.append("pgvector extension: " + ("OK" if ext else "MISSING"))
            details.append("embedding_items table: " + ("OK" if table else "MISSING"))

            await conn.close()
            passed = ext and table
            self.record("PGVector Store", passed, ", ".join(details))
        except (OSError, ConnectionError) as e:
            self.record(
                "PGVector Store", False,
                f"Cannot connect: {e}",
                warnings=["Run: docker compose up -d postgres"],
            )
        except Exception as e:
            self.record("PGVector Store", False, str(e))

    # ── Step 6: 全链路集成（如前面步骤都通过）───────────────

    async def step_full_pipeline(self):
        """端到端集成测试：PDF → Parse → Chunk → Embed → Store"""
        # 检查前置步骤（只检查核心 4 步，PGVector 不可用时仍可验证 Parser→Chunk→Embed）
        core_steps = {"Create Test PDF", "PDF Parser", "Chunking"}
        core_failed = [r for r in self.results if r.name in core_steps and not r.passed]
        embed_passed = any(
            r.name.startswith("Embedding") and r.passed
            for r in self.results
        )
        if core_failed:
            self.record(
                "Full Pipeline", False,
                f"Skipped — {len(core_failed)} core steps failed: {[f.name for f in core_failed]}",
            )
            return
        if not embed_passed:
            self.record(
                "Full Pipeline", False,
                "Skipped — no embedding provider available",
            )
            return

        try:
            # Re-parse
            from infrastructure.parser.pdf_parser import PyMuPDFParser
            from infrastructure.vector.chunking import chunk_document
            from infrastructure.vector.models import EmbeddingItem

            parser = PyMuPDFParser()
            doc = await parser.parse(self.test_pdf_bytes, self.source_id)
            page_texts = [(p.page_number, p.text) for p in doc.pages]
            chunks = chunk_document(page_texts, self.source_id, max_tokens=200)

            # Embed（先试本地，降级到 OpenAI）
            try:
                from infrastructure.vector.local_embedding import LocalEmbeddingProvider
                provider = LocalEmbeddingProvider()
            except ImportError:
                from infrastructure.vector.openai_embedding import OpenAIEmbeddingProvider
                provider = OpenAIEmbeddingProvider()

            texts = [c.text for c in chunks]
            vectors = await provider.embed(texts)

            # Build EmbeddingItems
            items = [
                EmbeddingItem(
                    id=c.chunk_id,
                    firm_id="validate",
                    client_id="validate",
                    engagement_id="validate",
                    source_type="CLIENT_DOCUMENT",
                    source_id=self.source_id,
                    content=c.text,
                    embedding=v,
                    metadata=c.metadata,
                    created_at=datetime.now(),
                )
                for c, v in zip(chunks, vectors)
            ]

            # Store（如果 PGVector 可用则写入数据库，否则写入 JSON 验证）
            store_note = ""
            try:
                import asyncpg
                from sqlalchemy.ext.asyncio import create_async_engine
                from infrastructure.vector.pgvector_store import PGVectorStore

                db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://auditflow:auditflow@localhost:5432/auditflow")
                engine = create_async_engine(db_url)
                async with engine.connect() as conn:
                    store = PGVectorStore(conn)
                    await store.insert(items)

                    from sqlalchemy import text
                    count = await conn.execute(
                        text("SELECT COUNT(*) FROM embedding_items WHERE source_id = :sid"),
                        {"sid": self.source_id},
                    )
                    count_val = count.scalar()

                await engine.dispose()
                store_note = f"PGVector({count_val} rows)"
            except (Exception, ImportError, OSError) as e:
                # PGVector 不可用时，写入 JSON 文件作为验证
                import json as jmod
                output = {
                    "source_id": self.source_id,
                    "total_pages": doc.total_pages,
                    "chunks": len(chunks),
                    "embeddings": len(vectors),
                    "dimension": len(vectors[0]) if vectors else 0,
                    "sample_chunk": {
                        "text": chunks[0].text[:200] if chunks else "",
                        "token_count": chunks[0].token_count if chunks else 0,
                        "metadata": chunks[0].metadata if chunks else {},
                    },
                    "embedding_preview": f"[{vectors[0][0]:.4f}, {vectors[0][1]:.4f}, ...] ({len(vectors[0])} dim)" if vectors else "N/A",
                }
                output_path = os.path.join(os.path.dirname(__file__), f"pipeline_{self.source_id[:8]}.json")
                with open(output_path, "w") as f:
                    jmod.dump(output, f, indent=2, ensure_ascii=False)
                store_note = f"JSON output ({output_path}) — PGVector not available"

            self.record(
                "Full Pipeline",
                True,
                f"PDF({doc.total_pages}p) → Chunks({len(chunks)}) → Embed({len(vectors)}) → {store_note}",
            )
        except Exception as e:
            self.record("Full Pipeline", False, str(e))

    # ── 执行所有步骤 ─────────────────────────────────────────

    async def run_all(self):
        print("=" * 65)
        print("  AuditFlow Document Pipeline — Validation Report")
        print("=" * 65)
        print(f"  Source ID: {self.source_id}")
        print()

        self.step_create_test_pdf()
        await self.step_pdf_parser()
        await self.step_chunking()
        await self.step_embedding()
        await self.step_pgvector()
        await self.step_full_pipeline()

        # 摘要
        print()
        print("=" * 65)
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        print(f"  Result: {passed}/{total} steps passed")
        for r in self.results:
            icon = "+" if r.passed else "x"
            print(f"  [{icon}] {r.name}")
            if r.warnings:
                for w in r.warnings:
                    print(f"      -> {w}")
        print("=" * 65)


async def main():
    validator = PipelineValidator()
    await validator.run_all()


if __name__ == "__main__":
    asyncio.run(main())
