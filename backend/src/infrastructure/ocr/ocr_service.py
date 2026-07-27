"""OCR Service — 扫描件文字识别"""

import os
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

import structlog
from pydantic import BaseModel

from infrastructure.parser.pdf_parser import ParsedPage, TextBlock

logger = structlog.get_logger(__name__)


class OCRResult(BaseModel):
    """OCR 识别结果"""
    page_number: int
    text: str
    blocks: list[TextBlock] = []


class OCRService(ABC):
    @abstractmethod
    async def ocr_page(self, image_bytes: bytes, page_number: int) -> OCRResult:
        ...


class TesseractOCRService(OCRService):
    """基于 Tesseract 的 OCR 实现

    支持中英文混合识别（需安装对应语言包）。
    Tesseract 路径通过环境变量 TESSERACT_PATH 配置。
    """

    def __init__(self, lang: str = "eng", tesseract_path: str | None = None):
        self.lang = lang
        self._tesseract = tesseract_path or os.getenv("TESSERACT_PATH", "E:\\Tesseract\\tesseract.exe")

    async def ocr_page(self, image_bytes: bytes, page_number: int) -> OCRResult:
        """对单页扫描图片执行 OCR"""
        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = Path(tmpdir) / f"page_{page_number}.png"
            with open(img_path, "wb") as f:
                f.write(image_bytes)

            result = subprocess.run(
                [self._tesseract, str(img_path), "stdout", "-l", self.lang, "--psm", "6"],
                capture_output=True, text=True, encoding="utf-8", timeout=60,
            )
            text = result.stdout.strip()

            # 从输出中提取文本块（Tesseract 用换行分隔）
            lines = [line for line in text.split("\n") if line.strip()]
            blocks = [
                TextBlock(
                    block_id=f"ocr_p{page_number}_b{i}",
                    text=line.strip(),
                    bbox=(0.0, 0.0, 1.0, 1.0),
                    block_type="PARAGRAPH",
                )
                for i, line in enumerate(lines)
            ]

            logger.info("ocr_completed", page=page_number, chars=len(text), blocks=len(blocks))
            return OCRResult(page_number=page_number, text=text, blocks=blocks)


class PyMuPDFOCRService(OCRService):
    """基于 PyMuPDF 将页面渲染为图片后识别

    使用 Tesseract 作为后端，PyMuPDF 负责页面→图片渲染。
    """

    def __init__(self, dpi: int = 300, lang: str = "eng",
                 tesseract_path: str | None = None):
        self.dpi = dpi
        self._tesseract = TesseractOCRService(lang=lang, tesseract_path=tesseract_path)

    async def ocr_page(self, image_bytes: bytes, page_number: int) -> OCRResult:
        return await self._tesseract.ocr_page(image_bytes, page_number)

    async def ocr_parsed_page(self, pdf_bytes: bytes, page: ParsedPage) -> OCRResult:
        """从 PDF 字节流渲染指定页后执行 OCR"""
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pdf_page = doc[page.page_number - 1]
        matrix = fitz.Matrix(self.dpi / 72, self.dpi / 72)
        pix = pdf_page.get_pixmap(matrix=matrix)
        img_bytes = pix.tobytes("png")
        doc.close()
        return await self._tesseract.ocr_page(img_bytes, page.page_number)
