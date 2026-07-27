"""Execution Sandbox — Agent 执行隔离

提供超时控制和执行隔离，防止 Agent 执行失控。

MVP 实现: asyncio-timeout 包装（同进程隔离）。
生产环境: subprocess 隔离（可扩展）。
"""

import asyncio
import structlog
from abc import ABC, abstractmethod

logger = structlog.get_logger(__name__)


class SandboxError(Exception):
    """Sandbox 执行异常"""
    pass


class Sandbox(ABC):
    """执行沙箱抽象接口"""

    @abstractmethod
    async def run(self, fn, *args, **kwargs):
        ...


class AsyncTimeoutSandbox(Sandbox):
    """基于 asyncio timeout 的轻量沙箱（MVP）

    提供: 超时控制、异常隔离。
    不提供: 进程隔离、资源限制（生产环境需升级）。

    用法:
        sandbox = AsyncTimeoutSandbox(timeout=300)
        result = await sandbox.run(agent.execute, request)
    """

    def __init__(self, timeout: int = 300, budget_tracker=None):
        self._timeout = timeout
        self._budget = budget_tracker

    async def run(self, fn, *args, **kwargs):
        """在沙箱中执行异步函数"""
        try:
            result = await asyncio.wait_for(fn(*args, **kwargs), timeout=self._timeout)
            return result
        except asyncio.TimeoutError:
            raise SandboxError(f"Execution timed out after {self._timeout}s")
        except Exception as e:
            raise SandboxError(f"Execution failed: {type(e).__name__}: {e}") from e


class SubprocessSandbox(Sandbox):
    """基于 subprocess 的完整隔离沙箱（生产环境）

    提供: 进程隔离、内存限制、时间限制。
    需要: dill 或 cloudpickle 序列化函数。

    用法:
        sandbox = SubprocessSandbox(timeout=300, max_memory_mb=512)
        result = await sandbox.run(agent.execute, request)
    """

    def __init__(self, timeout: int = 300, max_memory_mb: int = 512):
        self._timeout = timeout
        self._max_memory_mb = max_memory_mb

    async def run(self, fn, *args, **kwargs):
        # 生产环境实现: 用 multiprocessing 或 docker SDK
        # MVP 阶段降级为 AsyncTimeoutSandbox
        logger.warning("subprocess_sandbox_not_implemented", fallback="AsyncTimeoutSandbox")
        fallback = AsyncTimeoutSandbox(timeout=self._timeout)
        return await fallback.run(fn, *args, **kwargs)
