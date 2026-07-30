"""Anomaly 模块初始化 — 注册所有 Signal"""

from .signals.base import Detection, Signal
from .signals.registry import register_many
from .signals.weekend import WeekendSignal, NightSignal
from .signals.invoice import DuplicateInvoiceSignal, TaxMismatchSignal
from .signals.amount import AmountSpikeSignal, RoundNumberSignal, ThresholdViolationSignal
from .signals.party import RelatedPartySignal, ProvinceMismatchSignal
from .signals.relational import RelationalAnomalySignal, TemporalBurstSignal, AuditViolationSignal

register_many(
    AmountSpikeSignal(), RoundNumberSignal(), ThresholdViolationSignal(),
    DuplicateInvoiceSignal(), TaxMismatchSignal(),
    RelatedPartySignal(), ProvinceMismatchSignal(),
    WeekendSignal(), NightSignal(),
    RelationalAnomalySignal(), TemporalBurstSignal(), AuditViolationSignal(),
)
