"""Telemetry 基础设施 — trace_id 贯穿全链路."""

import uuid
from contextvars import ContextVar

# 当前请求的 trace_id（跨 Agent / Worker 共享）
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


def generate_trace_id() -> str:
    """生成新的 trace_id"""
    return uuid.uuid4().hex[:16]


def set_trace_id(trace_id: str | None = None) -> str:
    """设置当前上下文的 trace_id"""
    tid = trace_id or generate_trace_id()
    trace_id_var.set(tid)
    return tid


def get_trace_id() -> str:
    """获取当前上下文的 trace_id"""
    return trace_id_var.get()
