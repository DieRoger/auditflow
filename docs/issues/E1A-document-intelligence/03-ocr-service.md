# 1A.1.3 — OCR Service
- **Epic:** E1A Document Intelligence
- **Labels:** `ocr`, `document`, `celery`, `phase-1a`
- **Depends on:** 1A.1.2 (PDF Parser)

## 描述

实现 OCR（光学字符识别）服务，处理 PDF Parser 标记为 `needs_ocr=True` 的扫描件页面。使用 PaddleOCR 作为识别引擎，以 Celery Worker 异步执行，避免阻塞主 API 线程。

流程：PDF Parser 产出的 `ParsedDocument` 中 `needs_ocr=True` 的页面 → 渲染为高分辨率图片 → PaddleOCR 识别 → 将识别文本回填到 `ParsedPage.text` 和 `TextBlock.text` → 标记 `needs_ocr=False` → 传递给下游 Chunking Pipeline。

对于混合 PDF（部分页面有文本层、部分为扫描件），OCR Service 仅处理 `needs_ocr=True` 的页面，已有文本层的页面保持不变。

## Acceptance Criteria

- [ ] 集成 PaddleOCR（onnxruntime 推理，无 GPU 也能运行）
- [ ] Celery Worker 独立进程执行 OCR 任务（`ocr.process_document` task）
- [ ] 输入：`ParsedDocument`（含 needs_ocr 标记）；输出：回填文本后的 `ParsedDocument`
- [ ] 扫描页渲染分辨率 ≥ 300 DPI（保证财报小字可识别）
- [ ] OCR 结果文本合并到对应 `ParsedPage.text` 和 `TextBlock.text`
- [ ] 中文 + 英文 + 数字混合识别准确率 ≥ 95%（基于 E7 Benchmark 财报样本）
- [ ] OCR 失败时标记页面 `error`，不阻塞其他页面继续处理
- [ ] OCR 任务进度通过 WebSocket 推送（event_type: `DocumentProcessing`，step: `OCR`）
- [ ] 超时保护：单页 OCR > 60s 触发 timeout，跳过并记录错误

## I/O 接口

```python
class OCRService(ABC):
    """OCR 服务抽象 — 对扫描页执行文字识别"""

    async def process(
        self,
        parsed_doc: ParsedDocument,
        document_id: str,
    ) -> ParsedDocument:
        """对 needs_ocr=True 的页面执行 OCR，回填文本。

        Args:
            parsed_doc: PDF Parser 产出的 ParsedDocument
            document_id: 关联的文档 ID

        Returns:
            文本回填后的 ParsedDocument（所有页面 needs_ocr=False）
        """
        ...

# Celery Task 签名
@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def ocr_process_document(
    self,
    parsed_doc_json: str,       # ParsedDocument.model_dump_json()
    document_id: str,
) -> str:                       # 返回 ParsedDocument.model_dump_json()
    ...
```

### OCR 结果合并策略

```
对于每个 needs_ocr=True 的 ParsedPage:
  1. page.render(dpi=300) → PIL.Image (RGB)
  2. paddleocr.ocr(image) → list[line_text, bbox, confidence]
  3. 按 bbox y 坐标排序（从上到下阅读顺序）
  4. 按行间距聚类为 TextBlock
  5. 回填 page.text + page.blocks
  6. page.needs_ocr = False
```
