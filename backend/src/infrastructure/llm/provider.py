"""LLM Provider 抽象接口."""

from abc import ABC, abstractmethod

from .models import LLMMessage, LLMResponse


class LLMProvider(ABC):
    """统一的 LLM 调用接口

    所有 Agent/Service 必须通过此接口调用 LLM。
    禁止直接调用 OpenAI/DeepSeek SDK。
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """当前使用的模型名称"""
        ...

    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """生成 LLM 响应

        Args:
            messages: 对话消息列表
            temperature: 温度参数（审计场景默认 0.0 以保持确定性）
            max_tokens: 最大输出 token 数
        """
        ...
