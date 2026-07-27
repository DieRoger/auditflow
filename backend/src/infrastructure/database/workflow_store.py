"""PostgreSQL 持久化的 TraceStore + CheckpointStore

实现 TraceStore / CheckpointStore 接口，使用 SQLAlchemy + PostgreSQL。
"""

import json
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from workflows.trace import Checkpoint, CheckpointStore, ExecutionTrace, TraceStore


class PgTraceStore(TraceStore):
    """PostgreSQL 持久化的 TraceStore"""

    def __init__(self, db_url: str = None):
        import os
        self._db_url = db_url or os.getenv("DATABASE_URL", "sqlite:///dev.db")
        self._db_url = self._db_url.replace("+asyncpg", "").replace("+aiosqlite", "")
        self._engine = create_engine(self._db_url)
        from infrastructure.database.models.workflow import ExecutionTraceModel
        from infrastructure.database.base import Base
        Base.metadata.create_all(self._engine)

    async def append(self, trace: ExecutionTrace) -> None:
        from infrastructure.database.models.workflow import ExecutionTraceModel as M
        with Session(self._engine) as session:
            entry = M(
                workflow_id=trace.workflow_id, agent_name=trace.agent_name,
                step=trace.step, event_type=trace.event_type,
                input_data=json.dumps(trace.input, ensure_ascii=False) if trace.input else None,
                output=json.dumps(trace.output, ensure_ascii=False) if trace.output else None,
                duration_ms=trace.duration_ms, error=trace.error,
            )
            session.add(entry)
            session.commit()

    async def query(self, workflow_id: str) -> list[ExecutionTrace]:
        from infrastructure.database.models.workflow import ExecutionTraceModel as M
        with Session(self._engine) as session:
            rows = session.query(M).filter(M.workflow_id == workflow_id).order_by(M.step).all()
        return [
            ExecutionTrace(
                workflow_id=r.workflow_id, agent_name=r.agent_name,
                step=r.step, event_type=r.event_type,
                input=json.loads(r.input_data) if r.input_data else {},
                output=json.loads(r.output) if r.output else {},
                duration_ms=r.duration_ms, error=r.error,
            ) for r in rows
        ]

    async def replay(self, workflow_id: str) -> list[dict]:
        traces = await self.query(workflow_id)
        return [{"agent": t.agent_name, "event": t.event_type, "step": t.step,
                 "duration_ms": t.duration_ms, "error": t.error} for t in traces]


class PgCheckpointStore(CheckpointStore):
    """PostgreSQL 持久化的 CheckpointStore"""

    def __init__(self, db_url: str = None):
        import os
        self._db_url = db_url or os.getenv("DATABASE_URL", "sqlite:///dev.db")
        self._db_url = self._db_url.replace("+asyncpg", "").replace("+aiosqlite", "")
        self._engine = create_engine(self._db_url)
        from infrastructure.database.models.workflow import CheckpointModel
        from infrastructure.database.base import Base
        Base.metadata.create_all(self._engine)

    async def save(self, checkpoint: Checkpoint) -> None:
        from infrastructure.database.models.workflow import CheckpointModel as M
        with Session(self._engine) as session:
            entry = M(
                workflow_id=checkpoint.workflow_id, agent_name=checkpoint.agent_name,
                state_snapshot=json.dumps(checkpoint.state_snapshot, ensure_ascii=False),
            )
            session.add(entry)
            session.commit()

    async def load_latest(self, workflow_id: str) -> Checkpoint | None:
        from infrastructure.database.models.workflow import CheckpointModel as M
        with Session(self._engine) as session:
            row = session.query(M).filter(M.workflow_id == workflow_id).order_by(M.created_at.desc()).first()
        if not row:
            return None
        return Checkpoint(
            workflow_id=row.workflow_id, agent_name=row.agent_name,
            state_snapshot=json.loads(row.state_snapshot),
        )

    async def exists(self, workflow_id: str) -> bool:
        from infrastructure.database.models.workflow import CheckpointModel as M
        with Session(self._engine) as session:
            row = session.query(M).filter(M.workflow_id == workflow_id).first()
        return row is not None
