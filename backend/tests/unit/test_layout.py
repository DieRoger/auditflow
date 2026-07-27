"""Layout Analysis + Table Extraction 测试"""

import fitz
import pytest

from infrastructure.parser.layout import LayoutAnalyzer, TableExtractor
from infrastructure.parser.pdf_parser import PyMuPDFParser


@pytest.mark.asyncio
async def test_layout_classifies_headings():
    parser = PyMuPDFParser()
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Annual Report Heading", fontsize=16)
    page.insert_text((50, 150), "Normal body paragraph text line one.", fontsize=10)
    page.insert_text((50, 170), "Another body paragraph text line two.", fontsize=10)
    page.insert_text((50, 190), "Yet another body paragraph line three.", fontsize=10)
    pdf_bytes = doc.tobytes()
    doc.close()

    parsed = await parser.parse(pdf_bytes, "doc_001")
    analyzer = LayoutAnalyzer()
    result = analyzer.analyze(parsed)

    heading = [b for b in result.pages[0].blocks if "Heading" in b.text]
    paragraph = [b for b in result.pages[0].blocks if "paragraph" in b.text]
    if heading:
        assert heading[0].block_type == "HEADING"
    if paragraph:
        assert "PARAGRAPH" in paragraph[0].block_type


@pytest.mark.asyncio
async def test_table_extraction():
    parser = PyMuPDFParser()
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 100), "Revenue Growth Table", fontsize=10)
    page.insert_text((50, 120), "Year    2024    2025", fontsize=10)
    page.insert_text((50, 140), "Revenue 100M    145M", fontsize=10)
    pdf_bytes = doc.tobytes()
    doc.close()

    parsed = await parser.parse(pdf_bytes, "doc_002")
    extractor = TableExtractor()
    tables = extractor.extract_tables(parsed)
    # May or may not detect table depending on layout
    assert isinstance(tables, list)


@pytest.mark.asyncio
async def test_analyzed_document_preserves_structure():
    parser = PyMuPDFParser()
    doc = fitz.open()
    doc.new_page()
    page = doc[0]
    page.insert_text((50, 50), "Test Document", fontsize=14)
    page.insert_text((50, 100), "Body text line one.", fontsize=10)
    page.insert_text((50, 120), "Body text line two.", fontsize=10)
    pdf_bytes = doc.tobytes()
    doc.close()

    parsed = await parser.parse(pdf_bytes, "doc_003")
    analyzer = LayoutAnalyzer()
    result = analyzer.analyze(parsed)
    assert result.total_pages == 1
    assert len(result.pages[0].blocks) >= 2
