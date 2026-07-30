"""Multi-period Analysis — 多期财务数据分析引擎

支持 3+ 期财务数据导入、年度同比、趋势判定、异常波动。
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MultiPeriodTrend:
    """多期趋势"""
    metric: str = ""
    values: list[float] = field(default_factory=list)  # [2023, 2024, 2025]
    changes: list[float] = field(default_factory=list)  # [YoY_24, YoY_25]
    pattern: str = "stable"  # accelerating_growth, declining, reversal, volatile, stable


@dataclass
class MultiPeriodResult:
    """多期分析结果"""
    trends: list[MultiPeriodTrend] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "metrics_analyzed": len(self.trends),
            "red_flags": self.red_flags,
            "trends": [{"metric": t.metric, "values": t.values, "changes": t.changes, "pattern": t.pattern}
                       for t in self.trends],
        }


class MultiPeriodAnalyzer:
    """多期财务数据分析引擎"""

    # 关注阈值
    CHANGE_THRESHOLD = 0.15       # 15% 变动标记
    REVERSAL_THRESHOLD = 0.30     # 30% 反转标记

    def analyze(self, periods: dict[str, dict]) -> MultiPeriodResult:
        """分析多期财务数据
        
        periods = {
            "2023": {"revenue": 100, ...},
            "2024": {"revenue": 120, ...},
            "2025": {"revenue": 180, ...},
        }
        """
        result = MultiPeriodResult()
        sorted_years = sorted(periods.keys())
        if len(sorted_years) < 2:
            return result

        metrics = ["revenue", "net_income", "total_assets", "receivables", "inventory",
                   "current_liabilities", "cash", "cogs"]

        for metric in metrics:
            values = []
            for year in sorted_years:
                val = float(periods[year].get(metric, 0))
                values.append(val)

            changes = []
            for i in range(1, len(values)):
                prev = max(values[i-1], 1)
                change = (values[i] - prev) / prev
                changes.append(round(change, 4))

            # 趋势判定
            pattern = self._classify_pattern(changes)

            trend = MultiPeriodTrend(
                metric=metric.replace("_", " ").title(),
                values=[round(v, 2) for v in values],
                changes=changes,
                pattern=pattern,
            )
            result.trends.append(trend)

            # 异常判定
            if pattern in ("reversal", "volatile"):
                result.red_flags.append(
                    f"{metric} trend: {pattern} — "
                    + "; ".join(f"{sorted_years[i+1]} {c:+.1%}" for i, c in enumerate(changes))
                )
            for c in changes:
                if abs(c) > self.REVERSAL_THRESHOLD:
                    idx = changes.index(c)
                    year = sorted_years[idx + 1]
                    result.red_flags.append(
                        f"{metric} {c:+.1%} in {year} — exceeds {self.REVERSAL_THRESHOLD:.0%} threshold"
                    )
                    break

        return result

    def _classify_pattern(self, changes: list[float]) -> str:
        """判定趋势模式"""
        if len(changes) < 2:
            return "stable" if abs(changes[0]) < self.CHANGE_THRESHOLD else "growing"

        # 加速增长：增速持续上升
        if all(c > 0 for c in changes) and changes[-1] > max(changes[:-1]):
            return "accelerating_growth"

        # 反转：正向变负向或反之
        if changes[0] > 0 and changes[-1] < 0:
            return "reversal"
        if changes[0] < 0 and changes[-1] > 0:
            return "reversal"

        # 波动：正负交替
        if sum(1 for c in changes if c > 0) in (1, len(changes) - 1) if len(changes) > 1 else True:
            pass  # continue to next check
        signs = [1 if c > 0 else -1 for c in changes]
        if len(signs) >= 2 and signs[0] != signs[-1]:
            return "volatile"

        # 增长率持续正
        if all(c >= 0 for c in changes):
            return "growing" if max(changes) > self.CHANGE_THRESHOLD else "stable"

        # 持续下降
        if all(c < 0 for c in changes):
            return "declining"

        return "stable"
