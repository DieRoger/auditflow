"""Audit Log — 不可变审计日志模型

所有业务操作必须记录不可变审计日志。
日志仅追加（Append-Only），禁止更新或删除。
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text, func
from infrastructure.database.base import Base


class AuditLog(Base):
    """审计日志 — Append-Only 不可变记录"""

    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex[:12])
    user_id = Column(String(36), nullable=False, index=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)  # e.g. document_uploaded, workflow_started
    resource_type = Column(String(50), nullable=False)  # e.g. document, workflow, risk
    resource_id = Column(String(36), nullable=False)
    detail = Column(Text, nullable=True)  # JSON string
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "detail": self.detail,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
