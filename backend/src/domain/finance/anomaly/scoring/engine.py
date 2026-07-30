"""Risk Scoring Engine — 组合 Signal → RiskProfile → 可解释评分"""

from domain.finance.anomaly.signals.amount import (
    AmountSpikeSignal, RoundNumberSignal, ThresholdViolationSignal,
)
from domain.finance.anomaly.signals.invoice import DuplicateInvoiceSignal, TaxMismatchSignal
from domain.finance.anomaly.signals.party import RelatedPartySignal, ProvinceMismatchSignal
from domain.finance.anomaly.signals.weekend import WeekendSignal, NightSignal
from domain.finance.anomaly.signals.relational import RelationalAnomalySignal, TemporalBurstSignal, AuditViolationSignal
from .profile import ALL_PROFILES, RiskProfile


class RiskScoringEngine:
    """风险评分引擎 — Signal → Profile → 总分 → 解释"""

    def __init__(self):
        self._signals = self._init_signals()

    def _init_signals(self) -> list:
        return [
            AmountSpikeSignal(), RoundNumberSignal(), ThresholdViolationSignal(),
            DuplicateInvoiceSignal(), TaxMismatchSignal(),
            RelatedPartySignal(), ProvinceMismatchSignal(),
            WeekendSignal(), NightSignal(),
            RelationalAnomalySignal(), TemporalBurstSignal(), AuditViolationSignal(),
        ]

    def assess(self, row: dict, risk_profiles: list[str] = None) -> list[dict]:
        """对单行交易评估多个风险类型

        返回: [{risk, total, flagged, signals: [{name, score, detail}]}, ...]
        """
        # Step 1: 运行所有 Signal
        raw_signals = {}
        signal_items = []
        for sig in self._signals:
            result = sig.detect(row)
            if result.score > 0:
                raw_signals[result.signal_name] = result.score
                signal_items.append({
                    "name": result.signal_name,
                    "score": result.score,
                    "detail": result.detail,
                    "evidence": result.evidence,
                })

        # Step 2: 按 RiskProfile 加权评分
        profiles_to_run = risk_profiles or list(ALL_PROFILES.keys())
        results = []
        for key in profiles_to_run:
            profile = ALL_PROFILES[key]
            scoring = profile.score(raw_signals)
            results.append({
                "risk": scoring["risk"],
                "score": scoring["total"],
                "threshold": scoring["threshold"],
                "flagged": scoring["flagged"],
                "signals": signal_items,
                "breakdown": scoring["breakdown"],
            })

        return results

    def assess_batch(self, rows: list[dict], threshold: float = 10.0,
                     risk_profiles: list[str] = None) -> dict:
        """批量评估，返回汇总统计"""
        results = []
        for row in rows:
            scores = self.assess(row, risk_profiles)
            results.append(scores)

        total = len(results)
        flagged = sum(1 for r in results if any(s["flagged"] for s in r))
        avg_score = sum(max(s["score"] for s in r) for r in results) / max(total, 1)

        return {"total": total, "flagged": flagged, "flag_rate": flagged / max(total, 1),
                "avg_score": round(avg_score, 1)}
