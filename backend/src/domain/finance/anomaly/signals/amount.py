"""Amount Signal — 金额异常/整数/审批阈值"""
from .base import Detection, Signal


class AmountSpikeSignal(Signal):
    name = "amount_spike"

    def detect(self, row: dict) -> Detection:
        try:
            ratio = float(row.get("Transaction_to_Avg_Ratio", 0))
            amount = float(row.get("Transaction_Amount_RMB", 0))
        except (ValueError, TypeError):
            return None
        if ratio > 5 and amount > 10000:
            return Detection(signal=self.name, severity="HIGH", confidence=0.85,
                evidence=[f"Amount ${amount:,.0f} is {ratio:.1f}x historical avg"],
                explanation="Transaction significantly exceeds normal pattern")
        if ratio > 3:
            return Detection(signal=self.name, severity="MEDIUM", confidence=0.7,
                evidence=[f"Amount {ratio:.1f}x historical avg"])
        return None


class RoundNumberSignal(Signal):
    name = "round_number"

    def detect(self, row: dict) -> Detection:
        try:
            amount = float(row.get("Transaction_Amount_RMB", 0))
        except (ValueError, TypeError):
            return None
        if amount > 50000 and amount % 10000 == 0:
            return Detection(signal=self.name, severity="MEDIUM",
                evidence=[f"Round amount ${amount:,.0f}"])
        return None


class ThresholdViolationSignal(Signal):
    name = "threshold_violation"

    def detect(self, row: dict) -> Detection:
        try:
            ratio = float(row.get("Amount_Threshold_Ratio", 0))
        except (ValueError, TypeError):
            return None
        if ratio > 1.5:
            return Detection(signal=self.name, severity="HIGH", confidence=0.9,
                evidence=[f"Amount {ratio:.1f}x approval threshold"],
                explanation="Transaction exceeds approval threshold")
        if ratio > 1.0:
            return Detection(signal=self.name, severity="LOW",
                evidence=[f"Amount exceeds threshold"])
        return None
