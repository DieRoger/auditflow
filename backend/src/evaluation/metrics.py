"""Evaluation 数据模型 — Benchmark / Report / Metric"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel, Field

# ── Benchmark 数据模型 ──────────────────────────────────────────

class BenchmarkCase(BaseModel):
    """单个 Benchmark 测试案例"""
    id: str
    description: str = ""
    input: dict = Field(default_factory=dict, description="AgentRequest.inputs")
    expected: dict = Field(default_factory=dict, description="ground_truth")
    evaluation_metrics: list[str] = Field(default_factory=list, description="需要计算的指标名称列表")


class Benchmark(BaseModel):
    """Benchmark 数据集定义"""
    name: str
    version: str = "v1"
    cases: list[BenchmarkCase] = Field(default_factory=list)


# ── Metric 基类 ─────────────────────────────────────────────────

class Metric(ABC):
    """评估指标抽象基类"""
    name: str = ""

    @abstractmethod
    async def compute(self, prediction: dict, ground_truth: dict) -> float:
        ...


# ── L1 Retrieval Metrics ───────────────────────────────────────

class RecallAtK(Metric):
    name = "recall_at_k"

    async def compute(self, prediction: dict, ground_truth: dict) -> float:
        predicted = set(prediction.get("retrieved_ids", []))
        expected = set(ground_truth.get("expected_ids", []))
        if not expected:
            return 0.0
        return len(predicted & expected) / len(expected)


class MRR(Metric):
    name = "mrr"

    async def compute(self, prediction: dict, ground_truth: dict) -> float:
        retrieved = prediction.get("retrieved_ids", [])
        expected = set(ground_truth.get("expected_ids", []))
        for i, doc_id in enumerate(retrieved, 1):
            if doc_id in expected:
                return 1.0 / i
        return 0.0


class NDCG(Metric):
    name = "ndcg"

    async def compute(self, prediction: dict, ground_truth: dict) -> float:
        retrieved = prediction.get("retrieved_ids", [])
        expected = ground_truth.get("expected_ids", [])
        if not expected:
            return 0.0
        dcg = sum(1.0 / (i + 1) for i, d in enumerate(retrieved) if d in set(expected))
        idcg = sum(1.0 / (i + 1) for i in range(min(len(expected), len(retrieved))))
        return dcg / idcg if idcg > 0 else 0.0


# ── L2 Agent Metrics ───────────────────────────────────────────

class RiskClassificationAccuracy(Metric):
    """宽松匹配 — 检测expected_risks中的任一关键词是否出现在prediction中"""
    name = "risk_classification_accuracy"

    async def compute(self, prediction: dict, ground_truth: dict) -> float:
        pred_risks_lower = [r.lower() for r in prediction.get("detected_risks", [])]
        exp_risks_lower = [e.lower() for e in ground_truth.get("expected_risks", [])]
        if not exp_risks_lower:
            return 0.0
        # 只要 expected 中任一关键词出现在任意 detected 中就算匹配
        pred_text = " ".join(pred_risks_lower)
        matched = sum(1 for e in exp_risks_lower if e in pred_text or any(e in p for p in pred_risks_lower))
        return matched / len(exp_risks_lower)


class SeverityAccuracy(Metric):
    name = "severity_accuracy"

    async def compute(self, prediction: dict, ground_truth: dict) -> float:
        pred = prediction.get("severity", "")
        expected = ground_truth.get("severity", "")
        return 1.0 if pred == expected else 0.0


class CitationCompleteness(Metric):
    name = "citation_completeness"

    async def compute(self, prediction: dict, ground_truth: dict) -> float:
        pred_citations = prediction.get("citation_count", 0)
        expected_min = ground_truth.get("citation_min_count", 1)
        if pred_citations >= expected_min:
            return 1.0
        return pred_citations / expected_min


# ── L3 Grounding Metrics ───────────────────────────────────────

class CitationPrecision(Metric):
    name = "citation_precision"

    async def compute(self, prediction: dict, ground_truth: dict) -> float:
        pred_cites = set(prediction.get("citations", []))
        exp_cites = set(ground_truth.get("valid_citations", []))
        if not pred_cites:
            return 0.0
        return len(pred_cites & exp_cites) / len(pred_cites)


class CitationRecall(Metric):
    name = "citation_recall"

    async def compute(self, prediction: dict, ground_truth: dict) -> float:
        pred_cites = set(prediction.get("citations", []))
        exp_cites = set(ground_truth.get("valid_citations", []))
        if not exp_cites:
            return 1.0
        return len(pred_cites & exp_cites) / len(exp_cites)


class UnsupportedClaimRate(Metric):
    name = "unsupported_claim_rate"

    async def compute(self, prediction: dict, ground_truth: dict) -> float:  # noqa: ARG002
        total = prediction.get("total_claims", 1)
        unsupported = prediction.get("unsupported_claims", 0)
        return 1.0 - (unsupported / total) if total > 0 else 0.0


# ── Evaluation Report ──────────────────────────────────────────

class EvaluationReport(BaseModel):
    """单次评估的报告"""
    agent_name: str
    benchmark_name: str
    metrics: dict[str, float] = Field(default_factory=dict)
    baseline: dict[str, float] = Field(default_factory=dict)
    passed: bool = False
    experiment_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: datetime = Field(default_factory=datetime.now)
    duration_seconds: float = 0.0


# ── Metric Registry ────────────────────────────────────────────

DEFAULT_L1_METRICS: list[Metric] = [RecallAtK(), MRR(), NDCG()]
DEFAULT_L2_METRICS: list[Metric] = [
    RiskClassificationAccuracy(), SeverityAccuracy(), CitationCompleteness(),
]
DEFAULT_L3_METRICS: list[Metric] = [
    CitationPrecision(), CitationRecall(), UnsupportedClaimRate(),
]
