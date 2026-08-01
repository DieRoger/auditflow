"""AnomalyDetectionAgent — Agent 适配器，包装 DetectionFacade

不是 LLM Agent。不调 API。只是让 Rule-based Detection 通过 Agent 接口进入 Workflow DAG。

遵循 BaseAgent 协议 (AgentRequest → AgentResponse)，内部委托给 Application 层
DetectionFacade，后者统一管理多种检测算法（RiskScoringEngine / Benford / IsolationForest）。

架构:
  Workflow → AnomalyDetectionAgent → DetectionFacade → RiskScoringEngine
"""

from agents.base import BaseAgent, ToolDefinition
from domain.contracts import AgentRequest, AgentResponse
from domain.artifacts import FindingArtifact, FindingContent, FindingItem


class AnomalyDetectionAgent(BaseAgent):
    name = "anomaly_detection_agent"
    version = "0.2.0"

    async def execute(self, request: AgentRequest) -> AgentResponse:
        transactions = request.inputs.get("transactions", [])
        if not transactions:
            return AgentResponse(
                status="PARTIAL",
                result={"total": 0, "note": "No transaction data provided"},
                confidence=0.0,
                metrics={"transactions_scanned": 0, "findings_total": 0},
                next_action="EVIDENCE_AGENT",
            )

        from application.detection.detection_facade import DetectionFacade
        facade = DetectionFacade()
        summary = facade.scan(transactions)

        items = [
            FindingItem(
                risk_type=s["risk_type"],
                severity=s["severity"],
                score=s["score"],
                confidence=min(s["score"] / 100.0, 1.0),
                triggered_signals=s["triggered_signals"],
                procedure_template=s["procedure_template"],
                affected_assertions=s["affected_assertions"],
            )
            for s in summary
        ]

        content = FindingContent(
            findings=items,
            total=len(items),
            summary=self._severity_summary(items),
        )

        artifact = FindingArtifact(
            artifact_id=f"fa_{request.workflow_id[:8]}",
            created_by=self.name,
            content=content,
        )

        return AgentResponse(
            status="SUCCESS",
            result={
                "artifact": artifact.model_dump(),
                "findings_total": len(items),
                "transactions_scanned": len(transactions),
            },
            confidence=self._avg_confidence(items),
            metrics={
                "transactions_scanned": len(transactions),
                "findings_total": len(items),
            },
            next_action="EVIDENCE_AGENT",
        )

    def get_tools(self):
        return [
            ToolDefinition(name="scan_transactions"),
            ToolDefinition(name="detect_anomalies"),
        ]

    @staticmethod
    def _severity_summary(items: list[FindingItem]) -> dict:
        s = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for it in items:
            s[it.severity] = s.get(it.severity, 0) + 1
        return s

    @staticmethod
    def _avg_confidence(items: list[FindingItem]) -> float:
        if not items:
            return 0.0
        return sum(it.confidence for it in items) / len(items)

