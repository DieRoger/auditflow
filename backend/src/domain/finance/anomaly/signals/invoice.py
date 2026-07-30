"""Duplicate Invoice Signal"""
from .base import Detection, Signal


class DuplicateInvoiceSignal(Signal):
    name = "duplicate_invoice"

    def detect(self, row: dict) -> Detection:
        if row.get("Duplicate_Invoice_Flag", "").strip() == "1":
            return Detection(signal=self.name, severity="HIGH", confidence=0.92,
                evidence=["Duplicate invoice flagged"],
                explanation="Same invoice appears multiple times",
                recommendation="Verify both invoices with vendor")
        return None


class TaxMismatchSignal(Signal):
    name = "tax_mismatch"

    def detect(self, row: dict) -> Detection:
        if row.get("Tax_Validation_Flag", "").strip() == "0":
            return Detection(signal=self.name, severity="HIGH", confidence=0.95,
                evidence=["Tax validation failed"],
                explanation="Tax ID does not match registration records",
                recommendation="Confirm tax registration with counterparty")
        return None
