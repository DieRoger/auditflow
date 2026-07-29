"""Misstatement Engine — Phase D

从 Procedure Findings 生成错报汇总 + 调整分录 (AJE/RJE)。

Misstatement 类型:
  - Known: 已确认的错报（通过审计程序直接发现的）
  - Likely: 可能的错报（基于样本推断到总体的）
  - Projected: 推断错报（基于抽样结果的统计推断）
  - Judgmental: 判断性差异（会计估计 vs 审计估计）
"""

import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Optional


class MisstatementType(Enum):
    KNOWN = "KNOWN"
    LIKELY = "LIKELY"
    PROJECTED = "PROJECTED"
    JUDGMENTAL = "JUDGMENTAL"


class EntryType(Enum):
    AJE = "AJE"         # Audit Journal Entry (审计调整分录)
    RJE = "RJE"         # Reclassification Journal Entry (重分类分录)
    PJE = "PJE"         # Proposed Journal Entry (建议调整分录)


class MisstatementDirection(Enum):
    OVERSTATEMENT = "OVERSTATEMENT"     # 高估（收入/资产）
    UNDERSTATEMENT = "UNDERSTATEMENT"   # 低估（费用/负债）


@dataclass
class Misstatement:
    """单个错报"""
    misstatement_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    description: str = ""
    misstatement_type: MisstatementType = MisstatementType.KNOWN
    direction: MisstatementDirection = MisstatementDirection.OVERSTATEMENT
    amount: Decimal = Decimal("0")
    account_debit: str = ""             # 借方科目
    account_credit: str = ""            # 贷方科目
    assertion_affected: str = ""        # 受影响的认定 (CUTOFF/OCCURRENCE)
    finding_ref: str = ""               # 关联的 Finding ID
    passed_threshold: bool = True       # 是否超过可容忍错报门槛


@dataclass
class AdjustmentEntry:
    """调整分录"""
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    entry_type: EntryType = EntryType.AJE
    description: str = ""
    date: str = ""
    period: str = ""

    # 分录行
    debit_account: str = ""
    debit_amount: Decimal = Decimal("0")
    credit_account: str = ""
    credit_amount: Decimal = Decimal("0")

    misstatement_refs: list[str] = field(default_factory=list)

    def to_journal_text(self) -> str:
        """生成调整分录文本"""
        return (
            f"DR {self.debit_account:<40} {self.debit_amount:>12,.2f}\n"
            f"CR {self.credit_account:<40} {self.credit_amount:>12,.2f}\n"
            f"   ({self.description})"
        )


@dataclass
class MisstatementSummary:
    """错报汇总表"""
    summary_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    engagement_id: str = ""
    period: str = ""

    misstatements: list[Misstatement] = field(default_factory=list)
    adjustments: list[AdjustmentEntry] = field(default_factory=list)

    tolerable_error: Decimal = Decimal("0")      # 整体重要性水平
    de_minimis: Decimal = Decimal("0")            # 微小错报门槛（通常为 5% of tolerable）

    @property
    def total_known(self) -> Decimal:
        """已知错报合计"""
        return sum((m.amount for m in self.misstatements
                    if m.misstatement_type == MisstatementType.KNOWN), Decimal("0"))

    @property
    def total_likely(self) -> Decimal:
        """可能错报合计"""
        return sum((m.amount for m in self.misstatements
                    if m.misstatement_type == MisstatementType.LIKELY), Decimal("0"))

    @property
    def total_all(self) -> Decimal:
        """全部错报合计"""
        return sum((m.amount for m in self.misstatements), Decimal("0"))

    @property
    def exceeds_tolerable(self) -> bool:
        """是否超过重要性水平"""
        return self.total_all > self.tolerable_error

    @property
    def uncorrected_count(self) -> int:
        """未更正的错报数（超过微小门槛的）"""
        return sum(1 for m in self.misstatements
                   if m.amount >= self.de_minimis and m.passed_threshold)

    def summary_text(self) -> str:
        """生成错报汇总文本"""
        lines = [
            f"Misstatement Summary — {self.period}",
            f"{'='*55}",
            f"Tolerable Error: ${self.tolerable_error:,.2f}",
            f"De Minimis:      ${self.de_minimis:,.2f}",
            f"",
            f"  Known:       ${self.total_known:>12,.2f}",
            f"  Likely:      ${self.total_likely:>12,.2f}",
            f"  Total:       ${self.total_all:>12,.2f}",
            f"  Uncorrected: {self.uncorrected_count} items",
            f"",
            f"Conclusion: {'EXCEEDS tolerable error' if self.exceeds_tolerable else 'WITHIN tolerable error'}",
        ]
        if self.adjustments:
            lines.append(f"\nProposed Adjustments:")
            for i, adj in enumerate(self.adjustments, 1):
                lines.append(f"\n  [{i}] {adj.entry_type.value}-{adj.entry_id[:8]}")
                lines.append(f"      {adj.to_journal_text()}")
        return "\n".join(lines)


class MisstatementEngine:
    """错报引擎 — 从 Findings 生成 Misstatement 和 AdjustmentEntry"""

    def __init__(self, tolerable_error: Decimal = Decimal("0"),
                 de_minimis: Decimal = Decimal("0")):
        self._tolerable = tolerable_error
        self._de_minimis = de_minimis or (tolerable_error * Decimal("0.05"))

    def generate(self, findings: list, period: str = "FY2025",
                 engagement_id: str = "") -> MisstatementSummary:
        """从审计发现生成错报汇总"""
        from domain.audit.entities.procedure import FindingSeverity

        summary = MisstatementSummary(
            engagement_id=engagement_id,
            period=period,
            tolerable_error=self._tolerable,
            de_minimis=self._de_minimis,
        )

        for finding in findings:
            severity = finding.severity
            amount = self._to_decimal(finding.amount)

            # HIGH severity → Known misstatement
            if severity == FindingSeverity.HIGH:
                mtype = MisstatementType.KNOWN
            elif severity == FindingSeverity.MEDIUM:
                mtype = MisstatementType.LIKELY
            else:
                mtype = MisstatementType.PROJECTED

            mis = Misstatement(
                description=finding.description,
                misstatement_type=mtype,
                direction=MisstatementDirection.OVERSTATEMENT,
                amount=amount,
                account_debit="营业收入" if "Revenue" in finding.description else "相关收入科目",
                account_credit="合同负债 / 预收账款",
                assertion_affected="CUTOFF",
                finding_ref=finding.finding_id,
                passed_threshold=amount >= self._de_minimis,
            )
            summary.misstatements.append(mis)

            # 只在超过微小门槛时生成调整分录
            if mis.passed_threshold:
                adj = AdjustmentEntry(
                    entry_type=EntryType.AJE,
                    description=f"Revenue cutoff adjustment: {finding.description[:60]}",
                    date="2025-12-31",
                    period=period,
                    debit_account=mis.account_debit,
                    debit_amount=amount,
                    credit_account=mis.account_credit,
                    credit_amount=amount,
                    misstatement_refs=[mis.misstatement_id],
                )
                summary.adjustments.append(adj)

        return summary

    @staticmethod
    def _to_decimal(value) -> Decimal:
        """安全转换金额为 Decimal"""
        if value is None:
            return Decimal("0")
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        # 字符串 — 去除逗号/空格/货币符号
        cleaned = str(value).replace(",", "").replace(" ", "").replace("$", "").replace("¥", "")
        try:
            return Decimal(cleaned)
        except Exception:
            return Decimal("0")
