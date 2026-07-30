"""Relational + Temporal + Violation Signals"""
from .base import Signal, SignalResult


class RelationalAnomalySignal(Signal):
    name = "relational_anomaly"

    def detect(self, row: dict) -> SignalResult:
        try:
            score = float(row.get("Relational_Anomaly_Score", 0))
        except:
            return SignalResult(signal_name=self.name)
        if score > 0.8:
            return SignalResult(signal_name=self.name, score=5.0,
                evidence=[f"Relational anomaly score: {score:.2f}"], detail="High relational anomaly")
        if score > 0.6:
            return SignalResult(signal_name=self.name, score=3.0,
                evidence=[f"Relational anomaly score: {score:.2f}"], detail="Medium relational anomaly")
        if score > 0.4:
            return SignalResult(signal_name=self.name, score=1.0,
                evidence=[f"Relational anomaly score: {score:.2f}"], detail="Low relational anomaly")
        return SignalResult(signal_name=self.name)


class TemporalBurstSignal(Signal):
    name = "temporal_burst"

    def detect(self, row: dict) -> SignalResult:
        try:
            score = float(row.get("Temporal_Burst_Score", 0))
        except:
            return SignalResult(signal_name=self.name)
        if score > 0.8:
            return SignalResult(signal_name=self.name, score=3.0,
                evidence=[f"Burst score: {score:.2f}"], detail="High temporal burst")
        if score > 0.5:
            return SignalResult(signal_name=self.name, score=1.0,
                evidence=[f"Burst score: {score:.2f}"], detail="Medium temporal burst")
        return SignalResult(signal_name=self.name)


class AuditViolationSignal(Signal):
    name = "audit_violation"

    def detect(self, row: dict) -> SignalResult:
        try:
            count = int(row.get("Audit_Rule_Violation_Count", 0))
        except:
            return SignalResult(signal_name=self.name)
        if count > 0:
            score = min(count * 2, 6)
            return SignalResult(signal_name=self.name, score=float(score),
                evidence=[f"{count} audit rule violations"], detail=f"Violations: {count}")
        return SignalResult(signal_name=self.name)
