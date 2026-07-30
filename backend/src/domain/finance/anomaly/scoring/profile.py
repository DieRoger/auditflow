"""Risk Profile — 不同审计循环/风险类型的权重配置"""

from dataclasses import dataclass, field


@dataclass
class RiskProfile:
    """一个风险类型的 Signal 权重配置"""
    name: str = ""
    # signal_name → weight
    weights: dict[str, float] = field(default_factory=dict)
    threshold: float = 7.0

    def score(self, signals: dict[str, float]) -> dict:
        """按权重计算加权总分"""
        total = 0.0
        breakdown = {}
        for sig_name, raw_score in signals.items():
            if raw_score == 0:
                continue
            weight = self.weights.get(sig_name, 1.0)
            weighted = raw_score * weight
            total += weighted
            breakdown[sig_name] = {"raw": raw_score, "weight": weight, "weighted": weighted}
        return {"risk": self.name, "total": round(total, 1), "breakdown": breakdown,
                "threshold": self.threshold, "flagged": total >= self.threshold}


REVENUE_FRAUD = RiskProfile(
    name="Revenue Fraud",
    weights={
        "duplicate_invoice": 1.5,
        "amount_spike": 1.5,
        "related_party": 1.5,
        "weekend": 0.5,
        "night": 0.5,
        "round_number": 0.5,
        "tax_mismatch": 1.0,
        "province_mismatch": 0.5,
        "threshold_violation": 1.0,
        "relational_anomaly": 1.5,
        "temporal_burst": 1.0,
        "audit_violation": 1.0,
    },
    threshold=5.0,
)

PURCHASE_FRAUD = RiskProfile(
    name="Purchase Fraud",
    weights={
        "duplicate_invoice": 0.5,
        "amount_spike": 1.0,
        "related_party": 1.5,
        "weekend": 1.0,
        "night": 1.0,
        "round_number": 1.5,
        "tax_mismatch": 1.5,
        "province_mismatch": 1.5,
        "threshold_violation": 0.5,
        "relational_anomaly": 1.0,
        "temporal_burst": 1.0,
        "audit_violation": 1.5,
    },
    threshold=5.0,
)

EXPENSE_FRAUD = RiskProfile(
    name="Expense Fraud",
    weights={
        "duplicate_invoice": 1.0,
        "amount_spike": 1.0,
        "related_party": 1.5,
        "weekend": 1.5,
        "night": 1.0,
        "round_number": 1.5,
        "tax_mismatch": 1.0,
        "province_mismatch": 1.0,
        "threshold_violation": 1.5,
        "relational_anomaly": 0.5,
        "temporal_burst": 1.5,
        "audit_violation": 2.0,
    },
    threshold=5.0,
)

ALL_PROFILES = {"revenue": REVENUE_FRAUD, "purchase": PURCHASE_FRAUD, "expense": EXPENSE_FRAUD}
