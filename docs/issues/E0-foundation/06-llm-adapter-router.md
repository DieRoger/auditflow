# 0.3.1 — LLM Adapter + Model Router

- **Epic:** E0 — Foundation
- **Labels:** `ai-infra`, `phase-0`
- **Depends on:** 0.1.2
- **Estimate:** —

## Description
实现 LLM Provider 抽象层和 Model Router，支持 OpenAI / DeepSeek 可切换。API Key 仅从环境变量读取，Token 用量自动记录。

## Acceptance Criteria
- [ ] OpenAI / DeepSeek 可切换
- [ ] Key 仅环境变量
- [ ] Token 自动记录

## I/O Interface
```python
class LLMProvider(ABC):
    async def generate(self, messages, tools=None, **kwargs) -> LLMResponse: ...

class ModelRouter:
    async def route(self, task_type: "simple"|"complex"|"sensitive") -> LLMProvider: ...
```
