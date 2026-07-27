# 0.5.2.1 — Agent Base + Registry

- **Epic:** E0.5 Agent Kernel + Evaluation Core
- **Labels:** `agent-kernel`, `runtime`
- **Depends on:** 0.5.1.1

## Description
定义 BaseAgent 抽象基类——所有 Agent 的统一入口。包含 name、version、execute() 方法和 get_tools() 方法。Agent Registry 负责按名称发现和注册 Agent 实现。

## Acceptance Criteria
- [ ] BaseAgent(ABC) 定义 name: str / version: str
- [ ] async execute(request: AgentRequest) -> AgentResponse 抽象方法
- [ ] get_tools() -> list[ToolDefinition] 抽象方法
- [ ] AgentRegistry 支持 register / get / list 操作
- [ ] 按 agent_name 动态发现 Agent 实现

## I/O Interface
```python
class BaseAgent(ABC):
    name: str
    version: str

    @abstractmethod
    async def execute(self, request: AgentRequest) -> AgentResponse:
        ...

    @abstractmethod
    def get_tools(self) -> list[ToolDefinition]:
        ...

class AgentRegistry:
    _agents: dict[str, type[BaseAgent]] = {}

    def register(self, agent_class: type[BaseAgent]) -> None: ...
    def get(self, name: str) -> type[BaseAgent]: ...
    def list_agents(self) -> list[str]: ...
```

## Related ADR
ADR-001 — Agent Contract v1
