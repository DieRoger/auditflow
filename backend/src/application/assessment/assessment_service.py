"""AssessmentService — RiskFindingArtifact + FindingArtifact → Assessment

Application Service，在 Workflow Engine 中 Risk Agent 和 AnomalyDetectionAgent
都完成后调用。纯逻辑，无副作用，无 IO。
"""

from domain.artifacts import FindingArtifact, RiskFindingArtifact
from application.assessment.assessment import Assessment
from application.assessment.assessment_policy import AssessmentPolicy


class AssessmentService:
    """融合 LLM 风险叙述和 Rule-based 检测结果"""

    def build(
        self,
        risk_artifact: dict | None = None,
        finding_artifact: dict | None = None,
        materiality: float | None = None,
    ) -> Assessment:
        narrative_risk = self._extract_narrative(risk_artifact)
        findings = self._extract_findings(finding_artifact)

        overall = AssessmentPolicy.determine(narrative_risk, findings, materiality)
        decisions = AssessmentPolicy.policy_decisions(narrative_risk, findings, materiality)

        # confidence: LLM probability × avg finding confidence, 归一化
        llm_conf = narrative_risk.get("probability", 0.0)
        finding_confs = [f.get("confidence", 0.0) for f in findings]
        avg_finding_conf = sum(finding_confs) / len(finding_confs) if finding_confs else 0.0
        confidence = max(llm_conf, avg_finding_conf)

        return Assessment(
            overall_risk=overall,
            narrative_risk=narrative_risk,
            detected_findings=findings,
            confidence=confidence,
            policy_decisions=decisions,
        )

    @staticmethod
    def _extract_narrative(risk_artifact: dict | None) -> dict:
        if not risk_artifact:
            return {"severity": "LOW", "probability": 0.0, "title": "N/A"}
        content = risk_artifact.get("content", {})
        return {
            "severity": content.get("severity", "LOW"),
            "probability": content.get("probability", 0.0),
            "title": content.get("title", ""),
            "area": content.get("area", ""),
            "indicators": content.get("indicators", []),
        }

    @staticmethod
    def _extract_findings(finding_artifact: dict | None) -> list[dict]:
        if not finding_artifact:
            return []
        content = finding_artifact.get("content", {})
        return content.get("findings", [])
