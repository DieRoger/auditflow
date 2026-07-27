# ruff: noqa: B008
"""Document API Router — 上传/列表/详情/删除"""

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from api.schemas.document import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentSummary,
    DocumentUploadResponse,
)
from infrastructure.database.models import Document
from infrastructure.storage import MinIOStorage, ObjectStorage
from shared.logging import get_logger

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])
logger = get_logger(__name__)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_TYPES = {"application/pdf"}


def get_storage() -> ObjectStorage:
    import os
    return MinIOStorage(
        endpoint=os.getenv("MINIO_ENDPOINT", "localhost:9000"),
        access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
    )


def _get_db_url() -> str:
    """从环境变量获取数据库 URL，移除异步驱动前缀"""
    import os
    url = os.getenv("DATABASE_URL", "sqlite:///dev.db")
    return url.replace("+asyncpg", "").replace("+aiosqlite", "")


def _get_db_session():
    """创建同步数据库 session"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from infrastructure.database.base import Base
    engine = create_engine(_get_db_url())
    Base.metadata.create_all(engine)
    return Session(engine)


@router.post("", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    project_id: str = Form(...),
    firm_id: str = Form("default"),
    engagement_id: str = Form("default"),  # noqa: ARG001 — reserved for future tenant isolation
    document_type: str = Form("financial_report"),
    storage: ObjectStorage = Depends(get_storage),
):
    # 文件验证
    if file.content_type and file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"不支持的文件类型: {file.content_type}")
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "文件超过 50MB 限制")

    # 存入 MinIO
    doc_id = uuid.uuid4().hex[:12]
    task_id = uuid.uuid4().hex[:12]
    path = await storage.upload(firm_id, project_id, "documents", f"{doc_id}.pdf", content)

    # 数据库记录
    doc = Document(
        id=doc_id,
        tenant_id=firm_id,
        project_id=project_id,
        filename=file.filename or "unnamed.pdf",
        document_type=document_type,
        storage_path=path.path,
        status="PENDING",
    )
    with _get_db_session() as session:
        session.add(doc)
        session.commit()

    logger.info("document_uploaded", doc_id=doc_id, project_id=project_id, size=len(content))
    return DocumentUploadResponse(document_id=doc_id, task_id=task_id, status="PENDING", filename=file.filename or "")


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    project_id: str = Query(...),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    with _get_db_session() as session:
        query = session.query(Document).filter(Document.project_id == project_id)
        if status:
            query = query.filter(Document.status == status)
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
    return DocumentListResponse(
        items=[DocumentSummary(id=d.id, project_id=d.project_id, filename=d.filename,
                document_type=d.document_type, status=d.status, size_bytes=0,
                page_count=0, created_at=d.created_at) for d in items],
        total=total, page=page, page_size=page_size,
    )


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(document_id: str):
    with _get_db_session() as session:
        doc = session.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise HTTPException(404, "文档不存在")
        return DocumentDetailResponse(
            id=doc.id, project_id=doc.project_id, filename=doc.filename,
            document_type=doc.document_type, status=doc.status, size_bytes=0,
            page_count=0, created_at=doc.created_at, storage_path=doc.storage_path,
        )
