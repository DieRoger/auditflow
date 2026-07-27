"""Tenant 模型 — 审计组织/客户"""

import uuid

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, TimestampMixin


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
