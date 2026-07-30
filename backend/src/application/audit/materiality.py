"""Materiality Engine — ISA 320 重要性水平计算

三个层级: Overall Materiality / Performance Materiality / Trivial Threshold
四个基准: Profit Before Tax / Revenue / Total Assets / Equity
"""

from dataclasses import dataclass


@dataclass
class MaterialityResult:
    overall: float = 0
    performance: float = 0
    trivial: float = 0
    base: str = ""
    base_pct: float = 0
    bases: dict = None
    values: dict = None


class MaterialityEngine:
    """重要性水平计算引擎 — ISA 320"""

    ISA_PERCENTAGES = {
        "profit_before_tax": 0.05,    # 5% of PBT
        "revenue": 0.005,             # 0.5% of revenue
        "total_assets": 0.01,         # 1% of total assets
        "equity": 0.01,               # 1% of equity
    }
    RISK_ADJUSTMENT = {"LOW": 1.0, "MEDIUM": 0.75, "HIGH": 0.5}

    def calculate(self, financials: dict, audit_risk: str = "MEDIUM") -> MaterialityResult:
        """计算三个层级的重要性水平"""
        bases = {}
        for metric, pct in self.ISA_PERCENTAGES.items():
            val = float(financials.get(metric, 0))
            bases[metric] = round(val * pct)

        # 选最低值作为整体重要性（最保守原则）
        non_zero = {k: v for k, v in bases.items() if v > 0}
        base_metric = min(non_zero, key=non_zero.get) if non_zero else "revenue"
        overall = non_zero.get(base_metric, 0)

        risk_mult = self.RISK_ADJUSTMENT.get(audit_risk, 0.75)
        performance = round(overall * risk_mult)
        trivial = round(overall * 0.05)

        return MaterialityResult(
            overall=overall,
            performance=performance,
            trivial=trivial,
            base=base_metric,
            base_pct=self.ISA_PERCENTAGES.get(base_metric, 0) * 100,
            bases={k: round(v) for k, v in bases.items()},
            values=financials,
        )
