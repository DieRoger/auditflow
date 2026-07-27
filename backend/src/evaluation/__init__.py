"""Evaluation 层 — Metric 体系 + EvaluationRunner"""

from .experiment import Experiment, ExperimentComparison, ExperimentTracker
from .metrics import (
    DEFAULT_L1_METRICS,
    DEFAULT_L2_METRICS,
    DEFAULT_L3_METRICS,
    MRR,
    NDCG,
    Benchmark,
    BenchmarkCase,
    CitationCompleteness,
    CitationPrecision,
    CitationRecall,
    EvaluationReport,
    Metric,
    RecallAtK,
    RiskClassificationAccuracy,
    SeverityAccuracy,
    UnsupportedClaimRate,
)
from .prompt_registry import PromptRegistry, PromptVersion
from .runner import EvaluationRunner

__all__ = [
    "Metric",
    "Benchmark", "BenchmarkCase",
    "EvaluationReport",
    "RecallAtK", "MRR", "NDCG",
    "RiskClassificationAccuracy", "SeverityAccuracy", "CitationCompleteness",
    "CitationPrecision", "CitationRecall", "UnsupportedClaimRate",
    "DEFAULT_L1_METRICS", "DEFAULT_L2_METRICS", "DEFAULT_L3_METRICS",
    "EvaluationRunner",
    "PromptVersion", "PromptRegistry",
    "Experiment", "ExperimentComparison", "ExperimentTracker",
]
