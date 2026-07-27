"""PaddleOCR Provider — 替代 Tesseract，中文识别率 ~95%

安装:
  1. pip install paddlepaddle -i https://mirror.baidu.com/pypi/simple
  2. pip install paddleocr -i https://mirror.baidu.com/pypi/simple

镜像源（国内加速）:
  pip install paddlepaddle paddleocr -i https://mirror.baidu.com/pypi/simple

验证:
  python -c "from paddleocr import PaddleOCR; ocr = PaddleOCR(use_angle_cls=True, lang='ch'); print('OK')"
"""

import asyncio
import structlog

from infrastructure.ocr.ocr_service import OCRService, OCRResult, TextBlock

logger = structlog.get_logger(__name__)


class PaddleOCRService(OCRService):
    """基于 PaddleOCR 的中文 OCR 实现"""

    def __init__(self, lang: str = "ch", use_angle_cls: bool = True):
        self._lang = lang
        self._use_angle_cls = use_angle_cls
        self._ocr = None

    def _lazy_init(self):
        if self._ocr is not None:
            return
        from paddleocr import PaddleOCR
        self._ocr = PaddleOCR(use_angle_cls=self._use_angle_cls, lang=self._lang)

    async def ocr_page(self, image_bytes: bytes, page_number: int) -> OCRResult:
        """对单页扫描图片执行 OCR"""
        import tempfile
        from pathlib import Path

        loop = asyncio.get_event_loop()
        self._lazy_init()

        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = Path(tmpdir) / f"page_{page_number}.png"
            with open(img_path, "wb") as f:
                f.write(image_bytes)

            result = await loop.run_in_executor(None, self._ocr.ocr, str(img_path))

        # PaddleOCR 返回格式: [[[bbox, (text, confidence)], ...]]
        blocks = []
        lines = []
        if result and result[0]:
            for line_info in result[0]:
                bbox = line_info[0]  # [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
                text, conf = line_info[1]
                lines.append(text)
                blocks.append(TextBlock(
                    block_id=f"ocr_p{page_number}_b{len(blocks)}",
                    text=text,
                    bbox=(bbox[0][0], bbox[0][1], bbox[2][0], bbox[2][1]),
                    block_type="PARAGRAPH",
                ))

        full_text = "\n".join(lines)
        logger.info("ocr_completed", page=page_number, chars=len(full_text), blocks=len(blocks))
        return OCRResult(page_number=page_number, text=full_text, blocks=blocks)
