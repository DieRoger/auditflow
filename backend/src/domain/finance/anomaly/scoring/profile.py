"""Risk Profile — 不同审计循环/风险类型的权重配置"""

from dataclasses import dataclass, field
from domain.finance.anomaly.signals.base import SignalResult


@dataclass
class RiskProfile:
    """一个风险类型的配置"""
    name: str = ""
    weights: dict[str, float] = field(default_factory=dict)
    threshold: float = 7.0
    required_signals: list[str] = field(default_factory=list)  # 未触发则不成立
    optional_signals: list[str] = field(default_factory=list)  # 加分信号

    def score(self, signals: dict[str, float], signal_details: dict[str, SignalResult] = None) -> dict:
        """按权重计算加权总分"""
        total = 0.0
        breakdown = {}

        # 检查必要信号
        for req in self.required_signals:
            if signals.get(req, 0) == 0:
                return {"risk": self.name, "total": 0.0, "flagged": False,
                        "reason": f"Required signal '{req}' not triggered"}

        for sig_name, raw_score in signals.items():
            if raw_score == 0:
                continue
            weight = self.weights.get(sig_name, 1.0)
            weighted = raw_score * weight
            total += weighted
            detail_obj = signal_details.get(sig_name) if signal_details else None
            breakdown[sig_name] = {
                "raw": raw_score, "weight": weight, "weighted": round(weighted, 1),
                "explanation": detail_obj.explanation if detail_obj else "",
            }

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
