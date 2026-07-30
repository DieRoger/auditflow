"""Weekend/Night Signal — 非正常交易时间的交易"""
from .base import Signal, SignalResult


class WeekendSignal(Signal):
    name = "weekend"

    def detect(self, row: dict) -> SignalResult:
        if row.get("Weekend_Flag", "").strip() == "1":
            return SignalResult(
                signal_name=self.name, score=2.0,
                evidence=[f"Weekend transaction"],
                detail="Weekend posting",
            )
        return SignalResult(signal_name=self.name)


class NightSignal(Signal):
    name = "night"

    def detect(self, row: dict) -> SignalResult:
        if row.get("Night_Transaction_Flag", "").strip() == "1":
            return SignalResult(
                signal_name=self.name, score=2.0,
                evidence=[f"Night transaction"],
                detail="Night posting",
            )
        return SignalResult(signal_name=self.name)
