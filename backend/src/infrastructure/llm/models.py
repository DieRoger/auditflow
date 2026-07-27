"""LLM 相关数据模型."""

from pydantic import BaseModel


class TokenUsage(BaseModel):
    """单次 LLM 调用的 Token 用量"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    @classmethod
    def from_openai(cls, usage: object) -> "TokenUsage":
        """从 OpenAI 响应构建"""
        return cls(
            prompt_tokens=getattr(usage, "prompt_tokens", 0),
            completion_tokens=getattr(usage, "completion_tokens", 0),
            total_tokens=getattr(usage, "total_tokens", 0),
        )


class LLMMessage(BaseModel):
    """LLM 消息"""
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str


class LLMResponse(BaseModel):
    """LLM 调用的标准化响应"""
    content: str
    usage: TokenUsage
    model: str
