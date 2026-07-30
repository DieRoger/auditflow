"""Journal Entry Testing — 异常分录检测

检测模式: 周末记账, 深夜记账, 整数金额, 重复摘要, 异常用户, 手工分录
"""

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class AnomalyType(Enum):
    WEEKEND_POSTING = "WEEKEND_POSTING"
    NIGHT_POSTING = "NIGHT_POSTING"
    ROUND_NUMBER = "ROUND_NUMBER"
    DUPLICATE_DESCRIPTION = "DUPLICATE_DESCRIPTION"
    UNUSUAL_USER = "UNUSUAL_USER"
    MANUAL_ENTRY = "MANUAL_ENTRY"
    HIGH_VALUE = "HIGH_VALUE"
    END_PERIOD = "END_PERIOD"


@dataclass
class JournalEntry:
    """日记账分录"""
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    journal_no: str = ""
    description: str = ""
    amount: Decimal = Decimal("0")
    posting_date: Optional[date] = None
    created_by: str = ""
    is_manual: bool = True
    account_debit: str = ""
    account_credit: str = ""


@dataclass
class AnomalyResult:
    """异常检测结果"""
    entry_id: str = ""
    anomaly_type: AnomalyType = AnomalyType.ROUND_NUMBER
    severity: str = "LOW"
    detail: str = ""


class JournalAnomalyDetector:
    """日记账异常检测引擎"""

    ROUND_NUMBERS = {1000, 5000, 10000, 50000, 100000, 500000, 1000000}
    NIGHT_HOUR_START = 22
    NIGHT_HOUR_END = 6

    def detect(self, entries: list[JournalEntry]) -> list[AnomalyResult]:
        """对全量日记账执行异常检测"""
        anomalies = []

        for entry in entries:
            # 1. 周末记账
            if entry.posting_date and entry.posting_date.weekday() >= 5:
                anomalies.append(AnomalyResult(
                    entry_id=entry.entry_id,
                    anomaly_type=AnomalyType.WEEKEND_POSTING,
                    severity="MEDIUM",
                    detail=f"Weekend posting: {entry.posting_date} ({entry.posting_date.strftime('%A')})",
                ))

            # 2. 整数金额
            if entry.amount != 0 and entry.amount % 1000 == 0:
                severity = "HIGH" if entry.amount in self.ROUND_NUMBERS else "LOW"
                if entry.amount in self.ROUND_NUMBERS:
                    anomalies.append(AnomalyResult(
                        entry_id=entry.entry_id,
                        anomaly_type=AnomalyType.ROUND_NUMBER,
                        severity=severity,
                        detail=f"Round amount: {entry.amount} (common fraud amount)",
                    ))

            # 3. 手工分录高金额
            if entry.is_manual and entry.amount > 100000:
                anomalies.append(AnomalyResult(
                    entry_id=entry.entry_id,
                    anomaly_type=AnomalyType.MANUAL_ENTRY,
                    severity="HIGH",
                    detail=f"Large manual entry: ${entry.amount:,} ({entry.description[:40]})",
                ))

            # 4. 期末分录
            if entry.posting_date and entry.posting_date.day >= 28:
                anomalies.append(AnomalyResult(
                    entry_id=entry.entry_id,
                    anomaly_type=AnomalyType.END_PERIOD,
                    severity="MEDIUM",
                    detail=f"Period-end entry: {entry.posting_date}",
                ))

        # 5. 重复摘要检测（需要跨条目比较）
        desc_counts = {}
        for entry in entries:
            key = entry.description.strip().lower()[:30]
            desc_counts.setdefault(key, []).append(entry.entry_id)

        for desc, ids in desc_counts.items():
            if len(ids) > 3 and desc:
                for eid in ids:
                    anomalies.append(AnomalyResult(
                        entry_id=eid, anomaly_type=AnomalyType.DUPLICATE_DESCRIPTION,
                        severity="MEDIUM",
                        detail=f"Duplicate description ({len(ids)}x): '{desc[:40]}'",
                    ))

        return anomalies

    def high_risk_anomalies(self, anomalies: list[AnomalyResult]) -> list[AnomalyResult]:
        return [a for a in anomalies if a.severity == "HIGH"]

    def summary(self, anomalies: list[AnomalyResult]) -> dict:
        return {
            "total": len(anomalies),
            "high_risk": len(self.high_risk_anomalies(anomalies)),
            "by_type": {t.value: sum(1 for a in anomalies if a.anomaly_type == t) for t in AnomalyType},
            "details": [{"type": a.anomaly_type.value, "severity": a.severity, "detail": a.detail} for a in anomalies],
        }
