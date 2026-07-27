"""Evaluation 单元测试"""

import pytest

from evaluation.metrics import (
    MRR,
    Benchmark,
    BenchmarkCase,
    CitationPrecision,
    EvaluationReport,
    RecallAtK,
    RiskClassificationAccuracy,
    SeverityAccuracy,
    UnsupportedClaimRate,
)


@pytest.mark.asyncio
async def test_recall_at_k():
    metric = RecallAtK()
    score = await metric.compute(
        {"retrieved_ids": ["a", "b", "c"]},
        {"expected_ids": ["a", "b"]},
    )
    assert score == 1.0


@pytest.mark.asyncio
async def test_recall_partial():
    metric = RecallAtK()
    score = await metric.compute(
        {"retrieved_ids": ["a", "b"]},
        {"expected_ids": ["a", "b", "c"]},
    )
    assert score == pytest.approx(2 / 3)


@pytest.mark.asyncio
async def test_mrr():
    metric = MRR()
    score = await metric.compute(
        {"retrieved_ids": ["c", "a", "b"]},
        {"expected_ids": ["a"]},
    )
    assert score == 0.5  # 1/2


@pytest.mark.asyncio
async def test_risk_accuracy():
    metric = RiskClassificationAccuracy()
    score = await metric.compute(
        {"detected_risks": ["revenue", "inventory"]},
        {"expected_risks": ["revenue", "ar"]},
    )
    assert score == 0.5


@pytest.mark.asyncio
async def test_severity_accuracy():
    metric = SeverityAccuracy()
    assert await metric.compute({"severity": "HIGH"}, {"severity": "HIGH"}) == 1.0
    assert await metric.compute({"severity": "HIGH"}, {"severity": "LOW"}) == 0.0


@pytest.mark.asyncio
async def test_citation_precision():
    metric = CitationPrecision()
    score = await metric.compute(
        {"citations": ["doc_a", "doc_b"]},
        {"valid_citations": ["doc_a"]},
    )
    assert score == 0.5


@pytest.mark.asyncio
async def test_unsupported_claim_rate():
    metric = UnsupportedClaimRate()
    score = await metric.compute(
        {"total_claims": 10, "unsupported_claims": 2},
        {},
    )
    assert score == 0.8


def test_benchmark_model():
    bm = Benchmark(
        name="test_benchmark",
        cases=[BenchmarkCase(id="c1", input={"q": "test"}, expected={"a": "b"})],
    )
    assert len(bm.cases) == 1
    assert bm.cases[0].id == "c1"


def test_evaluation_report_defaults():
    report = EvaluationReport(agent_name="test_agent", benchmark_name="test_bm")
    assert report.experiment_id is not None
    assert report.passed is False
