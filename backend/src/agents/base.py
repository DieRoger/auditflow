"""Agent 基类 + ToolDefinition + AgentRegistry + ToolRegistry"""

from abc import ABC, abstractmethod
from collections.abc import Callable

from pydantic import BaseModel, Field

from domain.contracts import AgentRequest, AgentResponse

# ── Tool Definition ──────────────────────────────────────────────

class ToolDefinition(BaseModel):
    """Agent 工具的元数据定义"""
    name: str
    description: str
    parameters_schema: dict = Field(default_factory=dict, description="JSON Schema 格式参数定义")
    output_schema: dict = Field(default_factory=dict)
    category: str = "general"  # retrieval | document | calculator | ...


# ── Base Agent ──────────────────────────────────────────────────

class BaseAgent(ABC):
    """所有 Agent 必须实现的统一接口"""
    name: str = ""
    version: str = "v1"

    @abstractmethod
    async def execute(self, request: AgentRequest) -> AgentResponse:
        """统一执行入口"""
        ...

    @abstractmethod
    def get_tools(self) -> list[ToolDefinition]:
        """声明该 Agent 需要的工具"""
        ...


# ── Agent Registry ──────────────────────────────────────────────

class AgentRegistry:
    """Agent 注册表 — 按名称查找 Agent 实现"""

    def __init__(self) -> None:
        self._registry: dict[str, type[BaseAgent]] = {}

    def register(self, agent_class: type[BaseAgent]) -> None:
        name = agent_class.name
        if name in self._registry:
            raise ValueError(f"Agent '{name}' 已注册")
        self._registry[name] = agent_class

    def get(self, name: str) -> type[BaseAgent]:
        agent = self._registry.get(name)
        if agent is None:
            raise KeyError(f"Agent '{name}' 未注册")
        return agent

    def list_agents(self) -> list[str]:
        return list(self._registry.keys())


# ── 默认工具权限配置（ISO 14291 等价） ──────────────────────────

DEFAULT_AGENT_PERMISSIONS: dict[str, list[str]] = {
    "planner_agent": ["ontology_query", "agent_catalog"],
    "knowledge_agent": ["standard_search", "cross_reference"],
    "risk_agent": ["evidence_search", "standard_search", "calculator", "ontology_query"],
    "evidence_agent": ["client_doc_search", "structured_data_query"],
    "reviewer_agent": ["evidence_search", "standard_search", "grounding_checker"],
}

DEFAULT_TOOLS: dict[str, ToolDefinition] = {
    "ontology_query": ToolDefinition(
        name="ontology_query", description="查询审计本体推理链",
        category="retrieval",
    ),
    "agent_catalog": ToolDefinition(
        name="agent_catalog", description="列出可用 Agent 及能力",
        category="system",
    ),
    "standard_search": ToolDefinition(
        name="standard_search", description="检索审计准则/标准 ¶",
        category="retrieval",
    ),
    "cross_reference": ToolDefinition(
        name="cross_reference", description="查询准则间的交叉引用关系",
        category="retrieval",
    ),
    "evidence_search": ToolDefinition(
        name="evidence_search", description="从客户文档搜索审计证据",
        category="retrieval",
    ),
    "calculator": ToolDefinition(
        name="calculator", description="执行数值计算（重要性/抽样）",
        category="calculation",
    ),
    "client_doc_search": ToolDefinition(
        name="client_doc_search", description="检索客户文档内容",
        category="retrieval",
    ),
    "structured_data_query": ToolDefinition(
        name="structured_data_query", description="查询结构化数据（Excel/CSV/SQL）",
        category="retrieval",
    ),
    "grounding_checker": ToolDefinition(
        name="grounding_checker", description="验证 AI Claim 是否被 Citation 支持",
        category="evaluation",
    ),
}


# ── Tool Registry ──────────────────────────────────────────────

class ToolRegistry:
    """工具注册表 + 按 Agent 角色的权限控制"""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self._permissions: dict[str, list[str]] = {}
        self._executors: dict[str, callable] = {}

    def register_tool(self, tool: ToolDefinition, executor: Callable | None = None) -> None:
        """注册工具定义及可选的执行器"""
        self._tools[tool.name] = tool
        if executor:
            self._executors[tool.name] = executor

    def get_tool(self, name: str) -> ToolDefinition:
        """获取工具定义"""
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"Tool '{name}' 未注册")
        return tool

    def list_tools(self) -> list[str]:
        """列出所有已注册工具"""
        return list(self._tools.keys())

    def set_agent_permissions(self, agent_name: str, tool_names: list[str]) -> None:
        """设置 Agent 可用的工具白名单"""
        for tool_name in tool_names:
            if tool_name not in self._tools:
                raise ValueError(f"工具 '{tool_name}' 未注册，无法授权")
        self._permissions[agent_name] = tool_names

    def is_allowed(self, agent_name: str, tool_name: str) -> bool:
        """检查 Agent 是否有权限调用指定工具"""
        allowed = self._permissions.get(agent_name, [])
        return tool_name in allowed

    def list_by_agent(self, agent_name: str) -> list[ToolDefinition]:
        """列出 Agent 可调用的所有工具定义"""
        allowed = self._permissions.get(agent_name, [])
        return [self._tools[n] for n in allowed if n in self._tools]

    async def execute(self, agent_name: str, tool_name: str, params: dict) -> dict:
        """执行工具调用（含权限检查）"""
        if not self.is_allowed(agent_name, tool_name):
            raise PermissionError(f"Agent '{agent_name}' 无权调用工具 '{tool_name}'")
        executor = self._executors.get(tool_name)
        if executor is None:
            raise NotImplementedError(f"工具 '{tool_name}' 的执行器尚未注册")
        result = await executor(params) if callable(executor) else executor(params)
        return result

    @classmethod
    def create_default(cls) -> "ToolRegistry":
        """创建带默认配置的 ToolRegistry"""
        registry = cls()
        for _, tool in DEFAULT_TOOLS.items():
            registry.register_tool(tool)
        for agent_name, tool_names in DEFAULT_AGENT_PERMISSIONS.items():
            registry.set_agent_permissions(agent_name, tool_names)
        return registry
