"""Agent Contract — 全项目基础通信协议

所有 Agent 必须遵守此 Contract。
Architecture Baseline v1.0 冻结，E0.5 锁定后不可变。
"""

from typing import Literal

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """证据引用

    AI 输出的每条断言必须附带 Citation。
    无 Citation 的输出视为无效。
    """
    claim: str = Field(description="被引用的断言")
    document_id: str = Field(description="源文档 ID")
    page: int | None = Field(default=None, description="页码")
    chunk_id: str | None = Field(default=None, description="Chunk ID")
    excerpt: str = Field(description="引用原文片段")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="引用可信度")


class AgentRequest(BaseModel):
    """所有 Agent 的标准输入"""
    workflow_id: str
    project_id: str
    task_id: str
    firm_id: str
    client_id: str
    engagement_id: str
    context: dict = Field(default_factory=dict, description="上游 Agent 产出（共享记忆）")
    inputs: dict = Field(default_factory=dict, description="本 Agent 特定输入")
    memory: dict = Field(default_factory=dict, description="长期记忆/偏好")


class AgentResponse(BaseModel):
    """所有 Agent 的标准输出"""
    status: Literal["SUCCESS", "PARTIAL", "FAILED", "NEEDS_HUMAN"]
    result: dict = Field(default_factory=dict, description="Agent 产出")
    citations: list[Citation] = Field(default_factory=list, description="证据引用")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    metrics: dict = Field(default_factory=dict, description="token/cost/latency")
    next_action: str = Field(default="", description="给 Workflow Engine 的指令")


class AgentError(BaseModel):
    """Agent 错误响应"""
    status: Literal["FAILED"] = "FAILED"
    reason: str
    recoverable: bool = Field(description="True → 重试, False → 人工介入")
    retry_context: dict | None = None
