"""Related Party Signal + Province Mismatch Signal"""
from .base import Signal, SignalResult


class RelatedPartySignal(Signal):
    name = "related_party"

    def detect(self, row: dict) -> SignalResult:
        if row.get("Related_Party_Flag", "").strip() == "1":
            return SignalResult(
                signal_name=self.name, score=4.0,
                evidence=[f"Related party transaction"],
                detail="Related party",
            )
        return SignalResult(signal_name=self.name)


class ProvinceMismatchSignal(Signal):
    name = "province_mismatch"

    def detect(self, row: dict) -> SignalResult:
        if row.get("Province_Mismatch_Flag", "").strip() == "1":
            return SignalResult(
                signal_name=self.name, score=2.0,
                evidence=[f"Cross-province transaction"],
                detail="Province mismatch",
            )
        return SignalResult(signal_name=self.name)
