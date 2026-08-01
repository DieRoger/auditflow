"""Integration test: Detection Pipeline (Phase 2 Gate)

验证:
  DetectionFacade → FindingArtifact → AssessmentService → ProcedurePlanningService

不调 LLM，不访问数据库，纯逻辑链路。
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from application.detection.detection_facade import DetectionFacade
from application.assessment.assessment_service import AssessmentService
from application.assessment.assessment_policy import AssessmentPolicy
from application.audit.procedure_planning import ProcedurePlanningService
from domain.artifacts import FindingItem, FindingContent


def sample_transactions(n: int = 30) -> list[dict]:
    """生成模拟交易数据（与 demo_assessment_pipeline 一致）"""
    return [
        {
            "id": f"T{i:04d}",
            "amount": 100000 + i * 5000,
            "date": "2024-12-31",
            "customer": "ABC Corp" if i <= 15 else "XYZ Ltd",
            "invoice": f"INV-{i:04d}",
        }
        for i in range(1, n + 1)
    ]


class TestDetectionPipeline:
    """Phase 2 — DetectionFacade → Assessment → ProcedurePlanning"""

    def test_facade_returns_valid_findings(self):
        """DetectionFacade.scan() 返回 FindingItem-compatible dict"""
        facade = DetectionFacade()
        rows = sample_transactions(30)
        findings = facade.scan(rows)

        assert isinstance(findings, list)
        for f in findings:
            assert "risk_type" in f
            assert "severity" in f
            assert "score" in f
            assert "triggered_signals" in f

    def test_facade_empty_input(self):
        """空输入不抛异常"""
        facade = DetectionFacade()
        findings = facade.scan([])
        assert findings == []

    def test_finding_to_assessment_pipeline(self):
        """Finding dict → AssessmentService.build() → Assessment"""
        mock_finding = {
            "content": {
                "findings": [
                    {
                        "risk_type": "Revenue Fraud",
                        "severity": "HIGH",
                        "score": 92,
                        "confidence": 0.95,
                        "triggered_signals": [{"signal": "duplicate_invoice"}],
                        "procedure_template": "CUTOFF_TEST",
                        "affected_assertions": ["CUTOFF", "OCCURRENCE"],
                    }
                ]
            }
        }
        mock_risk = {
            "content": {
                "severity": "HIGH",
                "probability": 0.9,
                "title": "Revenue fraud risk",
                "area": "Revenue",
                "indicators": ["rapid growth"],
            }
        }

        svc = AssessmentService()
        assessment = svc.build(risk_artifact=mock_risk, finding_artifact=mock_finding)

        assert assessment.overall_risk == "HIGH"
        assert len(assessment.policy_decisions) > 0
        assert assessment.confidence > 0.8

    def test_assessment_to_procedure_pipeline(self):
        """HIGH risk Assessment → at least 2 procedures"""
        from application.assessment.assessment import Assessment

        assessment = Assessment(
            overall_risk="HIGH",
            narrative_risk={"severity": "HIGH", "probability": 0.9},
            detected_findings=[
                {
                    "severity": "HIGH",
                    "score": 92,
                    "risk_type": "Revenue Fraud",
                    "triggered_signals": [{"signal": "duplicate_invoice"}],
                    "procedure_template": "CUTOFF_TEST",
                    "affected_assertions": ["CUTOFF", "OCCURRENCE"],
                }
            ],
            confidence=0.95,
        )

        planner = ProcedurePlanningService()
        program = planner.build_program(assessment)

        assert program.risk_level == "HIGH"
        assert len(program.procedures) >= 2
        # HIGH risk → ALL sampling
        assert all(p.sampling.method.value == "ALL" for p in program.procedures)

    def test_policy_rule_7_low_confidence(self):
        """Rule 7: 低 confidence findings 不升级"""
        result = AssessmentPolicy.determine(
            {"severity": "HIGH"},
            [
                {"severity": "HIGH", "confidence": 0.1},
                {"severity": "HIGH", "confidence": 0.2},
            ],
        )
        assert result == "MEDIUM"

    def test_policy_rule_8_materiality(self):
        """Rule 8: 金额小于 Materiality → LOW"""
        result = AssessmentPolicy.determine(
            {"severity": "LOW"},
            [{"severity": "HIGH", "confidence": 0.9, "amount": 5000}],
            materiality=500000,
        )
        assert result == "LOW"


class TestDetectionFacadeExtensibility:
    """DetectionFacade 扩展性 — 注册自定义检测器"""

    def test_register_custom_detector(self):
        """注册自定义检测器后 scan 合并结果"""
        facade = DetectionFacade()

        class MockDetector:
            def detect(self, rows):
                return [{"risk_type": "Test Risk", "severity": "LOW", "score": 10}]

        facade.register_detector(MockDetector())
        results = facade.scan([{"id": "T1", "amount": 100}])

        # 至少包含 MockDetector 的结果
        risk_types = [r["risk_type"] for r in results]
        assert "Test Risk" in risk_types

    def test_facade_merge_deduplicates(self):
        """同名 risk_type 保留高分"""
        facade = DetectionFacade()

        class DetectorA:
            def detect(self, rows):
                return [{"risk_type": "Same", "severity": "LOW", "score": 10}]

        class DetectorB:
            def detect(self, rows):
                return [{"risk_type": "Same", "severity": "HIGH", "score": 90}]

        facade.register_detector(DetectorA())
        facade.register_detector(DetectorB())
        results = facade.scan([{"id": "T1"}])

        same_results = [r for r in results if r["risk_type"] == "Same"]
        assert len(same_results) == 1
        assert same_results[0]["score"] == 90
