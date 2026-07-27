"""Audit Log Service — 不可变审计日志写入 + 查询

所有业务操作通过此 Service 记录不可变审计日志。
"""

import json
import structlog
from datetime import datetime

logger = structlog.get_logger(__name__)


class AuditLogService:
    """审计日志服务 — Append-Only"""

    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def log(self, user_id: str, tenant_id: str, action: str,
                  resource_type: str, resource_id: str, detail: dict = None,
                  ip_address: str = None) -> str:
        """写入审计日志"""
        from infrastructure.database.models.audit_log import AuditLog

        entry = AuditLog(
            user_id=user_id, tenant_id=tenant_id,
            action=action, resource_type=resource_type,
            resource_id=resource_id,
            detail=json.dumps(detail, ensure_ascii=False) if detail else None,
            ip_address=ip_address,
        )
        # 使用同步 session（简化 MVP，生产环境应改为异步）
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        import os
        db_url = os.getenv("DATABASE_URL", "sqlite:///dev.db").replace("+asyncpg", "").replace("+aiosqlite", "")
        engine = create_engine(db_url)
        from infrastructure.database.base import Base
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            session.add(entry)
            session.commit()
            log_id = entry.id
        engine.dispose()
        logger.info("audit_log_written", action=action, resource=resource_type, id=log_id)
        return log_id

    async def query(self, tenant_id: str, action: str = None,
                    resource_type: str = None, limit: int = 50) -> list:
        """查询审计日志"""
        from infrastructure.database.models.audit_log import AuditLog
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        import os
        db_url = os.getenv("DATABASE_URL", "sqlite:///dev.db").replace("+asyncpg", "").replace("+aiosqlite", "")
        engine = create_engine(db_url)
        with Session(engine) as session:
            query = session.query(AuditLog).filter(AuditLog.tenant_id == tenant_id)
            if action:
                query = query.filter(AuditLog.action == action)
            if resource_type:
                query = query.filter(AuditLog.resource_type == resource_type)
            results = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
        engine.dispose()
        return [r.to_dict() for r in results]
