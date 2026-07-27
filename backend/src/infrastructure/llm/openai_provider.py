"""OpenAI LLM Provider 实现."""

import os

from openai import AsyncOpenAI

from .models import LLMMessage, LLMResponse, TokenUsage
from .provider import LLMProvider


class OpenAIProvider(LLMProvider):
    """基于 OpenAI API 的 LLM Provider"""

    def __init__(self, model: str | None = None):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 环境变量未设置")
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model or os.getenv("LLM_DEFAULT_MODEL", "gpt-4o")

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        raw = [
            {"role": m.role, "content": m.content}
            for m in messages
        ]
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=raw,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choice = response.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            usage=TokenUsage.from_openai(response.usage),
            model=self._model,
        )
