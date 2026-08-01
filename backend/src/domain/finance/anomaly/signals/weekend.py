"""Weekend/Night Signal"""
from .base import Detection, Signal


class WeekendSignal(Signal):
    name = "weekend"
    mode = "info"
    precision = 0.13

    def detect(self, row: dict) -> Detection:
        if row.get("Weekend_Flag", "").strip() == "1":
            return Detection(signal=self.name, severity="MEDIUM", confidence=0.95,
                evidence=["Weekend transaction"],
                explanation="Transaction posted on Saturday/Sunday",
                recommendation="Verify transaction authenticity with counterparty")
        return None


class NightSignal(Signal):
    name = "night"
    mode = "score"
    precision = 0.32

    def detect(self, row: dict) -> Detection:
        if row.get("Night_Transaction_Flag", "").strip() == "1":
            return Detection(signal=self.name, severity="MEDIUM",
                evidence=["Night transaction"],
                explanation="Transaction outside business hours (10PM-6AM)",
                recommendation="Review for unauthorized manual override")
        return None
