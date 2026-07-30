"""Confirmation Manager — 函证管理

生命周期: 生成函证 → 发送 → 回函 → 差异追踪 → 证据
"""

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class ConfirmationType(Enum):
    AR = "AR"           # 应收账款函证
    AP = "AP"           # 应付账款函证
    BANK = "BANK"       # 银行函证
    LEGAL = "LEGAL"     # 律师函证


class ConfirmationStatus(Enum):
    PENDING = "PENDING"             # 待发送
    SENT = "SENT"                   # 已发送
    RECEIVED = "RECEIVED"           # 已回函
    NO_REPLY = "NO_REPLY"           # 未回函
    DIFFERENCE = "DIFFERENCE"       # 回函差异
    AGREED = "AGREED"               # 回函一致
    ALTERNATIVE = "ALTERNATIVE"     # 已执行替代程序


@dataclass
class ConfirmationRequest:
    """函证请求"""
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    confirmation_type: ConfirmationType = ConfirmationType.AR
    party_name: str = ""
    address: str = ""
    amount_confirmed: Decimal = Decimal("0")
    period_end: Optional[date] = None
    status: ConfirmationStatus = ConfirmationStatus.PENDING
    sent_date: Optional[date] = None
    received_date: Optional[date] = None
    response_amount: Optional[Decimal] = None
    difference: Optional[Decimal] = None
    difference_reason: str = ""
    alternative_procedure_note: str = ""


@dataclass
class ConfirmationRegister:
    """函证汇总登记表"""
    register_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    engagement_id: str = ""
    requests: list[ConfirmationRequest] = field(default_factory=list)

    @property
    def total_sent(self) -> int:
        return sum(1 for r in self.requests if r.status != ConfirmationStatus.PENDING)

    @property
    def total_received(self) -> int:
        return sum(1 for r in self.requests if r.status in (ConfirmationStatus.RECEIVED, ConfirmationStatus.AGREED))

    @property
    def total_differences(self) -> int:
        return sum(1 for r in self.requests if r.status == ConfirmationStatus.DIFFERENCE)

    @property
    def coverage_pct(self) -> float:
        """回函覆盖率"""
        if not self.requests:
            return 0.0
        return round(self.total_received / len(self.requests) * 100, 1)

    def summary(self) -> dict:
        return {
            "total": len(self.requests),
            "sent": self.total_sent,
            "received": self.total_received,
            "differences": self.total_differences,
            "coverage": self.coverage_pct,
        }


class ConfirmationManager:
    """函证管理器"""

    def __init__(self):
        self._register = None
        self._requests = []

    def generate_ar_confirmations(self, register: ConfirmationRegister,
                                   ar_data: list[dict], sample: list = None) -> ConfirmationRegister:
        """从应收账款明细生成函证请求"""
        self._register = register
        items = sample or ar_data
        for item in items:
            register.requests.append(ConfirmationRequest(
                confirmation_type=ConfirmationType.AR,
                party_name=item.get("customer_name", "Unknown"),
                amount_confirmed=Decimal(str(item.get("balance", 0))),
                period_end=date.today(),
            ))
        return register

    def record_response(self, request_id: str, amount: Decimal, status: ConfirmationStatus) -> Optional[str]:
        """记录函证回函"""
        if not self._register:
            return "No register"
        for req in self._register.requests:
            if req.request_id != request_id:
                continue
            req.response_amount = amount
            req.received_date = date.today()
            difference = abs(amount - req.amount_confirmed)
            if difference > 0:
                req.difference = difference
                req.status = ConfirmationStatus.DIFFERENCE
                return f"Difference: ${difference:,}"
            req.status = ConfirmationStatus.AGREED
            return "Agreed"
        return "Not found"

    def _find_request(self, request_id: str):
        """查找请求（占位）"""
        return [None]
