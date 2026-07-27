"""Experiment Tracker 测试"""

from evaluation.experiment import ExperimentTracker
from evaluation.metrics import EvaluationReport


def test_record_and_history():
    tracker = ExperimentTracker()
    report = EvaluationReport(
        agent_name="risk_agent", benchmark_name="test_bm",
        metrics={"accuracy": 0.85}, baseline={"accuracy": 0.80}, passed=True,
    )
    exp = tracker.record(report)
    assert exp.agent_name == "risk_agent"
    history = tracker.get_history("risk_agent")
    assert len(history) == 1


def test_compare():
    tracker = ExperimentTracker()
    r1 = EvaluationReport(agent_name="a", benchmark_name="b", metrics={"acc": 0.70}, baseline={})
    r2 = EvaluationReport(agent_name="a", benchmark_name="b", metrics={"acc": 0.90}, baseline={})
    e1 = tracker.record(r1)
    e2 = tracker.record(r2)
    comp = tracker.compare(e1.experiment_id, e2.experiment_id)
    assert comp.winner == "B"
    assert comp.metric_deltas["acc"] == 0.20


def test_trend():
    tracker = ExperimentTracker()
    tracker.record(EvaluationReport(agent_name="a", benchmark_name="b", metrics={"acc": 0.80}, baseline={}))
    tracker.record(EvaluationReport(agent_name="a", benchmark_name="b", metrics={"acc": 0.85}, baseline={}))
    trend = tracker.get_trend("a", "acc")
    assert len(trend) == 2


def test_record_with_kwargs():
    tracker = ExperimentTracker()
    report = EvaluationReport(agent_name="a", benchmark_name="b", metrics={}, baseline={})
    exp = tracker.record(report, prompt_version="v1", model_name="gpt-4")
    assert exp.prompt_version == "v1"
    assert exp.model_name == "gpt-4"
