"""ReviewQueue — Assessment → Human Review → Procedure (ISA 500 HITL)

AI 提供候选，审计师做最终判断。

三态决策:
  ACCEPT             → 进入 Procedure Planning
  DISMISS            → 跳过（审计师认为无风险）
  NEED_MORE_EVIDENCE → 暂停，待证据补充后再审（Evidence Graph 缺失时）

设计原则: AI 永远不直接决定执行程序，只推荐。
"""

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class ReviewDecision(Enum):
    ACCEPT = "ACCEPT"
    DISMISS = "DISMISS"
    NEED_MORE_EVIDENCE = "NEED_MORE_EVIDENCE"


class ReviewStatus(Enum):
    PENDING = "PENDING"
    REVIEWED = "REVIEWED"


@dataclass
class ReviewItem:
    """一条待人工复核的风险项"""
    item_id: str = ""
    area: str = ""                # Revenue / Purchase / ...
    risk_level: str = "LOW"       # Assessment.overall_risk
    summary: str = ""             # AI 摘要（为什么推荐）
    evidence_summary: str = ""    # 证据情况（来自 Evidence Graph）
    findings_count: int = 0
    status: ReviewStatus = ReviewStatus.PENDING
    decision: ReviewDecision | None = None
    reviewer_comment: str = ""
    reviewed_at: str = ""

    def review(self, decision: ReviewDecision, comment: str = "") -> None:
        """审计师做出决策"""
        self.decision = decision
        self.reviewer_comment = comment
        self.status = ReviewStatus.REVIEWED
        self.reviewed_at = datetime.now().isoformat()


@dataclass
class ReviewQueue:
    """复核队列 — Assessment 输出到 Procedure 之间的 HITL 闸门"""
    items: list[ReviewItem] = field(default_factory=list)

    def add(self, item: ReviewItem) -> None:
        self.items.append(item)

    def pending(self) -> list[ReviewItem]:
        return [i for i in self.items if i.status == ReviewStatus.PENDING]

    def accepted(self) -> list[ReviewItem]:
        return [i for i in self.items if i.decision == ReviewDecision.ACCEPT]

    def dismissed(self) -> list[ReviewItem]:
        return [i for i in self.items if i.decision == ReviewDecision.DISMISS]

    def need_more_evidence(self) -> list[ReviewItem]:
        return [i for i in self.items if i.decision == ReviewDecision.NEED_MORE_EVIDENCE]

    def is_fully_reviewed(self) -> bool:
        return len(self.pending()) == 0

    def summary(self) -> dict:
        return {
            "total": len(self.items),
            "pending": len(self.pending()),
            "accepted": len(self.accepted()),
            "dismissed": len(self.dismissed()),
            "need_more_evidence": len(self.need_more_evidence()),
        }

    def accepted_risk_levels(self) -> list[str]:
        """已接受项的风险等级（决定 Procedure 的输入）"""
        return [i.risk_level for i in self.accepted()]

    def max_accepted_risk(self) -> str:
        """已接受项的最高风险等级 — 决定审计程序力度"""
        order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        levels = self.accepted_risk_levels()
        if not levels:
            return "LOW"
        return max(levels, key=lambda lv: order.get(lv, 0))


def build_review_queue(
    assessment,
    evidence_summary: str = "Evidence incomplete — DELIVERY/CONTRACT missing",
) -> ReviewQueue:
    """从 Assessment 构建 Review Queue

    HIGH risk 自动建议 ACCEPT（仍需人工确认）
    MEDIUM/LOW 进入队列由审计师判断
    """
    queue = ReviewQueue()
    queue.add(ReviewItem(
        item_id=f"rv_{assessment.narrative_risk.get('area', 'general').lower()[:8]}",
        area=assessment.narrative_risk.get("area", "General"),
        risk_level=assessment.overall_risk,
        summary=assessment.narrative_risk.get("title", "Risk assessment"),
        evidence_summary=evidence_summary,
        findings_count=len(assessment.detected_findings),
    ))
    return queue


# ── Reviewer Feedback Loop (HITL Quality) ───────────────────────

class ReviewCalibration:
    """复核反馈统计 — Accepted Finding Rate 与校准

    衡量 HITL 质量: AI 建议被审计师接受的比例。
    不修改权重（Benchmark v1.0 FROZEN）— 只统计与报告。
    """

    @staticmethod
    def accepted_finding_rate(queue: ReviewQueue) -> float:
        """Accepted Finding Rate = accepted / reviewed"""
        reviewed = queue.items
        if not reviewed:
            return 0.0
        accepted = sum(1 for i in reviewed
                       if i.decision == ReviewDecision.ACCEPT)
        return accepted / len(reviewed) * 100

    @staticmethod
    def decision_distribution(queue: ReviewQueue) -> dict:
        """三态分布"""
        return {
            "accepted": len(queue.accepted()),
            "dismissed": len(queue.dismissed()),
            "need_more_evidence": len(queue.need_more_evidence()),
            "total_reviewed": len(queue.items),
        }

    @staticmethod
    def simulate_calibration(initial_accept: int, initial_total: int,
                             improved_accept: int, improved_total: int) -> dict:
        """演示校准前后对比（如 67% → 82%）"""
        before = initial_accept / initial_total * 100 if initial_total else 0
        after = improved_accept / improved_total * 100 if improved_total else 0
        return {
            "before_pct": round(before, 1),
            "after_pct": round(after, 1),
            "improvement": round(after - before, 1),
        }
