"""Assessment — 统一风险评估对象

融合 Risk Agent (LLM narrative) 和 Anomaly Detection (rule-based findings)，
由 AssessmentPolicy 决定 overall_risk。

放在 domain/audit/ 因为最终服务于审计程序决策，不是会计概念。
"""

from pydantic import BaseModel, Field


class Assessment(BaseModel):
    """Procedure Agent 的唯一风险评估输入"""
    overall_risk: str = "LOW"       # HIGH / MEDIUM / LOW
    narrative_risk: dict = Field(default_factory=dict)   # RiskFindingArtifact 摘要
    detected_findings: list[dict] = Field(default_factory=list)  # FindingItem 列表
    confidence: float = 0.0
    policy_decisions: list[str] = Field(default_factory=list)  # 触发的规则名称

    def to_context(self) -> dict:
        """转为 AgentRequest.context 可直接消费的格式"""
        return {
            "overall_risk": self.overall_risk,
            "risk_summary": self.narrative_risk,
            "anomaly_findings": self.detected_findings,
            "confidence": self.confidence,
        }
