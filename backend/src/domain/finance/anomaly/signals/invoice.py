"""Duplicate Invoice Signal + Tax Mismatch Signal"""
from .base import Signal, SignalResult


class DuplicateInvoiceSignal(Signal):
    name = "duplicate_invoice"

    def detect(self, row: dict) -> SignalResult:
        if row.get("Duplicate_Invoice_Flag", "").strip() == "1":
            return SignalResult(
                signal_name=self.name, score=4.0, severity="HIGH",
                evidence=["Duplicate invoice flagged"],
                explanation="Duplicate invoice",
                recommendation="Verify both invoices with vendor",
            )
        return SignalResult(signal_name=self.name)


class TaxMismatchSignal(Signal):
    name = "tax_mismatch"

    def detect(self, row: dict) -> SignalResult:
        if row.get("Tax_Validation_Flag", "").strip() == "0":
            return SignalResult(
                signal_name=self.name, score=3.0, severity="HIGH",
                evidence=["Tax validation failed"],
                explanation="Tax ID mismatch",
                recommendation="Confirm tax registration with counterparty",
            )
        return SignalResult(signal_name=self.name)
