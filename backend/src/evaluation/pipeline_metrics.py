"""Pipeline Evaluation Metrics — Assessment / Procedure / Workflow 层

对应 EVALUATION_MATRIX.md 的 Layer 2-4:
  Layer 2: Assessment   — Risk Agreement vs 人工基线
  Layer 3: Procedure    — Procedure Coverage, Assertion Match
  Layer 4: Workflow     — End-to-end Success Rate
"""

from abc import ABC, abstractmethod


class PipelineMetric(ABC):
    """管线评估指标基类"""
    name: str = ""

    @abstractmethod
    def compute(self, prediction: dict, ground_truth: dict) -> float:
        ...


# ── Layer 2: Assessment ─────────────────────────────────────────

class AssessmentRiskAgreement(PipelineMetric):
    """Assessment.overall_risk 与人工标注风险等级的吻合度

    宽松匹配: 相邻等级算 0.5（HIGH vs MEDIUM），相同算 1.0。
    """
    name = "assessment_risk_agreement"

    LEVELS = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}

    def compute(self, prediction: dict, ground_truth: dict) -> float:
        pred = prediction.get("overall_risk", "LOW")
        expected = ground_truth.get("expected_risk", "LOW")
        p = self.LEVELS.get(pred, 1)
        e = self.LEVELS.get(expected, 1)
        diff = abs(p - e)
        if diff == 0:
            return 1.0
        if diff == 1:
            return 0.5
        return 0.0


class AssessmentPolicyCoverage(PipelineMetric):
    """策略覆盖 — 输出是否附带 policy_decisions"""
    name = "assessment_policy_coverage"

    def compute(self, prediction: dict, ground_truth: dict) -> float:
        decisions = prediction.get("policy_decisions", [])
        expected_min = ground_truth.get("min_decisions", 1)
        return 1.0 if len(decisions) >= expected_min else len(decisions) / expected_min


class AssessmentFalseEscalation(PipelineMetric):
    """误升级率 — 低风险案例被错误标记为 HIGH"""
    name = "assessment_false_escalation"

    def compute(self, prediction: dict, ground_truth: dict) -> float:
        pred = prediction.get("overall_risk", "LOW")
        expected = ground_truth.get("expected_risk", "LOW")
        # 期望 LOW/MEDIUM 却给出 HIGH → 误升级（0 分）
        if expected in ("LOW", "MEDIUM") and pred == "HIGH":
            return 0.0
        return 1.0


# ── Layer 3: Procedure ──────────────────────────────────────────

class ProcedureCoverage(PipelineMetric):
    """程序覆盖率 — 计划程序是否覆盖所有所需 assertions"""
    name = "procedure_coverage"

    def compute(self, prediction: dict, ground_truth: dict) -> float:
        planned = set(prediction.get("planned_assertions", []))
        required = set(ground_truth.get("required_assertions", []))
        if not required:
            return 1.0
        return len(planned & required) / len(required)


class AssertionMatch(PipelineMetric):
    """认定匹配 — 计划程序的 assertions 是否与所需完全一致"""
    name = "assertion_match"

    def compute(self, prediction: dict, ground_truth: dict) -> float:
        planned = set(prediction.get("planned_assertions", []))
        required = set(ground_truth.get("required_assertions", []))
        if not required:
            return 1.0
        return len(planned & required) / len(planned | required) if planned | required else 0.0


# ── Layer 4: Workflow ───────────────────────────────────────────

class WorkflowSuccessRate(PipelineMetric):
    """端到端成功率 — 管线是否完整跑通"""
    name = "workflow_success_rate"

    def compute(self, prediction: dict, ground_truth: dict) -> float:
        stages = prediction.get("completed_stages", [])
        required = ground_truth.get("required_stages", [])
        if not required:
            return 1.0
        return len(set(stages) & set(required)) / len(required)


# ── Registry ────────────────────────────────────────────────────

PIPELINE_METRICS: dict[str, PipelineMetric] = {
    AssessmentRiskAgreement().name: AssessmentRiskAgreement(),
    AssessmentPolicyCoverage().name: AssessmentPolicyCoverage(),
    AssessmentFalseEscalation().name: AssessmentFalseEscalation(),
    ProcedureCoverage().name: ProcedureCoverage(),
    AssertionMatch().name: AssertionMatch(),
    WorkflowSuccessRate().name: WorkflowSuccessRate(),
}
