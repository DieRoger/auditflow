# 1A.2.1 — Layout Analysis + Table Extraction
- **Epic:** E1A Document Intelligence
- **Labels:** `layout`, `table`, `document`, `phase-1a`
- **Depends on:** 1A.1.2 (PDF Parser)

## 描述

对已解析的 `ParsedDocument` 执行版面分析，识别文档的逻辑结构（标题层级、段落、页眉页脚、图表区域），并将 `TextBlock.block_type` 从 `UNKNOWN` 细化为具体类型。

重点实现**表格提取**：检测页面中的表格区域，提取表格结构（行/列/表头），输出结构化 `TableData`（含 DataFrame 表示 + 原始文本表示）。财报文档中的财务报表（资产负债表、利润表、现金流量表）是后续 Risk Agent 分析的核心数据源，表格提取质量直接影响审计风险评估的准确性。

版面分析推荐使用规则引擎（基于 bbox 坐标 + 字体信息）作为主路径，可选结合轻量视觉模型（如 YOLOv8-doclaynet）提升复杂布局的识别精度。

## Acceptance Criteria

- [ ] 基于 `TextBlock.bbox` + `font_size` + `is_bold` 规则引擎细化 block_type
- [ ] 识别层级标题（HEADING 按字号分为 H1/H2/H3）
- [ ] 识别页眉/页脚区域并标记（y < 5% page_height 或 y > 95% page_height）
- [ ] 检测表格区域 → 标记 block_type=TABLE
- [ ] 表格提取：合并同一表格的碎片化 TextBlock → 重建行列结构 → 输出 `TableData`
- [ ] 表头自动识别（首行粗体 / 首行背景色区别于数据行）
- [ ] 支持跨页表格合并（连续两页的表格结构相同 → 标记为同一表格的延续）
- [ ] 财报三大表（资产负债表/利润表/现金流量表）提取准确率 ≥ 90%（基于 E7 Benchmark）
- [ ] 输出结构含：DataFrame（程序消费）+ Markdown Table（LLM 消费）+ 原始 HTML-like 表示

## I/O 接口

```python
class TableData(BaseModel):
    """提取的表格结构化数据"""
    table_id: str                                   # 全局唯一 table ID
    page_numbers: list[int]                         # 表格跨越的页码（跨页表格含多页）
    caption: str | None                             # 表格标题/说明文字
    headers: list[str]                              # 列标题
    rows: list[list[str]]                           # 数据行（字符串形式保留原始格式）
    df_json: str                                    # pandas DataFrame.to_json(orient="records")
    markdown: str                                   # Markdown 表格表示
    bbox: tuple[float, float, float, float]         # 表格在首页的归一化边界框

class LayoutAnalysisResult(BaseModel):
    """版面分析输出 — 在原 ParsedDocument 基础上细化"""
    document_id: str
    pages: list[AnalyzedPage]
    tables: list[TableData]                         # 文档中所有表格

class AnalyzedPage(BaseModel):
    """含细化 block_type 的单页"""
    page_number: int
    blocks: list[TextBlock]                         # block_type 已细化为 HEADING/PARAGRAPH/TABLE/HEADER/FOOTER/IMAGE
    has_table: bool
    table_ids: list[str]                            # 该页包含的 table_id 列表
```
