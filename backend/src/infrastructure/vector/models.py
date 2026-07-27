"""Embedding 相关的数据模型."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

SourceType = Literal[
    "CLIENT_DOCUMENT",
    "AUDIT_STANDARD",
    "WORKPAPER",
    "RISK_CASE",
]

SecurityLevel = Literal[
    "PUBLIC",
    "INTERNAL",
    "CONFIDENTIAL",
    "RESTRICTED",
]


class EmbeddingItem(BaseModel):
    """统一向量存储条目

    所有向量化数据（文档 Chunk / 准则段落 / 底稿片段）使用此模型。
    """
    id: str
    firm_id: str
    client_id: str
    engagement_id: str
    source_type: SourceType
    source_id: str
    content: str
    embedding: list[float]
    metadata: dict = {}
    security_level: SecurityLevel = "INTERNAL"
    created_at: datetime = datetime.now()
