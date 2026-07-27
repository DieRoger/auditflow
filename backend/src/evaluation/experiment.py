"""Experiment Tracker — Evaluation 实验追踪

每次 EvaluationRunner.run() 自动记录 Experiment。
支持历史对比、趋势分析。
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from .metrics import EvaluationReport


class Experiment(BaseModel):
    model_config = {"protected_namespaces": ()}
    """一次 Evaluation 实验的完整记录"""
    experiment_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    agent_name: str
    prompt_version: str = ""
    model_name: str = ""
    benchmark_name: str = ""
    benchmark_version: str = "v1"
    metrics: dict[str, float] = Field(default_factory=dict)
    baseline: dict[str, float] = Field(default_factory=dict)
    passed: bool = False
    timestamp: datetime = Field(default_factory=datetime.now)
    duration_seconds: float = 0.0
    notes: str | None = None


class ExperimentComparison(BaseModel):
    """两个 Experiment 的对比结果"""
    experiment_a: Experiment
    experiment_b: Experiment
    metric_deltas: dict[str, float] = Field(default_factory=dict)
    winner: str = "TIE"  # "A" | "B" | "TIE"


class ExperimentTracker:
    """实验追踪器

    记录每次 Evaluation 的历史，支持对比与趋势分析。
    """

    def __init__(self) -> None:
        self._experiments: list[Experiment] = []

    def record(self, report: EvaluationReport, **kwargs) -> Experiment:
        """从 EvaluationReport 创建 Experiment 记录"""
        experiment = Experiment(
            agent_name=report.agent_name,
            benchmark_name=report.benchmark_name,
            metrics=report.metrics,
            baseline=report.baseline,
            passed=report.passed,
            duration_seconds=report.duration_seconds,
            **kwargs,
        )
        self._experiments.append(experiment)
        return experiment

    def get_history(self, agent_name: str, limit: int = 20) -> list[Experiment]:
        """获取指定 Agent 的实验历史（按时间降序）"""
        filtered = [e for e in self._experiments if e.agent_name == agent_name]
        return sorted(filtered, key=lambda e: e.timestamp, reverse=True)[:limit]

    def compare(self, experiment_id_a: str, experiment_id_b: str) -> ExperimentComparison:
        """对比两个 Experiment 的指标差异"""
        exp_a = self._get(experiment_id_a)
        exp_b = self._get(experiment_id_b)
        deltas = {}
        all_metrics = set(exp_a.metrics.keys()) | set(exp_b.metrics.keys())
        for metric in all_metrics:
            val_a = exp_a.metrics.get(metric, 0.0)
            val_b = exp_b.metrics.get(metric, 0.0)
            deltas[metric] = round(val_b - val_a, 4)

        # 判断 winner
        total_delta = sum(deltas.values())
        if total_delta > 0.01:
            winner = "B"
        elif total_delta < -0.01:
            winner = "A"
        else:
            winner = "TIE"

        return ExperimentComparison(
            experiment_a=exp_a, experiment_b=exp_b,
            metric_deltas=deltas, winner=winner,
        )

    def get_trend(self, agent_name: str, metric_name: str) -> list[tuple[datetime, float]]:
        """获取指定 Agent 某指标的时序数据"""
        return [
            (e.timestamp, e.metrics.get(metric_name, 0.0))
            for e in self._experiments
            if e.agent_name == agent_name and metric_name in e.metrics
        ]

    def _get(self, experiment_id: str) -> Experiment:
        for e in self._experiments:
            if e.experiment_id == experiment_id:
                return e
        raise KeyError(f"Experiment '{experiment_id}' 不存在")
