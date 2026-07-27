"""RapidOCR Provider — 基于 ONNX，中文识别率 ~95%，轻量无依赖"""

import asyncio
import structlog

from infrastructure.ocr.ocr_service import OCRService, OCRResult, TextBlock

logger = structlog.get_logger(__name__)


class RapidOCRService(OCRService):
    """基于 RapidOCR 的中文 OCR 实现（ONNX 运行时，无需 PaddlePaddle/PyTorch）"""

    def __init__(self):
        self._ocr = None

    def _lazy_init(self):
        if self._ocr is not None:
            return
        from rapidocr_onnxruntime import RapidOCR
        self._ocr = RapidOCR()

    async def ocr_page(self, image_bytes: bytes, page_number: int) -> OCRResult:
        import tempfile
        from pathlib import Path

        loop = asyncio.get_event_loop()
        self._lazy_init()

        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = Path(tmpdir) / f"page_{page_number}.png"
            with open(img_path, "wb") as f:
                f.write(image_bytes)

            result, elapse = await loop.run_in_executor(None, self._ocr, str(img_path))

        blocks = []
        lines = []
        if result:
            for box, text, conf in result:
                lines.append(text)
                blocks.append(TextBlock(
                    block_id=f"ocr_p{page_number}_b{len(blocks)}",
                    text=text,
                    bbox=tuple(box.flatten().tolist()) if hasattr(box, 'flatten') else (0, 0, 0, 0),
                    block_type="PARAGRAPH",
                ))

        full_text = "\n".join(lines)
        logger.info("ocr_completed", page=page_number, chars=len(full_text), blocks=len(blocks))
        return OCRResult(page_number=page_number, text=full_text, blocks=blocks)
