# 0.5.3.4 — Experiment Tracker

- **Epic:** E0.5 Agent Kernel + Evaluation Core
- **Labels:** `evaluation`, `agent-kernel`
- **Depends on:** 0.5.3.1

## Description
记录每次 Evaluation Experiment（Prompt 版本 + Model + 日期 + Metrics），支持历史对比。每次 EvaluationRunner.run() 自动创建 Experiment 记录，提供时间线对比与趋势分析。

## Acceptance Criteria
- [ ] Experiment 记录：experiment_id / agent_name / prompt_version / model_name / benchmark_name / metrics / timestamp
- [ ] 每次 EvaluationRunner.run() 自动创建 Experiment
- [ ] 历史对比：同一 Agent 不同 Experiment 之间 metrics 差异
- [ ] 趋势分析：同一 Agent 所有 Experiment 的指标时间线
- [ ] 与 PromptVersion.evaluation_score 同步更新

## I/O Interface
```python
class Experiment(BaseModel):
    experiment_id: str
    agent_name: str
    prompt_version: str
    model_name: str
    benchmark_name: str
    benchmark_version: str
    metrics: dict[str, float]
    baseline: dict[str, float]
    passed: bool
    timestamp: datetime
    duration_seconds: float
    notes: str | None

class ExperimentTracker:
    def record(self, report: EvaluationReport) -> Experiment: ...
    def get_history(self, agent_name: str, limit: int = 20) -> list[Experiment]: ...
    def compare(self, experiment_id_a: str, experiment_id_b: str) -> ExperimentComparison: ...
    def get_trend(self, agent_name: str, metric_name: str) -> list[tuple[datetime, float]]: ...

class ExperimentComparison(BaseModel):
    experiment_a: Experiment
    experiment_b: Experiment
    metric_deltas: dict[str, float]    # 各指标差值
    winner: str                         # "A" | "B" | "TIE"
```

## Related ADR
N/A
