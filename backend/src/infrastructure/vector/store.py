"""VectorStore 抽象接口."""

from abc import ABC, abstractmethod

from pydantic import BaseModel

from .models import EmbeddingItem, SecurityLevel, SourceType


class SearchFilter(BaseModel):
    """检索过滤器"""
    firm_id: str | None = None
    engagement_id: str | None = None
    source_type: list[SourceType] | None = None
    security_level_min: SecurityLevel | None = None


class VectorStore(ABC):
    """统一向量存储接口"""

    @abstractmethod
    async def insert(self, items: list[EmbeddingItem]) -> None:
        """批量插入向量"""
        ...

    @abstractmethod
    async def search(
        self,
        query_vector: list[float],
        top_k: int = 20,
        filters: SearchFilter | None = None,
    ) -> list[EmbeddingItem]:
        """向量检索，支持多维过滤"""
        ...

    @abstractmethod
    async def delete_by_source(self, source_id: str) -> None:
        """按来源 ID 删除"""
        ...

    @abstractmethod
    async def delete_by_engagement(self, engagement_id: str) -> None:
        """按审计项目删除（用于项目重置）"""
        ...
