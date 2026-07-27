"""LLM Base Agent — 通用 LLM Agent 基类"""

import json
import os
from pathlib import Path

import structlog

from agents.base import BaseAgent
from infrastructure.llm.deepseek_provider import DeepSeekProvider
from infrastructure.llm.models import LLMMessage

logger = structlog.get_logger(__name__)


class LlmBaseAgent(BaseAgent):
    """基于 LLM 的 Agent 基类——封装 LLM 调用、JSON 解析、错误处理"""

    def __init__(self) -> None:
        try:
            self._llm = DeepSeekProvider()
        except ValueError:
            from infrastructure.llm.openai_provider import OpenAIProvider
            self._llm = OpenAIProvider()

    def load_prompt(self, agent_name: str, version: str = "v1") -> str:
        """从 prompts/ 目录加载系统 prompt
        
        查找顺序: 
          1. <project_root>/prompts/<agent_name>/<version>.md
          2. <project_root>/prompts/<agent_name>/v1.md (fallback)
          3. 返回空字符串
        """
        # 从 backend/src/agents/ 向上 4 层到项目根
        base = Path(__file__).parents[3] / "prompts" / agent_name
        for candidate in [base / f"{version}.md", base / "v1.md"]:
            if candidate.exists():
                return candidate.read_text(encoding="utf-8")
        logger.warning("prompt_not_found", agent=agent_name, version=version)
        return ""

    async def call_llm(self, system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> dict:
        """调用 LLM 并解析 JSON 响应"""
        resp = await self._llm.generate([
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ], max_tokens=max_tokens, temperature=0.1)
        self._last_tokens = resp.usage.total_tokens
        try:
            result = json.loads(resp.content)
        except (json.JSONDecodeError, AttributeError):
            result = {"raw": resp.content, "error": "JSON parse failed"}
        logger.info("llm_call", agent=self.name, tokens=self._last_tokens, success="error" not in result)
        return result
