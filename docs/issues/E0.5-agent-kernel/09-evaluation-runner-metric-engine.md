# 0.5.3.1 — Evaluation Runner + Metric Engine

- **Epic:** E0.5 Agent Kernel + Evaluation Core
- **Labels:** `evaluation`, `agent-kernel`
- **Depends on:** 0.5.1.1

## Description
实现 Evaluation Runner —— 统一的 Agent 评估框架。Metric 抽象基类支持自定义指标计算；EvaluationRunner 接受 Agent + Benchmark → 输出 EvaluationReport。支持基线对比，低于基线 = FAIL。

覆盖 Evaluation 四层体系中的 L1/L2/L3（L4 在 E4 完成后追加）。

## Acceptance Criteria
- [ ] Metric(ABC)：name + async compute(prediction, ground_truth) -> float
- [ ] EvaluationRunner：async run(agent, benchmark) -> EvaluationReport
- [ ] EvaluationReport：agent_name / benchmark_name / metrics / baseline / passed / experiment_id
- [ ] 低于基线 → passed=False
- [ ] 支持 L1 Retrieval 指标（Recall@K, MRR, NDCG）
- [ ] 支持 L2 Agent 指标（Risk Accuracy, Severity Accuracy, Reasoning Quality）
- [ ] 支持 L3 Grounding 指标（Citation Precision, Citation Recall, Unsupported Claim Rate）
- [ ] experiment_id 可追踪

## I/O Interface
```python
class Metric(ABC):
    name: str

    @abstractmethod
    async def compute(self, prediction: AgentResponse, ground_truth: dict) -> float:
        ...

class EvaluationRunner:
    def __init__(self, metrics: list[Metric], baseline: dict[str, float] | None = None): ...

    async def run(self, agent: BaseAgent, benchmark: Benchmark) -> EvaluationReport:
        ...

class EvaluationReport(BaseModel):
    agent_name: str
    benchmark_name: str
    metrics: dict[str, float]         # 本次评估各项指标分数
    baseline: dict[str, float]        # 基线分数
    passed: bool                      # 低于基线 = FAIL
    experiment_id: str                # 可追踪
    timestamp: datetime
    duration_seconds: float

class Benchmark(BaseModel):
    name: str
    version: str
    cases: list[BenchmarkCase]

class BenchmarkCase(BaseModel):
    id: str
    description: str
    input: dict                       # AgentRequest.inputs
    expected: dict                    # ground_truth
    evaluation_metrics: list[str]     # 需要计算的指标
```

## Related ADR
N/A
