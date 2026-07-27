# ruff: noqa: E501
"""Event Contract — Workflow 事件定义与持久化

所有 Workflow 状态变更必有对应 Event。
Event 不可变，Append-Only 写入 agent_execution_log。
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class EventType(StrEnum):
    """16 种事件类型（v3.2 冻结）"""
    # Agent 级事件
    AGENT_STARTED = "agent_started"
    AGENT_THINKING = "agent_thinking"
    TOOL_CALLED = "tool_called"
    TOOL_COMPLETED = "tool_completed"
    RETRIEVAL_COMPLETED = "retrieval_completed"
    EVIDENCE_FOUND = "evidence_found"
    ARTIFACT_CREATED = "artifact_created"
    RISK_DETECTED = "risk_detected"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    # 审批相关
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_SUBMITTED = "approval_submitted"
    # 工作流生命周期
    WORKFLOW_PAUSED = "workflow_paused"
    WORKFLOW_RESUMED = "workflow_resumed"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"


class WorkflowEvent(BaseModel):
    """所有 Workflow 事件的标准格式"""
    event_id: str
    workflow_id: str
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.now)
    payload: dict = Field(default_factory=dict)

    def to_log_entry(self) -> dict:
        """转换为 agent_execution_log 的存储格式"""
        return {
            "workflow_id": self.workflow_id,
            "agent_name": self.payload.get("agent_name", ""),
            "event_type": self.event_type.value,
            "payload": self.model_dump(mode="json"),
        }


# ── 事件 Payload 工厂函数 ────────────────────────────────────────

def event_agent_started(event_id: str, workflow_id: str, agent_name: str, task_summary: str) -> WorkflowEvent:
    return WorkflowEvent(
        event_id=event_id, workflow_id=workflow_id,
        event_type=EventType.AGENT_STARTED,
        payload={"agent_name": agent_name, "task_summary": task_summary},
    )


def event_agent_thinking(event_id: str, workflow_id: str, agent_name: str, step_description: str) -> WorkflowEvent:
    return WorkflowEvent(
        event_id=event_id, workflow_id=workflow_id,
        event_type=EventType.AGENT_THINKING,
        payload={"agent_name": agent_name, "step_description": step_description},
    )


def event_tool_called(event_id: str, workflow_id: str, agent_name: str, tool_name: str, params_summary: str) -> WorkflowEvent:
    return WorkflowEvent(
        event_id=event_id, workflow_id=workflow_id,
        event_type=EventType.TOOL_CALLED,
        payload={"agent_name": agent_name, "tool_name": tool_name, "params_summary": params_summary},
    )


def event_tool_completed(event_id: str, workflow_id: str, agent_name: str, tool_name: str, result_summary: str, duration_ms: int) -> WorkflowEvent:
    return WorkflowEvent(
        event_id=event_id, workflow_id=workflow_id,
        event_type=EventType.TOOL_COMPLETED,
        payload={"agent_name": agent_name, "tool_name": tool_name, "result_summary": result_summary, "duration_ms": duration_ms},
    )


def event_retrieval_completed(event_id: str, workflow_id: str, query: str, hit_count: int, top_score: float) -> WorkflowEvent:
    return WorkflowEvent(
        event_id=event_id, workflow_id=workflow_id,
        event_type=EventType.RETRIEVAL_COMPLETED,
        payload={"query": query, "hit_count": hit_count, "top_score": top_score},
    )


def event_evidence_found(event_id: str, workflow_id: str, evidence_id: str, claim: str, source_summary: str) -> WorkflowEvent:
    return WorkflowEvent(
        event_id=event_id, workflow_id=workflow_id,
        event_type=EventType.EVIDENCE_FOUND,
        payload={"evidence_id": evidence_id, "claim": claim, "source_summary": source_summary},
    )


def event_artifact_created(event_id: str, workflow_id: str, artifact_id: str, artifact_type: str, created_by: str) -> WorkflowEvent:
    return WorkflowEvent(
        event_id=event_id, workflow_id=workflow_id,
        event_type=EventType.ARTIFACT_CREATED,
        payload={"artifact_id": artifact_id, "artifact_type": artifact_type, "created_by": created_by},
    )


def event_risk_detected(event_id: str, workflow_id: str, risk_id: str, area: str, severity: str) -> WorkflowEvent:
    return WorkflowEvent(
        event_id=event_id, workflow_id=workflow_id,
        event_type=EventType.RISK_DETECTED,
        payload={"risk_id": risk_id, "area": area, "severity": severity},
    )


def event_agent_completed(event_id: str, workflow_id: str, agent_name: str, duration_ms: int, tokens: int, confidence: float) -> WorkflowEvent:
    return WorkflowEvent(
        event_id=event_id, workflow_id=workflow_id,
        event_type=EventType.AGENT_COMPLETED,
        payload={"agent_name": agent_name, "duration_ms": duration_ms, "tokens": tokens, "confidence": confidence},
    )


def event_agent_failed(event_id: str, workflow_id: str, agent_name: str, error_type: str, retry_count: int, recoverable: bool) -> WorkflowEvent:
    return WorkflowEvent(
        event_id=event_id, workflow_id=workflow_id,
        event_type=EventType.AGENT_FAILED,
        payload={"agent_name": agent_name, "error_type": error_type, "retry_count": retry_count, "recoverable": recoverable},
    )


def event_approval_required(event_id: str, workflow_id: str, agent_name: str, severity: str, summary: str) -> WorkflowEvent:
    return WorkflowEvent(
        event_id=event_id, workflow_id=workflow_id,
        event_type=EventType.APPROVAL_REQUIRED,
        payload={"agent_name": agent_name, "severity": severity, "summary": summary},
    )


def event_approval_submitted(event_id: str, workflow_id: str, decision: str, comment: str) -> WorkflowEvent:
    return WorkflowEvent(
        event_id=event_id, workflow_id=workflow_id,
        event_type=EventType.APPROVAL_SUBMITTED,
        payload={"decision": decision, "comment": comment},
    )


def event_workflow_paused(event_id: str, workflow_id: str, reason: str) -> WorkflowEvent:
    return WorkflowEvent(
        event_id=event_id, workflow_id=workflow_id,
        event_type=EventType.WORKFLOW_PAUSED,
        payload={"reason": reason},
    )


def event_workflow_resumed(event_id: str, workflow_id: str) -> WorkflowEvent:
    return WorkflowEvent(
        event_id=event_id, workflow_id=workflow_id,
        event_type=EventType.WORKFLOW_RESUMED,
        payload={},
    )


def event_workflow_completed(event_id: str, workflow_id: str, total_duration_ms: int, total_tokens: int, total_cost: float) -> WorkflowEvent:
    return WorkflowEvent(
        event_id=event_id, workflow_id=workflow_id,
        event_type=EventType.WORKFLOW_COMPLETED,
        payload={"total_duration_ms": total_duration_ms, "total_tokens": total_tokens, "total_cost": total_cost},
    )


def event_workflow_failed(event_id: str, workflow_id: str, error: str, recoverable: bool) -> WorkflowEvent:
    return WorkflowEvent(
        event_id=event_id, workflow_id=workflow_id,
        event_type=EventType.WORKFLOW_FAILED,
        payload={"error": error, "recoverable": recoverable},
    )
