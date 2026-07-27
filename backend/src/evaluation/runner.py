"""EvaluationRunner — Agent 评估框架

接收 Agent + Benchmark → 计算所有 Metric → 输出 EvaluationReport。
"""

import time

from agents.base import BaseAgent
from domain.contracts import AgentRequest

from .metrics import Benchmark, EvaluationReport, Metric


class EvaluationRunner:
    """统一的 Agent 评估执行器"""

    def __init__(self, metrics: list[Metric], baseline: dict[str, float] | None = None):
        self._metrics = metrics
        self._baseline = baseline or {}

    async def run(self, agent: BaseAgent, benchmark: Benchmark) -> EvaluationReport:
        """运行评估：对 Benchmark 中每个 Case 执行 Agent 并计算指标"""
        start = time.time()
        agg_predictions: dict[str, list] = {m.name: [] for m in self._metrics}
        agg_truths: dict[str, list] = {m.name: [] for m in self._metrics}

        for case in benchmark.cases:
            request = AgentRequest(
                workflow_id="eval",
                project_id="eval",
                task_id="eval",
                firm_id="eval",
                client_id="eval",
                engagement_id="eval",
                inputs=case.input,
            )
            response = await agent.execute(request)

            for metric in self._metrics:
                agg_predictions[metric.name].append(response.result)
                agg_truths[metric.name].append(case.expected)

        # 计算各指标均值
        scores: dict[str, float] = {}
        for metric in self._metrics:
            case_scores = []
            for pred, truth in zip(agg_predictions[metric.name], agg_truths[metric.name], strict=False):
                case_scores.append(await metric.compute(pred, truth))
            scores[metric.name] = sum(case_scores) / len(case_scores) if case_scores else 0.0

        duration = time.time() - start

        # 基线对比
        passed = all(
            scores.get(name, 0.0) >= baseline
            for name, baseline in self._baseline.items()
        )

        return EvaluationReport(
            agent_name=agent.name,
            benchmark_name=benchmark.name,
            metrics=scores,
            baseline=self._baseline,
            passed=passed,
            duration_seconds=round(duration, 3),
        )
