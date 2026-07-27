# 0.5.4.1 — Mock 5 Agent 闭环

- **Epic:** E0.5 Agent Kernel + Evaluation Core
- **Labels:** `agent-kernel`, `vertical-slice`
- **Depends on:** 0.5.2.2, 0.3.1, 0.3.2

## Description
实现 Mock 5 Agent 完整闭环——项目第一个可演示里程碑。5 个 Mock Agent（Planner / Knowledge / Risk / Evidence / Reviewer）全部实现 Agent Contract + Artifact Contract，通过 Workflow Engine 串联执行，HITL 状态机完整流转，所有 Event 类型触发并持久化。

流程：Planner → Knowledge → Risk → Evidence → Reviewer → WAITING_APPROVAL

全部 Contract 在此 Issue 完成后冻结（Agent Contract v1 Freeze）。

## Acceptance Criteria
- [ ] 5 Mock Agent 全部实现 BaseAgent.execute() + Agent Contract + Artifact Contract
- [ ] Planner Agent → 拆解审计任务 → 输出 AuditPlanArtifact
- [ ] Knowledge Agent → 检索审计准则 → 输出 KnowledgePackageArtifact
- [ ] Risk Agent → 识别风险 + 评级 → 输出 RiskFindingArtifact
- [ ] Evidence Agent → 证据收集封装 → 输出 EvidencePackageArtifact
- [ ] Reviewer Agent → 审查所有 Artifact → 输出 ReviewReportArtifact
- [ ] Workflow Engine 串联完整 DAG：Planner → Knowledge → Risk → Evidence → Reviewer
- [ ] HITL 状态机完整流转至 WAITING_APPROVAL
- [ ] 16 种 Event 类型全部触发并持久化
- [ ] Mock Agent 使用 LLM Adapter（0.3.1）+ 真实 Tool 调用（Mock 实现即可）
- [ ] 项目第一个可演示里程碑
- [ ] **全部 Contract 在此 Issue 完成后冻结**

## I/O Interface
```python
# Mock Planner Agent
class MockPlannerAgent(BaseAgent):
    name = "planner"
    version = "0.1.0"

    async def execute(self, request: AgentRequest) -> AgentResponse:
        # 基于审计目标拆解子任务
        ...
        return AgentResponse(
            status="SUCCESS",
            result={"plan": artifact.dict()},
            citations=[...],
            confidence=0.9,
            metrics={"task_count": 3},
            next_action="KNOWLEDGE_AGENT"
        )

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(name="ontology_query", ...),
            ToolDefinition(name="agent_catalog", ...),
        ]

# 其余 4 个 Mock Agent 类似结构
# 关键：所有 Agent.execute() 必须返回 AgentResponse，产出必须是 Artifact 子类型
```

## Related ADR
ADR-001 — Agent Contract v1（此 Issue 完成后冻结）
