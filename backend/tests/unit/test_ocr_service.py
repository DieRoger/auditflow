"""OCR Service 测试"""

import pytest

from infrastructure.ocr.ocr_service import OCRResult, TesseractOCRService


@pytest.mark.asyncio
async def test_tesseract_available():
    """验证 Tesseract 可执行"""
    import subprocess
    result = subprocess.run(
        ["E:\\Tesseract\\tesseract.exe", "--version"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    assert "tesseract" in result.stdout.lower()


@pytest.mark.asyncio
async def test_ocr_english_text():
    svc = TesseractOCRService(tesseract_path="E:\\Tesseract\\tesseract.exe")
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 200), "HELLO WORLD 123", fontsize=24)
    pdf_bytes = doc.tobytes()
    doc.close()
    # 渲染为图片
    doc2 = fitz.open(stream=pdf_bytes, filetype="pdf")
    pix = doc2[0].get_pixmap(matrix=fitz.Matrix(300 / 72, 300 / 72))
    img_bytes = pix.tobytes("png")
    doc2.close()

    result = await svc.ocr_page(img_bytes, 1)
    assert isinstance(result, OCRResult)
    assert len(result.text) > 0
    assert "HELLO" in result.text or "123" in result.text
