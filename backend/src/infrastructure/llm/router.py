"""Model Router — 按任务复杂度路由 LLM Provider."""

from .deepseek_provider import DeepSeekProvider
from .openai_provider import OpenAIProvider
from .provider import LLMProvider


class ModelRouter:
    """按任务类型选择最优 LLM Provider

    路由策略：
    - simple: 小模型（快速、低成本），适合 OCR、元数据提取
    - complex: 大模型（高推理能力），适合风险分析、报告生成
    - sensitive: 私有部署，适合敏感审计数据
    """

    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {}

    def register(self, task_type: str, provider: LLMProvider) -> None:
        """注册任务类型对应的 Provider"""
        self._providers[task_type] = provider

    async def route(self, task_type: str) -> LLMProvider:
        """获取指定任务类型的 Provider"""
        provider = self._providers.get(task_type)
        if provider is None:
            # 默认使用 OpenAI Provider
            provider = OpenAIProvider()
            self._providers[task_type] = provider
        return provider

    @classmethod
    def create_default(cls) -> "ModelRouter":
        """创建默认路由配置，优先使用 DeepSeek"""
        router = cls()
        try:
            router.register("simple", DeepSeekProvider(model="deepseek-chat"))
            router.register("complex", DeepSeekProvider(model="deepseek-chat"))
        except ValueError:
            # Fallback to OpenAI if DeepSeek not configured
            router.register("simple", OpenAIProvider(model="gpt-4o-mini"))
            router.register("complex", OpenAIProvider(model="gpt-4o"))
        return router
