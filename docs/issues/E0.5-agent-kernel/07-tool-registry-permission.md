# 0.5.2.4 — Tool Registry + Permission

- **Epic:** E0.5 Agent Kernel + Evaluation Core
- **Labels:** `agent-kernel`, `tool`
- **Depends on:** 0.5.2.1

## Description
实现 Tool Registry——统一管理所有 Agent 可调用的工具，按 Agent 角色配置权限。每个 Agent 只能调用其 Role 白名单内的 Tools。

各 Agent 工具权限：
- Planner Agent: `ontology_query`, `agent_catalog`
- Knowledge Agent: `standard_search`, `cross_reference`
- Risk Agent: `evidence_search`, `standard_search`, `calculator`, `ontology_query`
- Evidence Agent: `client_doc_search`, `structured_data_query`
- Reviewer Agent: `evidence_search`, `standard_search`, `grounding_checker`

## Acceptance Criteria
- [ ] ToolDefinition: name / description / parameters_schema / required_permissions
- [ ] ToolRegistry: register / get / list_by_agent(agent_name)
- [ ] Agent 调用不在白名单内的 Tool → 拒绝并记录
- [ ] 权限配置文件独立于代码（YAML）
- [ ] Tool 调用自动记录到 ExecutionTrace

## I/O Interface
```python
class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters_schema: dict       # JSON Schema
    required_permissions: list[str]

class ToolRegistry:
    _tools: dict[str, ToolDefinition] = {}
    _permissions: dict[str, list[str]] = {}  # agent_name → [tool_names]

    def register(self, tool: ToolDefinition) -> None: ...
    def get(self, name: str) -> ToolDefinition: ...
    def list_by_agent(self, agent_name: str) -> list[ToolDefinition]: ...
    def is_allowed(self, agent_name: str, tool_name: str) -> bool: ...
```

```yaml
# tool_permissions.yaml
planner_agent: [ontology_query, agent_catalog]
knowledge_agent: [standard_search, cross_reference]
risk_agent: [evidence_search, standard_search, calculator, ontology_query]
evidence_agent: [client_doc_search, structured_data_query]
reviewer_agent: [evidence_search, standard_search, grounding_checker]
```

## Related ADR
N/A
