# ruff: noqa: E501
"""Layout Analysis — 版面分析与表格提取"""

from statistics import median

import structlog
from pydantic import BaseModel, Field

from infrastructure.parser.pdf_parser import ParsedDocument, ParsedPage, TextBlock

logger = structlog.get_logger(__name__)


class TableCell(BaseModel):
    text: str
    row: int
    col: int
    is_header: bool = False


class TableData(BaseModel):
    table_id: str
    page_start: int
    page_end: int = 0
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    markdown: str = ""
    html: str = ""


class LayoutAnalyzer:
    """版面分析器 — 基于规则的精化 TextBlock 类型"""

    HEADER_FOOTER_MARGIN = 0.05
    TITLE_MIN_FONT_RATIO = 1.4

    def analyze(self, doc: ParsedDocument) -> ParsedDocument:
        for page in doc.pages:
            page.blocks = self._classify_blocks(page.blocks)
        logger.info("layout_analyzed", document_id=doc.document_id, pages=len(doc.pages))
        return doc

    def _classify_blocks(self, blocks: list[TextBlock]) -> list[TextBlock]:
        body_size = self._estimate_body_size(blocks)
        for block in blocks:
            # Footer/header by y position
            y_mid = (block.bbox[1] + block.bbox[3]) / 2
            if y_mid < self.HEADER_FOOTER_MARGIN or y_mid > 1 - self.HEADER_FOOTER_MARGIN:
                block.block_type = "PARAGRAPH"
                continue
            # Heading: larger font or bold
            if block.is_bold or (block.font_size and body_size and block.font_size >= body_size * self.TITLE_MIN_FONT_RATIO):
                block.block_type = "HEADING"
                continue
            block.block_type = "PARAGRAPH"
        return blocks

    def _estimate_body_size(self, blocks: list[TextBlock]) -> float:
        sizes = [b.font_size for b in blocks if b.font_size and b.font_size > 0]
        if len(sizes) < 3:
            return 12.0
        return median(sizes)


class TableExtractor:
    """表格检测与提取 — 基于坐标启发式"""

    def extract_tables(self, doc: ParsedDocument) -> list[TableData]:
        tables: list[TableData] = []
        for page in doc.pages:
            regions = self._detect_table_regions(page)
            for region in regions:
                td = self._extract_region(region, page, tables)
                if td:
                    tables.append(td)
        return tables

    def _detect_table_regions(self, page: ParsedPage) -> list[list[TextBlock]]:
        blocks = [b for b in page.blocks if b.text.strip()]
        if not blocks:
            return []
        rows: dict[int, list[TextBlock]] = {}
        for b in blocks:
            y_key = round((b.bbox[1] + b.bbox[3]) / 2 * 100)
            rows.setdefault(y_key, []).append(b)
        potential: list[list[TextBlock]] = []
        for y_key in sorted(rows.keys()):
            row = rows[y_key]
            if len(row) >= 2:
                potential.append(row)
        if potential:
            merged = [b for row in potential for b in row]
            return [merged]
        return []

    def _extract_region(self, blocks: list[TextBlock], page: ParsedPage, existing: list[TableData]) -> TableData | None:
        if not blocks:
            return None
        lines = sorted(blocks, key=lambda b: b.bbox[1])
        headers = [b.text for b in lines if b.is_bold] or [f"Col {i}" for i in range(len(lines))]
        rows = [[b.text] for b in lines if not b.is_bold]
        header_md = " | ".join(headers)
        markdown = f"| {header_md} |\n| {' | '.join(['---'] * len(headers))} |\n"
        if rows:
            markdown += f"| {' | '.join(rows[0])} |"
        return TableData(
            table_id=f"tbl_{len(existing) + 1}",
            page_start=page.page_number,
            headers=headers, rows=rows,
            markdown=markdown,
        )
