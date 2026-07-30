"""Amount Signal — 金额异常、整数金额、审批阈值"""
from .base import Signal, SignalResult


class AmountSpikeSignal(Signal):
    name = "amount_spike"

    def detect(self, row: dict) -> SignalResult:
        try:
            ratio = float(row.get("Transaction_to_Avg_Ratio", 0))
            amount = float(row.get("Transaction_Amount_RMB", 0))
        except:
            return SignalResult(signal_name=self.name)

        if ratio > 5 and amount > 10000:
            return SignalResult(
                signal_name=self.name, score=4.0,
                evidence=[f"Amount ${amount:,.0f} is {ratio:.1f}x historical avg"],
                detail=f"Amount spike ({ratio:.1f}x)",
            )
        if ratio > 3:
            return SignalResult(
                signal_name=self.name, score=2.0,
                evidence=[f"Amount {ratio:.1f}x historical avg"],
                detail=f"Moderate spike",
            )
        return SignalResult(signal_name=self.name)


class RoundNumberSignal(Signal):
    name = "round_number"

    def detect(self, row: dict) -> SignalResult:
        try:
            amount = float(row.get("Transaction_Amount_RMB", 0))
        except:
            return SignalResult(signal_name=self.name)
        if amount > 50000 and amount % 10000 == 0:
            return SignalResult(
                signal_name=self.name, score=2.0,
                evidence=[f"Round amount ${amount:,.0f}"],
                detail="Round number",
            )
        return SignalResult(signal_name=self.name)


class ThresholdViolationSignal(Signal):
    name = "threshold_violation"

    def detect(self, row: dict) -> SignalResult:
        try:
            ratio = float(row.get("Amount_Threshold_Ratio", 0))
        except:
            return SignalResult(signal_name=self.name)
        if ratio > 1.5:
            return SignalResult(
                signal_name=self.name, score=3.0,
                evidence=[f"Amount {ratio:.1f}x approval threshold"],
                detail="Exceeds threshold",
            )
        if ratio > 1.0:
            return SignalResult(
                signal_name=self.name, score=1.0,
                evidence=[f"Amount exceeds threshold"],
                detail="Near threshold",
            )
        return SignalResult(signal_name=self.name)
