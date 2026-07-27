# 01 — Workflow Engine 接管 5 Agent

**父 Issue：** E3.5 System Bring-up
**优先级：** P0
**预计工作量：** 2-3 天

## 当前状态

`demo_v0.py` 硬编码调用链：

```python
agents = {planner: LlmPlannerAgent(), knowledge: LlmKnowledgeAgent(), ...}
r = await agents["planner"].execute(...)
ctx["planner_output"] = r.result
r = await agents["knowledge"].execute(...)
# ...
```

**问题：**
- Agent 直接 `new` 实例化，跳过 AgentRegistry
- Tool 不经过 ToolRegistry 权限检查
- Context 手工传递，不经过 Workflow State
- 无 Event Bus、无 Trace 记录
- Reviewer 返回后无后续处理

## 目标

将上述链路改为 Workflow Engine 驱动：

```
WorkflowEngine
  ├── create(GraphDefinition)
  ├── start(workflow_id)
  │   ├── Node: planner_agent  ──→ AgentRegistry.get("planner_agent")
  │   ├── Node: knowledge_agent ──→ AgentRegistry.get("knowledge_agent")
  │   ├── Node: risk_agent      ──→ AgentRegistry.get("risk_agent")
  │   ├── Node: evidence_agent  ──→ AgentRegistry.get("evidence_agent")
  │   └── Node: reviewer_agent  ──→ AgentRegistry.get("reviewer_agent")
  └── 结果：完整 Audit Trail JSON
```

## 验收标准

### 必须通过（5 项）

1. **Agent 注册。** 5 个 Agent 通过 `AgentRegistry.register()` 注册，Workflow Engine 通过名称查找。不允许直接 `new XxxAgent()`。
2. **Tool 权限。** 每个 Agent 的 Tool 调用经过 `ToolRegistry.is_allowed()` 检查。
3. **Context 流转。** Agent 之间的上下文通过 `WorkflowState.context` 传递，不通过手动 `ctx["key"] = ...`。
4. **事件记录。** 管线执行过程中产生 `event_agent_started` / `event_agent_completed` 事件。
5. **Trace 记录。** 每次 Agent 调用的 input/output/duration 写入 `ExecutionTrace`。

### 应该通过（3 项）

6. **HITL 暂停/恢复。** Reviewer 返回 NEEDS_HUMAN 时管线暂停，人工审批后恢复。
7. **Checkpoint 恢复。** 管线中断后可从最近 Checkpoint 恢复。
8. **错误处理。** 任一 Agent 返回 FAILED 时管线优雅终止并记录错误。

## 产出物

1. `scripts/bringup.py` — 可重现运行的系统集成脚本
2. `tests/integration/test_workflow_5_agent.py` — 集成测试
3. 更新 `AgentRegistry` 以确保 5 个 Agent 均注册

## 不做的事

- 不修改 Agent 的 Prompt
- 不修改 Agent 的业务逻辑
- 不新增 Workflow Engine 功能（充分使用现有 API）
