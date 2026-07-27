"""Embedding Provider 抽象接口."""

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """统一的 Embedding 接口

    所有模块（文档 / 知识 / 证据）必须通过此接口生成向量。
    """

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """将文本列表转换为向量列表"""
        ...

    @abstractmethod
    def dimension(self) -> int:
        """返回向量维度

        OpenAI text-embedding-3-large: 3072
        BGE-M3: 1024
        """
        ...
