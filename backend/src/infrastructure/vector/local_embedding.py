"""Local Embedding Provider — 基于 fastembed 本地运行，零外部依赖"""

import asyncio

from .provider import EmbeddingProvider


class LocalEmbeddingProvider(EmbeddingProvider):
    """基于 fastembed 的本地 Embedding

    使用 BAAI/bge-small-en-v1.5 模型（384维，~30MB ONNX 量化）。
    不依赖任何外部 API Key，完全本地运行，隐私安全。
    首次运行会从 HuggingFace 自动下载模型（一次性，后续离线可用）。
    """

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        self._model_name = model_name
        self._dim = 384
        self._model = None

    async def _load_model(self):
        if self._model is not None:
            return
        loop = asyncio.get_event_loop()
        self._model = await loop.run_in_executor(None, self._load_sync)

    def _load_sync(self):
        from fastembed import TextEmbedding
        return TextEmbedding(self._model_name)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        await self._load_model()
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(None, self._embed_sync, texts)
        return embeddings

    def _embed_sync(self, texts: list[str]) -> list[list[float]]:
        # fastembed 返回 numpy arrays，转为 Python list
        results = list(self._model.embed(texts))
        return [v.tolist() if hasattr(v, 'tolist') else list(v) for v in results]

    def dimension(self) -> int:
        return self._dim
