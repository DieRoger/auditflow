"""Relational/Temporal/Violation Signals"""
from .base import Detection, Signal


class RelationalAnomalySignal(Signal):
    name = "relational_anomaly"

    def detect(self, row: dict) -> Detection:
        try:
            score = float(row.get("Relational_Anomaly_Score", 0))
        except (ValueError, TypeError):
            return None
        if score > 0.8:
            return Detection(signal=self.name, severity="HIGH", confidence=score)
        if score > 0.6:
            return Detection(signal=self.name, severity="MEDIUM", confidence=score)
        return None


class TemporalBurstSignal(Signal):
    name = "temporal_burst"
    mode = "score"
    precision = 0.57

    def detect(self, row: dict) -> Detection:
        try:
            score = float(row.get("Temporal_Burst_Score", 0))
        except (ValueError, TypeError):
            return None
        if score > 0.8:
            return Detection(signal=self.name, severity="HIGH", confidence=score)
        if score > 0.5:
            return Detection(signal=self.name, severity="MEDIUM", confidence=score)
        return None


class AuditViolationSignal(Signal):
    name = "audit_violation"
    mode = "info"
    precision = 0.14

    def detect(self, row: dict) -> Detection:
        try:
            count = int(row.get("Audit_Rule_Violation_Count", 0))
        except (ValueError, TypeError):
            return None
        if count > 0:
            return Detection(signal=self.name, severity="HIGH", confidence=min(0.5 + count * 0.1, 1.0),
                evidence=[f"{count} audit rule violations"],
                explanation=f"Transaction violates {count} audit rules",
                recommendation="Review each violation with audit lead")
        return None
