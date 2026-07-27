"""Token Budget Tracker — LLM 调用预算管理

每个 Agent 执行时有 Token/工具调用/时间预算。
超出则触发 ContextManager 压缩或请求人工介入。
"""

import structlog
from dataclasses import dataclass, field

logger = structlog.get_logger(__name__)


class BudgetExceededError(Exception):
    """预算超限异常"""
    def __init__(self, message: str, recoverable: bool = True):
        self.recoverable = recoverable
        super().__init__(message)


@dataclass
class TokenBudget:
    """单次 Agent 执行的预算配置"""
    max_tokens: int = 50000
    max_tool_calls: int = 20
    timeout_seconds: int = 300
    max_context_tokens: int = 8000


class TokenBudgetTracker:
    """Token 预算跟踪器 — 记录并强制执行预算"""

    def __init__(self, budget: TokenBudget | None = None):
        self.budget = budget or TokenBudget()
        self.used_tokens = 0
        self.tool_calls = 0

    def record_tokens(self, tokens: int) -> None:
        """记录 Token 消耗，超限则抛出 BudgetExceededError"""
        self.used_tokens += tokens
        logger.debug("budget_tokens", used=self.used_tokens, max=self.budget.max_tokens)
        if self.used_tokens > self.budget.max_tokens:
            raise BudgetExceededError(
                f"Token budget {self.budget.max_tokens} exceeded (used: {self.used_tokens})"
            )

    def record_tool_call(self) -> None:
        """记录工具调用，超限则抛出 BudgetExceededError"""
        self.tool_calls += 1
        if self.tool_calls > self.budget.max_tool_calls:
            raise BudgetExceededError(
                f"Tool call budget {self.budget.max_tool_calls} exceeded"
            )

    @property
    def usage_pct(self) -> float:
        """预算使用百分比"""
        return round(self.used_tokens / self.budget.max_tokens, 4)

    def reset(self) -> None:
        """重置计数器（用于重试时）"""
        self.used_tokens = 0
        self.tool_calls = 0
