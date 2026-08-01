"""Risk Profile — 不同审计循环/风险类型的配置"""

from dataclasses import dataclass, field


@dataclass
class SeverityMap:
    """严重性映射"""
    medium: float = 8.0
    high: float = 12.0
    critical: float = 18.0


@dataclass
class RiskProfile:
    """风险类型配置"""
    name: str = ""
    weights: dict[str, float] = field(default_factory=dict)
    threshold: float = 10.0
    required_signals: list[str] = field(default_factory=list)
    optional_signals: list[str] = field(default_factory=list)
    minimum_score: float = 0.0
    severity: SeverityMap = field(default_factory=SeverityMap)
    procedure_template: str = ""  # e.g. "revenue_cutoff"

    def classify_severity(self, score: float) -> str:
        if score >= self.severity.critical:
            return "CRITICAL"
        if score >= self.severity.high:
            return "HIGH"
        if score >= self.severity.medium:
            return "MEDIUM"
        return "LOW"

    def score(self, detections: list) -> dict:
        """从 Detections 计算加权总分"""
        # 检查必要信号
        for req in self.required_signals:
            if not any(d.signal == req for d in detections):
                return {"risk": self.name, "total": 0.0, "flagged": False,
                        "reason": f"Required signal '{req}' not triggered"}

        total = 0.0
        for d in detections:
            # 按 severity 给基础分
            base = {"HIGH": 4, "MEDIUM": 2, "LOW": 1, "CRITICAL": 6}.get(d.severity, 1)
            weight = self.weights.get(d.signal, 1.0)
            total += base * weight

        total = round(total, 1)
        severity = self.classify_severity(total)

        return {
            "risk": self.name,
            "score": total,
            "severity": severity,
            "threshold": self.threshold,
            "flagged": total >= self.threshold,
            "procedure_template": self.procedure_template,
            "detections": len(detections),
        }


REVENUE_FRAUD = RiskProfile(
    name="Revenue Fraud",
    weights={"duplicate_invoice": 4, "amount_spike": 5, "related_party": 5,
             "relational_anomaly": 2, "threshold_violation": 1,
             "round_number": 3, "tax_mismatch": 1, "temporal_burst": 1.5,
             "night": 0.5},
    threshold=5, required_signals=[],
    severity=SeverityMap(medium=6, high=10, critical=16),
    procedure_template="revenue_cutoff",
)

PURCHASE_FRAUD = RiskProfile(
    name="Purchase Fraud",
    weights={"duplicate_invoice": 3, "amount_spike": 3, "related_party": 3,
             "relational_anomaly": 2, "tax_mismatch": 3,
             "round_number": 2, "threshold_violation": 1},
    threshold=4,
    severity=SeverityMap(medium=5, high=8, critical=14),
    procedure_template="purchase_vouching",
)

EXPENSE_FRAUD = RiskProfile(
    name="Expense Fraud",
    weights={"duplicate_invoice": 2, "amount_spike": 2, "related_party": 3,
             "round_number": 2, "threshold_violation": 2,
             "tax_mismatch": 2, "relational_anomaly": 1},
    threshold=4,
    severity=SeverityMap(medium=4, high=7, critical=12),
    procedure_template="expense_occurrence",
)

ALL_PROFILES = {"revenue": REVENUE_FRAUD, "purchase": PURCHASE_FRAUD, "expense": EXPENSE_FRAUD}
