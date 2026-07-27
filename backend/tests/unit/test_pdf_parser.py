"""PDF Parser 测试"""

import fitz
import pytest

from infrastructure.parser.pdf_parser import PyMuPDFParser


@pytest.mark.asyncio
async def test_parse_real_pdf():
    parser = PyMuPDFParser()
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 100), "Hello AuditFlow Test", fontsize=12)
    page.insert_text((50, 130), "Second line for text coverage", fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    result = await parser.parse(pdf_bytes, "doc_001")
    assert result.total_pages == 1
    assert "Hello AuditFlow" in result.pages[0].text


@pytest.mark.asyncio
async def test_detect_scanned_page():
    parser = PyMuPDFParser()
    doc = fitz.open()
    doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()
    result = await parser.parse(pdf_bytes, "doc_002")
    assert result.needs_ocr is True


@pytest.mark.asyncio
async def test_metadata_extracted():
    parser = PyMuPDFParser()
    doc = fitz.open()
    doc.set_metadata({"title": "AR 2025", "author": "Test Corp"})
    doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()
    result = await parser.parse(pdf_bytes, "doc_003")
    assert result.metadata.get("title") == "AR 2025"
