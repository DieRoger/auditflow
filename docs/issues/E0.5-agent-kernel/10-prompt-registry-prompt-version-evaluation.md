# 0.5.3.2 — Prompt Registry + Prompt Version Evaluation（v3.2 增强）

- **Epic:** E0.5 Agent Kernel + Evaluation Core
- **Labels:** `agent-kernel`, `prompt`
- **Depends on:** 0.5.1.1

## Description
Prompt 版本化管理 + Evaluation 绑定。AI 系统最大变化来源不是代码而是 Prompt，必须区分"是 Prompt 变好了还是 Model 升级了"。每次 Prompt 变更自动触发 Evaluation，新版本分数低于基线不可激活。

## Acceptance Criteria
- [ ] PromptVersion：agent_name / version / content / variables / model_name / evaluation_score / baseline_score / improvement / created_at / is_active
- [ ] v1/v2 版本化，禁止覆盖，禁止删除已评估版本
- [ ] 每次 Prompt 变更 → 自动触发 Evaluation → 记录 score + delta
- [ ] 新版本分数 < baseline → 不可激活为 is_active
- [ ] CI 集成：Prompt 变更 PR 必须附带 Evaluation Report
- [ ] 支持区分 Prompt 变更 vs Model 升级的影响

## I/O Interface
```python
class PromptVersion(BaseModel):
    agent_name: str
    version: str                     # "v1", "v2"
    content: str                     # Markdown 模板
    variables: list[str]
    model_name: str                  # 绑定的模型
    evaluation_score: float | None   # 当前 Benchmark 分数
    baseline_score: float | None     # 上一版本分数
    improvement: float | None        # delta
    created_at: datetime
    is_active: bool

class PromptRegistry:
    _versions: dict[str, list[PromptVersion]] = {}  # agent_name → [versions]

    def register(self, version: PromptVersion) -> None: ...
    def activate(self, agent_name: str, version: str) -> None:
        """激活前检查 evaluation_score >= baseline_score"""
        ...
    def get_active(self, agent_name: str) -> PromptVersion: ...
    def get_history(self, agent_name: str) -> list[PromptVersion]: ...
    def compare_versions(self, agent_name: str, v1: str, v2: str) -> dict: ...
```

## Related ADR
N/A
