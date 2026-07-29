"""Financial Analytics Engine — Phase F

比率分析、趋势分析、异常检测、重大账户识别。
输入 Canonical Transaction 数据，输出 FinancialRiskIndicators。
"""

import structlog
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional

from domain.finance.entities.transaction import Transaction

logger = structlog.get_logger(__name__)


@dataclass
class RatioResult:
    """单个比率分析结果"""
    name: str = ""                  # e.g. "Gross Margin"
    value: float = 0.0
    interpretation: str = ""        # e.g. "Normal", "Declining", "Improving"
    benchmark: Optional[float] = None
    risk_level: str = "LOW"         # LOW / MEDIUM / HIGH


@dataclass
class TrendResult:
    """趋势分析结果"""
    metric: str = ""                # e.g. "Revenue"
    current_value: float = 0.0
    prior_value: float = 0.0
    change_pct: float = 0.0
    direction: str = "stable"       # "up", "down", "stable"
    anomaly: bool = False           # 异常变动标记


@dataclass
class RatioAnalysis:
    """比率分析报告"""
    ratios: list[RatioResult] = field(default_factory=list)

    def high_risk_ratios(self) -> list[RatioResult]:
        return [r for r in self.ratios if r.risk_level == "HIGH"]

    def summary(self) -> dict:
        return {
            "total": len(self.ratios),
            "high_risk": len(self.high_risk_ratios()),
            "details": [{"name": r.name, "value": r.value, "risk": r.risk_level,
                          "interpretation": r.interpretation} for r in self.ratios],
        }


class RatioEngine:
    """比率计算引擎"""

    def analyze(self, data: dict, benchmarks: dict = None) -> RatioAnalysis:
        """计算关键财务比率"""
        benchmarks = benchmarks or {}
        ratios = []

        # 流动性比率
        current = data.get("current_assets", 0) / max(data.get("current_liabilities", 1), 1)
        ratios.append(RatioResult(
            name="Current Ratio", value=round(current, 2),
            interpretation="Normal" if current >= 1 else "Below 1 — liquidity concern",
            benchmark=benchmarks.get("current_ratio"),
            risk_level="LOW" if current >= 1.2 else "MEDIUM" if current >= 0.8 else "HIGH",
        ))

        quick = (data.get("current_assets", 0) - data.get("inventory", 0)) / max(data.get("current_liabilities", 1), 1)
        ratios.append(RatioResult(
            name="Quick Ratio", value=round(quick, 2),
            interpretation="Normal" if quick >= 0.8 else "Low quick ratio",
            risk_level="LOW" if quick >= 1.0 else "MEDIUM" if quick >= 0.5 else "HIGH",
        ))

        # 盈利能力
        revenue = max(data.get("revenue", 1), 1)
        gross_margin = data.get("gross_profit", 0) / revenue * 100
        ratios.append(RatioResult(
            name="Gross Margin %", value=round(gross_margin, 1),
            interpretation=f"Declining" if gross_margin < 30 else "Stable",
            risk_level="LOW" if gross_margin > 30 else "MEDIUM" if gross_margin > 15 else "HIGH",
        ))

        net_margin = data.get("net_income", 0) / revenue * 100
        ratios.append(RatioResult(
            name="Net Margin %", value=round(net_margin, 1),
            risk_level="LOW" if net_margin > 5 else "MEDIUM" if net_margin > 0 else "HIGH",
        ))

        # 效率比率
        ar_turnover = revenue / max(data.get("receivables", 1), 1)
        ratios.append(RatioResult(
            name="AR Turnover", value=round(ar_turnover, 1),
            interpretation=f"DSO: {365 / max(ar_turnover, 0.1):.0f} days",
            risk_level="LOW" if ar_turnover > 6 else "MEDIUM" if ar_turnover > 3 else "HIGH",
        ))

        inventory_turnover = data.get("cogs", 0) / max(data.get("inventory", 1), 1) if data.get("cogs") else 0
        if inventory_turnover:
            ratios.append(RatioResult(
                name="Inventory Turnover", value=round(inventory_turnover, 1),
                risk_level="LOW" if inventory_turnover > 4 else "MEDIUM",
            ))

        # 偿债能力
        debt_ratio = data.get("total_liabilities", 0) / max(data.get("total_assets", 1), 1) * 100
        ratios.append(RatioResult(
            name="Debt Ratio %", value=round(debt_ratio, 1),
            risk_level="LOW" if debt_ratio < 50 else "MEDIUM" if debt_ratio < 80 else "HIGH",
        ))

        return RatioAnalysis(ratios=ratios)


class TrendEngine:
    """趋势分析引擎 — 本期 vs 上期比较"""

    def analyze(self, current: dict, prior: dict) -> list[TrendResult]:
        """计算关键指标的同比变动"""
        trends = []
        metrics = ["revenue", "net_income", "total_assets", "receivables", "inventory",
                   "current_liabilities"]

        for metric in metrics:
            curr = max(float(current.get(metric, 0)), 1)
            prev = max(float(prior.get(metric, 0)), 1)
            change = round((curr - prev) / prev * 100, 1)

            # 异常检测：变动超过 30% 标记
            anomaly = abs(change) > 30
            direction = "up" if change > 0 else "down" if change < 0 else "stable"

            trends.append(TrendResult(
                metric=metric.replace("_", " ").title(),
                current_value=curr,
                prior_value=prev,
                change_pct=change,
                direction=direction,
                anomaly=anomaly,
            ))

        return trends

    def anomaly_trends(self, trends: list[TrendResult]) -> list[TrendResult]:
        """返回异常趋势（变动 > 30%）"""
        return [t for t in trends if t.anomaly]


class AccountAnalyzer:
    """重大账户识别"""

    def identify_significant(self, account_data: dict, total: float = None) -> list[dict]:
        """基于金额占比识别重大账户"""
        if not total:
            total = sum(account_data.values()) if account_data else 1

        significant = []
        for name, amount in sorted(account_data.items(), key=lambda x: x[1], reverse=True):
            pct = round(amount / max(total, 1) * 100, 1)
            if pct > 5:  # 5% 以上为重大账户
                significant.append({
                    "account": name,
                    "amount": amount,
                    "percentage": pct,
                    "risk": "HIGH" if pct > 15 else "MEDIUM" if pct > 10 else "LOW",
                })

        return significant


@dataclass
class FinancialRiskIndicators:
    """财务风险指标 — Risk Agent 的直接输入"""
    ratios: RatioAnalysis = field(default_factory=RatioAnalysis)
    trends: list[TrendResult] = field(default_factory=list)
    anomalies: list[TrendResult] = field(default_factory=list)
    significant_accounts: list[dict] = field(default_factory=list)

    def to_risk_context(self) -> dict:
        """转为 Risk Agent 可直接读取的格式"""
        return {
            "ratio_risks": self.ratios.summary(),
            "trend_anomalies": [
                {"metric": t.metric, "change": f"{t.change_pct:+.1f}%", "direction": t.direction}
                for t in self.anomalies
            ],
            "significant_accounts": self.significant_accounts,
            "overall_risk_flags": (
                f"{len(self.ratios.high_risk_ratios())} ratio risks, "
                f"{len(self.anomalies)} trend anomalies, "
                f"{len(self.significant_accounts)} significant accounts"
            ),
        }
