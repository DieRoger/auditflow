# 0.5.1.3 — Event Contract

- **Epic:** E0.5 Agent Kernel + Evaluation Core
- **Labels:** `agent-kernel`, `contract`
- **Depends on:** 0.5.1.1

## Description
WorkflowEvent 定义 + 16 个事件类型（见 ISSUES.md §Event Contract）。所有 Workflow 状态变更必须有对应 Event，通过 WebSocket 推送前端 + 数据库持久化。Event 不可变。

事件类型（v3.2 冻结）：
- AgentStarted / AgentThinking / ToolCalled / ToolCompleted
- RetrievalCompleted / EvidenceFound / ArtifactCreated / RiskDetected
- AgentCompleted / AgentFailed / ApprovalRequired / ApprovalSubmitted
- WorkflowPaused / WorkflowResumed / WorkflowCompleted / WorkflowFailed

## Acceptance Criteria
- [ ] WorkflowEvent：event_id / workflow_id / event_type / timestamp / payload
- [ ] 16 种事件类型全部定义（枚举 + payload schema）
- [ ] 所有 Workflow 状态变更必须有对应 Event
- [ ] WebSocket 推送 + 数据库持久化
- [ ] Event 不可变（Append-Only 写入）

## I/O Interface
```python
class WorkflowEvent(BaseModel):
    event_id: str
    workflow_id: str
    event_type: str             # 16 种事件类型
    timestamp: datetime
    payload: dict

# 事件类型枚举（v3.2 冻结 — 16 种事件）
# AgentStarted        → {agent_name, task_summary}
# AgentThinking       → {agent_name, step_description}
# ToolCalled          → {agent_name, tool_name, params_summary}
# ToolCompleted       → {agent_name, tool_name, result_summary, duration_ms}
# RetrievalCompleted  → {query, hit_count, top_score}
# EvidenceFound       → {evidence_id, claim, source_summary}
# ArtifactCreated     → {artifact_id, artifact_type, created_by}
# RiskDetected        → {risk_id, area, severity}
# AgentCompleted      → {agent_name, duration_ms, tokens, confidence}
# AgentFailed         → {agent_name, error_type, retry_count, recoverable}
# ApprovalRequired    → {approval_id, agent_name, severity, summary}
# ApprovalSubmitted   → {approval_id, decision, comment}
# WorkflowPaused      → {reason}
# WorkflowResumed     → {}
# WorkflowCompleted   → {total_duration, total_tokens, total_cost}
# WorkflowFailed      → {error, recoverable}
```

## Related ADR
ADR-001 — Agent Contract v1 (Event)
