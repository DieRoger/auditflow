"""Audit Completion Domain — Phase E

Partner Review, EQCR, Representation Letter, Audit Opinion, Archive
"""

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class OpinionType(Enum):
    UNQUALIFIED = "UNQUALIFIED"             # 无保留意见
    QUALIFIED = "QUALIFIED"                 # 保留意见
    ADVERSE = "ADVERSE"                     # 否定意见
    DISCLAIMER = "DISCLAIMER"               # 无法表示意见


class ReviewConclusion(Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REQUIRES_CHANGES = "REQUIRES_CHANGES"


@dataclass
class PartnerReview:
    """合伙人复核"""
    review_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    reviewer: str = ""
    review_date: Optional[date] = None
    conclusion: ReviewConclusion = ReviewConclusion.APPROVED
    notes: str = ""
    issues_found: list[str] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "review_id": self.review_id,
            "reviewer": self.reviewer,
            "conclusion": self.conclusion.value,
            "issues": len(self.issues_found),
        }


@dataclass
class EQCR:
    """Engagement Quality Control Review — 项目质量控制复核"""
    eqcr_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    reviewer: str = ""                              # EQCR 复核人（须独立于项目组）
    review_date: Optional[date] = None
    conclusion: ReviewConclusion = ReviewConclusion.APPROVED
    key_judgments_reviewed: list[str] = field(default_factory=list)  # 复核的关键判断
    notes: str = ""

    def summary(self) -> dict:
        return {
            "eqcr_id": self.eqcr_id,
            "reviewer": self.reviewer,
            "conclusion": self.conclusion.value,
            "judgments_reviewed": self.key_judgments_reviewed,
        }


@dataclass
class AuditOpinion:
    """审计意见"""
    opinion_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    opinion_type: OpinionType = OpinionType.UNQUALIFIED
    issuance_date: Optional[date] = None
    basis_paragraphs: list[str] = field(default_factory=list)  # 形成意见的基础
    emphasis_of_matter: Optional[str] = None                     # 强调事项段
    other_matter: Optional[str] = None                           # 其他事项段
    going_concern_noted: bool = False                            # 持续经营重大不确定性

    def is_clean(self) -> bool:
        return self.opinion_type == OpinionType.UNQUALIFIED and self.emphasis_of_matter is None

    def to_report_text(self) -> str:
        """生成审计意见文本"""
        lines = [
            "INDEPENDENT AUDITOR'S REPORT",
            "=" * 40,
            f"",
            f"Opinion",
            f"{'-'*40}",
        ]
        if self.opinion_type == OpinionType.UNQUALIFIED:
            lines.append("We have audited the financial statements of the Company, which")
            lines.append("present fairly, in all material respects, the financial position")
            lines.append("as of December 31, 2025, in accordance with applicable standards.")
        elif self.opinion_type == OpinionType.QUALIFIED:
            lines.append("Except for the effects of the matter described in the Basis for")
            lines.append("Qualified Opinion section, the financial statements present fairly...")
        elif self.opinion_type == OpinionType.ADVERSE:
            lines.append("Because of the significance of the matters described in the Basis")
            lines.append("for Adverse Opinion section, the financial statements do NOT present fairly...")
        else:
            lines.append("We were unable to obtain sufficient appropriate audit evidence to")
            lines.append("provide a basis for an audit opinion. We do NOT express an opinion.")

        if self.emphasis_of_matter:
            lines.append(f"\nEmphasis of Matter")
            lines.append(f"{'-'*40}")
            lines.append(self.emphasis_of_matter)

        if self.going_concern_noted:
            lines.append(f"\nMaterial Uncertainty Related to Going Concern")
            lines.append(f"{'-'*40}")
            lines.append("We draw attention to Note X in the financial statements, which")
            lines.append("indicates that the Company incurred a net loss and has net current")
            lines.append("liabilities. These conditions indicate that a material uncertainty")
            lines.append("exists that may cast significant doubt on the Company's ability")
            lines.append("to continue as a going concern.")

        return "\n".join(lines)


@dataclass
class ManagementRepresentation:
    """管理层声明书"""
    letter_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    signed_by: str = ""             # 签字人（通常为 CEO/CFO）
    signed_date: Optional[date] = None
    status: str = "UNSIGNED"        # UNSIGNED → SIGNED
    representations: list[str] = field(default_factory=list)  # 管理层声明事项

    def sign(self, signer: str) -> None:
        self.signed_by = signer
        self.signed_date = date.today()
        self.status = "SIGNED"

    def to_letter_text(self) -> str:
        """生成管理层声明书文本"""
        return (
            f"MANAGEMENT REPRESENTATION LETTER\n"
            f"{'='*50}\n\n"
            f"To the Independent Auditor,\n\n"
            f"We confirm, to the best of our knowledge and belief, the following\n"
            f"representations made to you during your audit:\n\n"
            + "\n".join(f"  - {r}" for r in self.representations)
            + f"\n\n"
            + f"Signed: {self.signed_by or '[pending]'}\n"
            + f"Date: {self.signed_date or '[pending]'}\n"
        )


@dataclass
class EngagementArchive:
    """审计档案归档"""
    archive_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    engagement_id: str = ""
    archived_at: datetime = field(default_factory=datetime.now)
    status: str = "ACTIVE"          # ACTIVE → ARCHIVED
    retention_years: int = 5        # 档案保存年限
    files: list[str] = field(default_factory=list)  # 归档文件列表

    def archive(self) -> None:
        self.status = "ARCHIVED"
        self.archived_at = datetime.now()


@dataclass
class AuditCompletion:
    """审计完成 — 聚合全部完成阶段文档"""
    completion_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    engagement_id: str = ""
    period: str = "FY2025"

    partner_review: Optional[PartnerReview] = None
    eqcr: Optional[EQCR] = None
    opinion: Optional[AuditOpinion] = None
    representation: Optional[ManagementRepresentation] = None
    archive: Optional[EngagementArchive] = None

    # 引用 Phase D 的 MisstatementSummary
    misstatement_summary: Optional[dict] = None

    def is_complete(self) -> bool:
        """所有签核是否完成"""
        checks = []
        if self.partner_review:
            checks.append(self.partner_review.conclusion == ReviewConclusion.APPROVED)
        if self.eqcr:
            checks.append(self.eqcr.conclusion == ReviewConclusion.APPROVED)
        if self.representation:
            checks.append(self.representation.status == "SIGNED")
        if self.opinion:
            checks.append(self.opinion.issuance_date is not None)
        return all(checks) and len(checks) >= 3

    def determine_opinion(self, misstatement_exceeds: bool, evidence_insufficient: bool) -> OpinionType:
        """根据错报汇总和证据充分性判定审计意见类型"""
        if misstatement_exceeds and evidence_insufficient:
            return OpinionType.DISCLAIMER
        elif misstatement_exceeds:
            return OpinionType.ADVERSE
        elif evidence_insufficient:
            return OpinionType.QUALIFIED
        return OpinionType.UNQUALIFIED

    def summary(self) -> dict:
        return {
            "completion_id": self.completion_id,
            "period": self.period,
            "complete": self.is_complete(),
            "partner_review": self.partner_review.summary() if self.partner_review else None,
            "eqcr": self.eqcr.summary() if self.eqcr else None,
            "opinion": self.opinion.opinion_type.value if self.opinion else "UNDETERMINED",
            "representation": self.representation.status if self.representation else "UNSIGNED",
            "archive": self.archive.status if self.archive else "NOT_ARCHIVED",
            "misstatement_exceeds": self.misstatement_summary.get("exceeds", False) if self.misstatement_summary else False,
        }
