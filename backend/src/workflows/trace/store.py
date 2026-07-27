"""Execution Trace 模型 + TraceStore / CheckpointStore"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel, Field

# ── Execution Trace ──────────────────────────────────────────────

class ExecutionTrace(BaseModel):
    """单步 Agent 执行的完整记录"""
    trace_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    workflow_id: str
    agent_name: str
    step: int = 0
    event_type: str  # AGENT_START | TOOL_CALL | LLM_REQUEST | AGENT_COMPLETE | AGENT_FAIL
    timestamp: datetime = Field(default_factory=datetime.now)
    input: dict = Field(default_factory=dict)
    output: dict | None = None
    duration_ms: int | None = None
    error: str | None = None


class TraceStore(ABC):
    @abstractmethod
    async def append(self, trace: ExecutionTrace) -> None: ...
    @abstractmethod
    async def query(self, workflow_id: str) -> list[ExecutionTrace]: ...
    @abstractmethod
    async def replay(self, workflow_id: str) -> list[dict]: ...


class InMemoryTraceStore(TraceStore):
    def __init__(self):
        self._traces: list[ExecutionTrace] = []
        self._seq: dict[str, int] = {}

    async def append(self, trace: ExecutionTrace) -> None:
        self._seq[trace.workflow_id] = self._seq.get(trace.workflow_id, 0) + 1
        trace.step = self._seq[trace.workflow_id]
        self._traces.append(trace)

    async def query(self, workflow_id: str) -> list[ExecutionTrace]:
        return [t for t in self._traces if t.workflow_id == workflow_id]

    async def replay(self, workflow_id: str) -> list[dict]:
        traces = await self.query(workflow_id)
        return [{
            "step": t.step, "agent": t.agent_name,
            "event": t.event_type, "duration_ms": t.duration_ms,
            "error": t.error,
        } for t in traces]


# ── Checkpoint ──────────────────────────────────────────────────

class Checkpoint(BaseModel):
    """Workflow 状态快照"""
    checkpoint_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    workflow_id: str
    agent_name: str
    node_id: str = ""
    state_snapshot: dict = Field(default_factory=dict)
    seq: int = 0
    created_at: datetime = Field(default_factory=datetime.now)


class CheckpointStore(ABC):
    @abstractmethod
    async def save(self, checkpoint: Checkpoint) -> None: ...
    @abstractmethod
    async def load(self, checkpoint_id: str) -> Checkpoint | None: ...
    @abstractmethod
    async def load_latest(self, workflow_id: str) -> Checkpoint | None: ...


class InMemoryCheckpointStore(CheckpointStore):
    def __init__(self):
        self._checkpoints: dict[str, Checkpoint] = {}
        self._seq: dict[str, int] = {}

    async def save(self, checkpoint: Checkpoint) -> None:
        self._seq[checkpoint.workflow_id] = self._seq.get(checkpoint.workflow_id, 0) + 1
        checkpoint.seq = self._seq[checkpoint.workflow_id]
        self._checkpoints[checkpoint.checkpoint_id] = checkpoint

    async def load(self, checkpoint_id: str) -> Checkpoint | None:
        return self._checkpoints.get(checkpoint_id)

    async def load_latest(self, workflow_id: str) -> Checkpoint | None:
        matches = {k: v for k, v in self._checkpoints.items() if v.workflow_id == workflow_id}
        if not matches:
            return None
        return max(matches.values(), key=lambda c: c.seq)
