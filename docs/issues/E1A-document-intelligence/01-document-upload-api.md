# 1A.1.1 — Document Upload API
- **Epic:** E1A Document Intelligence
- **Labels:** `api`, `document`, `phase-1a`
- **Depends on:** 0.2.2 (MinIO Object Storage)

## 描述

实现文档上传 REST API。客户端通过 `POST /api/v1/documents` 提交 PDF 财报文档（支持分块上传），后端接收后存入 MinIO 对象存储，创建异步处理任务（Celery），返回 `task_id` 并通过 WebSocket 实时推送处理进度（`PENDING → PARSING → OCR → CHUNKING → EMBEDDING → READY`）。

GET 端点支持按项目分页查询文档列表，包含文件名、大小、上传时间、处理状态、页数等摘要信息。

这是 E1A 的入口 API — 冻结后前端 Document Center 才可开始消费。

## Acceptance Criteria

- [ ] `POST /api/v1/documents` 接受 multipart/form-data 上传（PDF ≤ 50MB）
- [ ] 文件通过 ObjectStorage.upload() 写入 MinIO，路径 `{tenant_id}/{project_id}/documents/{uuid}.pdf`
- [ ] 数据库记录 documents 表行（id / project_id / filename / size / status / created_at）
- [ ] 返回 `{ document_id, task_id, status: "PENDING" }`
- [ ] Celery 异步任务链下发：Parse → OCR（如需）→ Chunk → Embed
- [ ] WebSocket 推送事件：`DocumentUploaded` / `DocumentProcessing` / `DocumentReady` / `DocumentFailed`
- [ ] `GET /api/v1/documents?project_id=...` 分页列表 + 状态过滤
- [ ] `GET /api/v1/documents/{id}` 返回文档详情 + 最新状态
- [ ] `DELETE /api/v1/documents/{id}` 级联清理 MinIO 文件 + documents 行
- [ ] 所有端点注入 `firm_id` + `engagement_id` 隔离（租户 + 委托双层）

## I/O 接口

```python
# POST /api/v1/documents
class DocumentUploadResponse(BaseModel):
    document_id: str
    task_id: str
    status: Literal["PENDING"]
    filename: str

# GET /api/v1/documents?project_id=...&status=...&page=1&page_size=20
class DocumentListResponse(BaseModel):
    items: list[DocumentSummary]
    total: int
    page: int
    page_size: int

class DocumentSummary(BaseModel):
    document_id: str
    filename: str
    size_bytes: int
    status: Literal["PENDING", "PARSING", "OCR", "CHUNKING", "EMBEDDING", "READY", "FAILED"]
    page_count: int | None
    created_at: datetime

# GET /api/v1/documents/{id}
class DocumentDetailResponse(DocumentSummary):
    metadata: DocumentMetadata | None
    chunk_count: int | None
    error_message: str | None
```
