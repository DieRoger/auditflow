"""Document API 请求/响应模型"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    document_id: str
    task_id: str
    status: Literal["PENDING"]
    filename: str


class DocumentSummary(BaseModel):
    id: str
    project_id: str
    filename: str
    document_type: str
    status: str  # PENDING | PARSING | OCR | CHUNKING | EMBEDDING | READY | FAILED
    size_bytes: int = 0
    page_count: int = 0
    created_at: datetime


class DocumentListResponse(BaseModel):
    items: list[DocumentSummary]
    total: int
    page: int
    page_size: int


class DocumentDetailResponse(DocumentSummary):
    storage_path: str
    error_message: str | None = None
    updated_at: datetime | None = None
