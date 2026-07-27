"""Memory Store — 会话记忆持久化"""

import uuid
from datetime import datetime

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class MemoryEntry(BaseModel):
    id: str = ""
    workflow_id: str
    agent_name: str
    key: str
    value: dict = Field(default_factory=dict)
    created_at: str = ""


class MemoryStore:
    """记忆存储 — 跨 Agent 传递推理中间状态

    MVP 使用内存存储，生产环境切换为 Redis/PostgreSQL。
    """

    def __init__(self):
        self._store: dict[str, list[MemoryEntry]] = {}

    async def save(self, workflow_id: str, agent_name: str, key: str, value: dict) -> None:
        """保存记忆条目"""
        entry = MemoryEntry(
            id=uuid.uuid4().hex[:12],
            workflow_id=workflow_id,
            agent_name=agent_name,
            key=key,
            value=value,
            created_at=datetime.now().isoformat(),
        )
        self._store.setdefault(workflow_id, []).append(entry)
        logger.debug("memory_saved", workflow=workflow_id, agent=agent_name, key=key)

    async def get(self, workflow_id: str, key: str) -> dict | None:
        """获取指定 key 的记忆"""
        entries = self._store.get(workflow_id, [])
        for entry in reversed(entries):
            if entry.key == key:
                return entry.value
        return None

    async def get_all(self, workflow_id: str) -> dict[str, dict]:
        """获取工作流的所有记忆"""
        result: dict[str, dict] = {}
        for entry in self._store.get(workflow_id, []):
            result[entry.key] = entry.value
        return result

    async def clear(self, workflow_id: str) -> None:
        """清除工作流的记忆（工作流完成后调用）"""
        self._store.pop(workflow_id, None)
        logger.info("memory_cleared", workflow=workflow_id)
