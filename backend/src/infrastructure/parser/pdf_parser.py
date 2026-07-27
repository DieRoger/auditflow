"""PDF Parser — PyMuPDF 实现"""

from abc import ABC, abstractmethod
from typing import Literal

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

# ── Data Models ─────────────────────────────────────────────────

class TextBlock(BaseModel):
    block_id: str
    text: str
    bbox: tuple[float, float, float, float]
    font_name: str | None = None
    font_size: float | None = None
    is_bold: bool = False
    block_type: Literal["PARAGRAPH", "HEADING", "TABLE", "IMAGE", "UNKNOWN"] = "PARAGRAPH"


class ParsedPage(BaseModel):
    page_number: int
    text: str = ""
    width: float = 0.0
    height: float = 0.0
    blocks: list[TextBlock] = Field(default_factory=list)
    needs_ocr: bool = False


class ParsedDocument(BaseModel):
    document_id: str
    filename: str = ""
    total_pages: int = 0
    pages: list[ParsedPage] = Field(default_factory=list)
    needs_ocr: bool = False
    metadata: dict[str, str] = Field(default_factory=dict)


class PDFParseError(Exception):
    def __init__(self, message: str, document_id: str = "", page_number: int = 0):
        self.document_id = document_id
        self.page_number = page_number
        super().__init__(message)


# ── PDF Parser ─────────────────────────────────────────────────

class PDFParser(ABC):
    @abstractmethod
    async def parse(self, file_bytes: bytes, document_id: str) -> ParsedDocument:
        ...


class PyMuPDFParser(PDFParser):
    """基于 PyMuPDF 的 PDF 解析器"""

    TEXT_COVERAGE_THRESHOLD = 0.05  # 文本面积 < 5% 页面 → 标记 needs_ocr

    async def parse(self, file_bytes: bytes, document_id: str) -> ParsedDocument:
        import fitz
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pdf_meta = doc.metadata or {}

        pages: list[ParsedPage] = []
        overall_needs_ocr = False

        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks_raw = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

            text_blocks: list[TextBlock] = []
            page_text_parts: list[str] = []
            text_area = 0.0
            page_width = page.rect.width
            page_height = page.rect.height

            for b in blocks_raw:
                if b["type"] == 0:  # text block
                    block_text = ""
                    block_font = None
                    block_size = None
                    block_bold = False
                    for line in b.get("lines", []):
                        for span in line.get("spans", []):
                            block_text += span.get("text", "")
                            if span.get("font"):
                                block_font = span["font"]
                                block_size = span.get("size", 0)
                                block_bold = "Bold" in span.get("font", "")  # noqa: E501
                    if block_text.strip():
                        x0, y0, x1, y1 = b["bbox"]
                        text_area += (x1 - x0) * (y1 - y0)
                        tb = TextBlock(
                            block_id=f"p{page_num + 1}_b{len(text_blocks)}",
                            text=block_text.strip(),
                            bbox=(x0 / page_width, y0 / page_height,
                                  x1 / page_width, y1 / page_height),
                            font_name=block_font,
                            font_size=block_size,
                            is_bold=block_bold,
                        )
                        text_blocks.append(tb)
                        page_text_parts.append(block_text.strip())

                elif b["type"] == 1:  # image block
                    pass

            page_text = "\n".join(page_text_parts)
            total_area = page_width * page_height
            coverage = text_area / total_area if total_area > 0 else 0
            needs_ocr = coverage < self.TEXT_COVERAGE_THRESHOLD
            if needs_ocr:
                overall_needs_ocr = True

            pages.append(ParsedPage(
                page_number=page_num + 1,
                text=page_text,
                width=page_width,
                height=page_height,
                blocks=text_blocks,
                needs_ocr=needs_ocr,
            ))

        doc.close()
        logger.info("pdf_parsed", document_id=document_id, pages=len(pages), needs_ocr=overall_needs_ocr)

        return ParsedDocument(
            document_id=document_id,
            filename=pdf_meta.get("title", ""),
            total_pages=len(pages),
            pages=pages,
            needs_ocr=overall_needs_ocr,
            metadata={k: str(v) for k, v in pdf_meta.items() if v},
        )
