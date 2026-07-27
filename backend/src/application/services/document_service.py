"""Document Application Service — 文档上传 → 解析 → 索引的 Use Case 编排

职责: 协调 Parser → OCR → Chunking → Embedding → PGVector 全流程。
API 层通过此 Service 调用，不直接访问 Infrastructure。
"""

import uuid
import structlog
from datetime import datetime

from infrastructure.parser.pdf_parser import PDFParser
from infrastructure.ocr.ocr_service import OCRService
from infrastructure.vector.chunking import chunk_document
from infrastructure.vector.provider import EmbeddingProvider
from infrastructure.vector.store import VectorStore
from infrastructure.storage import ObjectStorage

logger = structlog.get_logger(__name__)


class DocumentService:
    """文档管理 Use Case"""

    def __init__(
        self,
        parser: PDFParser,
        ocr: OCRService | None = None,
        embedder: EmbeddingProvider | None = None,
        vector_store: VectorStore | None = None,
        storage: ObjectStorage | None = None,
    ):
        self._parser = parser
        self._ocr = ocr
        self._embedder = embedder
        self._vector_store = vector_store
        self._storage = storage

    async def upload_and_index(
        self,
        file_bytes: bytes,
        filename: str,
        project_id: str,
        firm_id: str = "default",
    ) -> dict:
        """上传文档并索引到 PGVector（完整 Use Case）"""
        doc_id = uuid.uuid4().hex[:12]

        # 1. 存储原始文件
        if self._storage:
            await self._storage.upload(firm_id, project_id, "documents", f"{doc_id}.pdf", file_bytes)

        # 2. 解析
        parsed = await self._parser.parse(file_bytes, doc_id)

        # 3. OCR（如果需要）
        pages_text = []
        for page in parsed.pages:
            if page.needs_ocr and self._ocr:
                import fitz
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                pdf_page = doc[page.page_number - 1]
                mat = fitz.Matrix(300 / 72, 300 / 72)
                pix = pdf_page.get_pixmap(matrix=mat)
                img = pix.tobytes("png")
                result = await self._ocr.ocr_page(img, page.page_number)
                pages_text.append((page.page_number, result.text))
                doc.close()
            else:
                pages_text.append((page.page_number, page.text))

        # 4. Chunk
        chunks = chunk_document(pages_text, doc_id, max_tokens=500)

        # 5. Embed + Store
        if self._embedder and self._vector_store:
            from infrastructure.vector.models import EmbeddingItem
            vectors = await self._embedder.embed([c.text for c in chunks])
            items = [
                EmbeddingItem(
                    id=c.chunk_id, firm_id=firm_id, client_id=project_id,
                    engagement_id="default", source_type="CLIENT_DOCUMENT",
                    source_id=doc_id, content=c.text, embedding=v,
                    metadata={"page": c.page_number, "source": filename},
                    created_at=datetime.now(),
                ) for c, v in zip(chunks, vectors)
            ]
            await self._vector_store.insert(items)

        logger.info("document_indexed", doc_id=doc_id, pages=parsed.total_pages, chunks=len(chunks))
        return {"document_id": doc_id, "pages": parsed.total_pages, "chunks": len(chunks)}
