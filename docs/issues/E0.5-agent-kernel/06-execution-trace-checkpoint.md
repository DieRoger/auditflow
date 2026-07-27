# 0.5.2.3 — Execution Trace + Checkpoint

- **Epic:** E0.5 Agent Kernel + Evaluation Core
- **Labels:** `agent-kernel`, `trace`
- **Depends on:** 0.5.2.2

## Description
实现 Agent 执行的全链路追踪与 Checkpoint 机制。每次 Agent 调用、Tool 调用、LLM 交互均需记录为 Execution Trace。Checkpoint 支持中断恢复与 Replay。

## Acceptance Criteria
- [ ] 100% 执行记录：每次 Agent.execute() / Tool 调用 / LLM 请求均自动记录
- [ ] ExecutionTrace 包含：trace_id / workflow_id / agent_name / step / timestamp / input / output / duration
- [ ] Checkpoint 机制：每个 Agent 完成后自动保存状态快照
- [ ] Checkpoint 可恢复：从任意 Checkpoint 重新启动 Workflow
- [ ] Replay 引擎：基于 Trace 重新执行并对比差异

## I/O Interface
```python
class ExecutionTrace(BaseModel):
    trace_id: str
    workflow_id: str
    agent_name: str
    step: int
    event_type: str              # AGENT_START | TOOL_CALL | LLM_REQUEST | AGENT_END
    timestamp: datetime
    input: dict
    output: dict | None
    duration_ms: int | None
    error: str | None

class Checkpoint(BaseModel):
    checkpoint_id: str
    workflow_id: str
    agent_name: str
    state_snapshot: dict         # 完整 Agent 状态
    created_at: datetime

class TraceStore(ABC):
    async def append(self, trace: ExecutionTrace) -> None: ...
    async def query(self, workflow_id: str) -> list[ExecutionTrace]: ...

class CheckpointStore(ABC):
    async def save(self, checkpoint: Checkpoint) -> None: ...
    async def load(self, workflow_id: str) -> Checkpoint | None: ...
    async def load_latest(self, workflow_id: str, agent_name: str) -> Checkpoint | None: ...
```

## Related ADR
N/A
