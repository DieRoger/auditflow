"""Finance Domain Entities — Canonical Audit Schema v1.0

Transaction, Document, Party — 冻结后不可修改字段语义。
"""

import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional, Union


class TransactionType(Enum):
    SALES = "SALES"
    PURCHASE = "PURCHASE"
    PAYMENT = "PAYMENT"
    RECEIPT = "RECEIPT"
    JOURNAL = "JOURNAL"


class DocumentType(Enum):
    INVOICE = "INVOICE"
    DELIVERY = "DELIVERY"
    CONTRACT = "CONTRACT"
    RECEIPT = "RECEIPT"
    PURCHASE_ORDER = "PURCHASE_ORDER"
    SHIPPING = "SHIPPING"


class PartyType(Enum):
    CUSTOMER = "CUSTOMER"
    VENDOR = "VENDOR"
    EMPLOYEE = "EMPLOYEE"


@dataclass(frozen=True)
class Transaction:
    """一笔可审计的业务交易（不可变）"""
    transaction_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    transaction_type: TransactionType = TransactionType.SALES
    transaction_date: date = field(default_factory=date.today)
    period: str = ""  # YYYY-MM
    amount: Decimal = Decimal("0.00")
    currency: str = "CNY"
    party_id: Optional[str] = None
    document_refs: list[str] = field(default_factory=list)
    description: str = ""
    source: str = ""  # ImportSession.session_id

    def __post_init__(self):
        if not self.period:
            object.__setattr__(self, "period", self.transaction_date.strftime("%Y-%m"))


@dataclass(frozen=True)
class Document:
    """支持审计证据的业务文档"""
    document_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    document_type: DocumentType = DocumentType.INVOICE
    document_no: str = ""
    document_date: date = field(default_factory=date.today)
    party_id: Optional[str] = None
    amount: Optional[Decimal] = None
    reference_no: Optional[str] = None


@dataclass
class Party:
    """交易对手方"""
    party_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    party_type: PartyType = PartyType.CUSTOMER
    name: str = ""


@dataclass
class AccountEntry:
    """科目发生额（预留 v2.0，Phase A 不实现存储）"""
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    account_code: str = ""
    debit: Decimal = Decimal("0.00")
    credit: Decimal = Decimal("0.00")
    period: str = ""
