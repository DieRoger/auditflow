# 0.5.1.1 — AgentRequest / AgentResponse / Citation

- **Epic:** E0.5 Agent Kernel + Evaluation Core
- **Labels:** `agent-kernel`, `contract`
- **Depends on:** 0.1.1

## Description
基础 Contract（见 ISSUES.md §Agent Contract v1 — 基础 Contract）。定义 Agent 间通信的核心数据模型：AgentRequest 包含 workflow/project/task/firm/client/engagement 上下文、inputs 与 memory；AgentResponse 包含状态、结果、citations、置信度、metrics 与 next_action。

## Acceptance Criteria
- [ ] AgentRequest 包含 workflow_id / project_id / task_id / firm_id / client_id / engagement_id / context / inputs / memory
- [ ] AgentResponse 包含 status (SUCCESS | PARTIAL | FAILED | NEEDS_HUMAN) / result / citations / confidence / metrics / next_action
- [ ] Citation 类型定义（包含 source / content / relevance 等字段）
- [ ] Pydantic BaseModel 序列化/反序列化验证通过
- [ ] 所有 5 Agent 的 execute() 签名统一使用此 Contract

## I/O Interface
```python
class AgentRequest(BaseModel):
    workflow_id: str
    project_id: str
    task_id: str
    firm_id: str
    client_id: str
    engagement_id: str
    context: dict
    inputs: dict
    memory: dict

class AgentResponse(BaseModel):
    status: Literal["SUCCESS", "PARTIAL", "FAILED", "NEEDS_HUMAN"]
    result: dict
    citations: list[Citation]
    confidence: float
    metrics: dict
    next_action: str
```

## Related ADR
ADR-001 — Agent Contract v1
