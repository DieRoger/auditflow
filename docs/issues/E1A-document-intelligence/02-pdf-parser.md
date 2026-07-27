# 1A.1.2 — PDF Parser
- **Epic:** E1A Document Intelligence
- **Labels:** `parser`, `document`, `phase-1a`
- **Depends on:** 1A.1.1 (Document Upload API)

## 描述

实现 PDF 解析器，基于 PyMuPDF (fitz) 将上传的 PDF 文档解析为结构化中间表示 `ParsedDocument`。解析内容包括：逐页文本提取、字体信息（名称/大小/是否粗体）、字符级坐标（bbox）、页面尺寸。解析结果供下游 Layout Analysis、OCR Service 和 Semantic Chunking 消费。

对于包含可提取文本层的"原生 PDF"（非扫描件），解析器直接产出 ParsedDocument；对于纯图片扫描件，标记 `needs_ocr=True`，由 OCR Service 后续处理。

## Acceptance Criteria

- [ ] 使用 PyMuPDF 打开 PDF，逐页提取文本 + 字体信息 + 字符坐标
- [ ] 输出 `ParsedDocument` 结构化对象（见 I/O 接口）
- [ ] 自动检测是否扫描件：若文本覆盖率 < 5% 总页面积，标记 `needs_ocr=True`
- [ ] 支持多页 PDF（≥ 200 页）不 OOM — 流式逐页处理
- [ ] 保留原始 PDF 元数据（作者/创建日期/标题，如有）
- [ ] 解析失败时抛出明确异常类型（`PDFParseError`），含 `document_id` + `page_number`
- [ ] 解析耗时纳入 structlog 记录（trace_id 贯穿）

## I/O 接口

```python
class ParsedPage(BaseModel):
    """单页解析结果"""
    page_number: int                        # 1-based
    text: str                               # 该页全部文本（按阅读顺序）
    width: float                            # 页面宽度 (pt)
    height: float                           # 页面高度 (pt)
    blocks: list[TextBlock]                 # 按阅读顺序排列的文本块
    needs_ocr: bool                         # 该页是否需要 OCR

class TextBlock(BaseModel):
    """页面内的一个文本块（段落/标题/表格区域）"""
    block_id: str                           # 全局唯一 block ID
    text: str                               # 块内文本
    bbox: tuple[float, float, float, float] # (x0, y0, x1, y1) 归一化到 [0,1]
    font_name: str | None
    font_size: float | None
    is_bold: bool
    block_type: Literal["PARAGRAPH", "HEADING", "TABLE", "IMAGE", "UNKNOWN"]

class ParsedDocument(BaseModel):
    """PDF 解析的完整结构化输出"""
    document_id: str
    filename: str
    total_pages: int
    pages: list[ParsedPage]
    needs_ocr: bool                         # 任意一页 needs_ocr=True 即为 True
    metadata: dict[str, str]                # PDF 元数据（author/title/created）

class PDFParser(ABC):
    """PDF 解析器抽象"""
    async def parse(self, file_bytes: bytes, document_id: str) -> ParsedDocument: ...
```
