"""Duplicate Invoice Signal — 发票重复"""
from .base import Signal, SignalResult


class DuplicateInvoiceSignal(Signal):
    name = "duplicate_invoice"

    def detect(self, row: dict) -> SignalResult:
        if row.get("Duplicate_Invoice_Flag", "").strip() == "1":
            return SignalResult(
                signal_name=self.name, score=4.0,
                evidence=[f"Duplicate invoice flagged"],
                detail="Duplicate invoice",
            )
        return SignalResult(signal_name=self.name)


class TaxMismatchSignal(Signal):
    name = "tax_mismatch"

    def detect(self, row: dict) -> SignalResult:
        if row.get("Tax_Validation_Flag", "").strip() == "0":
            return SignalResult(
                signal_name=self.name, score=3.0,
                evidence=[f"Tax validation failed"],
                detail="Tax ID mismatch",
            )
        return SignalResult(signal_name=self.name)
