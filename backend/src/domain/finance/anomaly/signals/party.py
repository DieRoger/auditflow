"""Related Party Signal"""
from .base import Detection, Signal


class RelatedPartySignal(Signal):
    name = "related_party"
    precision = 0.96

    def detect(self, row: dict) -> Detection:
        if row.get("Related_Party_Flag", "").strip() == "1":
            return Detection(signal=self.name, severity="HIGH", confidence=0.9,
                evidence=["Related party flag"],
                explanation="Counterparty identified as related party",
                recommendation="Verify transaction at arm's length")
        return None


class ProvinceMismatchSignal(Signal):
    name = "province_mismatch"
    mode = "info"
    precision = 0.13

    def detect(self, row: dict) -> Detection:
        if row.get("Province_Mismatch_Flag", "").strip() == "1":
            return Detection(signal=self.name, severity="MEDIUM",
                evidence=["Cross-province transaction"],
                explanation="Transaction crosses province boundaries")
        return None
