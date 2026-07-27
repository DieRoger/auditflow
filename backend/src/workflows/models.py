"""Workflow 数据模型 — Graph / State / Approval"""

from typing import Literal

from pydantic import BaseModel, Field


class AgentNode(BaseModel):
    """Workflow 图中的一个 Agent 节点"""
    id: str
    agent_name: str
    input_mapping: dict = Field(default_factory=dict, description="将上游输出映射为本节点输入")
    retry_policy: dict | None = None
    timeout_seconds: int = 300


class Edge(BaseModel):
    """节点间的有向边"""
    source: str  # 源节点 ID
    target: str  # 目标节点 ID
    condition: str | None = None  # 条件表达式（如 "risk.level == HIGH → approval"）


class GraphDefinition(BaseModel):
    """完整的 Workflow Graph 定义"""
    nodes: list[AgentNode]
    edges: list[Edge]
    entry_point: str
    end_nodes: list[str] = Field(default_factory=list)


class ApprovalDecision(BaseModel):
    """人工审批决策"""
    workflow_id: str
    reviewer_id: str
    decision: Literal["APPROVED", "REJECTED", "MODIFY"]
    comment: str = ""
    modifications: dict | None = None


class WorkflowState(BaseModel):
    """Workflow 运行时状态"""
    workflow_id: str
    project_id: str = ""
    status: str = "CREATED"  # CREATED | QUEUED | RUNNING | WAITING_APPROVAL | RETRYING | FAILED | COMPLETED | CANCELLED
    current_node: str = ""
    agent_results: dict[str, dict] = Field(default_factory=dict)
    error: str | None = None
    retry_count: int = 0
    created_at: str = ""
    updated_at: str = ""
