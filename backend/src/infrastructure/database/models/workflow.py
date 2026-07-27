"""Workflow 持久化模型 — 执行轨迹 + Checkpoint 的 PostgreSQL 存储"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, func
from infrastructure.database.base import Base


class ExecutionTraceModel(Base):
    """执行轨迹 — 持久化到 PostgreSQL"""

    __tablename__ = "execution_traces"

    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex[:12])
    workflow_id = Column(String(36), nullable=False, index=True)
    agent_name = Column(String(100), nullable=False)
    step = Column(Integer, nullable=False)
    event_type = Column(String(30), nullable=False)
    input_data = Column(Text, nullable=True)
    output = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())


class CheckpointModel(Base):
    """Checkpoint — 持久化到 PostgreSQL"""

    __tablename__ = "workflow_checkpoints"

    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex[:12])
    workflow_id = Column(String(36), nullable=False, index=True)
    agent_name = Column(String(100), nullable=False)
    state_snapshot = Column(Text, nullable=False)  # JSON
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())
