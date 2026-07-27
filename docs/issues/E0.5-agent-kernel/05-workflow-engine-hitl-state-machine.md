# 0.5.2.2 — Workflow Engine + HITL 状态机

- **Epic:** E0.5 Agent Kernel + Evaluation Core
- **Labels:** `agent-kernel`, `workflow`, `hitl`
- **Depends on:** 0.5.2.1

## Description
实现 Workflow Engine 与 Human-In-The-Loop (HITL) 状态机。Workflow Engine 基于 Agent DAG 编排执行流程，HITL 状态机管理审批中断、回退、重试与超时取消。

状态机流转：
```
CREATED → QUEUED → RUNNING → WAITING_APPROVAL → (APPROVED→RUNNING | REJECTED→回退) → COMPLETED
                   → RETRYING(≤3) → FAILED
                   → FAILED(不可恢复)
                   72h 超时 → CANCELLED
```

## Acceptance Criteria
- [ ] WorkflowEngine: create(graph_def) / start / pause / resume / request_approval / submit_decision
- [ ] ApprovalDecision: workflow_id / reviewer_id / decision (APPROVED|REJECTED|MODIFY) / comment / modifications
- [ ] HITL 状态机完整流转：CREATED → QUEUED → RUNNING → WAITING_APPROVAL → COMPLETED
- [ ] WAITING_APPROVAL 支持 APPROVED / REJECTED / MODIFY 三种决策
- [ ] REJECTED 时回退到指定上游 Agent 重新执行
- [ ] 自动重试 ≤3 次后 → FAILED
- [ ] 72 小时超时 → CANCELLED
- [ ] 状态变更触发对应 WorkflowEvent

## I/O Interface
```python
class WorkflowEngine:
    async def create(self, graph_def: GraphDefinition) -> str:
        """创建 Workflow 实例，返回 workflow_id"""
        ...

    async def start(self, workflow_id: str) -> None: ...
    async def pause(self, workflow_id: str) -> None: ...
    async def resume(self, workflow_id: str) -> None: ...
    async def request_approval(self, workflow_id: str, agent_response: AgentResponse) -> None: ...
    async def submit_decision(self, workflow_id: str, decision: ApprovalDecision) -> None: ...

class ApprovalDecision(BaseModel):
    workflow_id: str
    reviewer_id: str
    decision: Literal["APPROVED", "REJECTED", "MODIFY"]
    comment: str
    modifications: dict | None

class GraphDefinition(BaseModel):
    nodes: list[AgentNode]
    edges: list[Edge]
    entry_point: str
```

## Related ADR
ADR-001 — Agent Contract v1
