"""OpenAI Embedding Provider 实现."""

import os

from openai import AsyncOpenAI

from .provider import EmbeddingProvider


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """基于 OpenAI text-embedding-3-large 的 Embedding"""

    def __init__(self, model: str = "text-embedding-3-large"):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 环境变量未设置")
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        response = await self._client.embeddings.create(
            model=self._model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    def dimension(self) -> int:
        return 3072
