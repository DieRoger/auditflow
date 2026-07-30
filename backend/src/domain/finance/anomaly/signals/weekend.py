"""Weekend/Night Signal — 非正常交易时间的交易"""
from .base import Signal, SignalResult


class WeekendSignal(Signal):
    name = "weekend"

    def detect(self, row: dict) -> SignalResult:
        if row.get("Weekend_Flag", "").strip() == "1":
            return SignalResult(
                signal_name=self.name, score=2.0, severity="MEDIUM",
                evidence=["Weekend transaction"],
                explanation="Transaction posted on Saturday/Sunday, may indicate unusual approval flow",
                recommendation="Verify transaction authenticity with counterparty",
            )
        return SignalResult(signal_name=self.name)


class NightSignal(Signal):
    name = "night"

    def detect(self, row: dict) -> SignalResult:
        if row.get("Night_Transaction_Flag", "").strip() == "1":
            return SignalResult(
                signal_name=self.name, score=2.0, severity="MEDIUM",
                evidence=["Night transaction"],
                explanation="Transaction posted outside business hours (10PM-6AM)",
                recommendation="Review for unauthorized manual override",
            )
        return SignalResult(signal_name=self.name)
