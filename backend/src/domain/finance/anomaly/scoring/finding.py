"""Finding — 可解释审计发现

连接 Risk Scoring Engine → Procedure Agent → Evidence Graph。
Finding 包含: 风险类型、分数、触发的信号、证据、解释、建议。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Finding:
    """单个可解释审计发现"""
    finding_id: str = ""
    transaction_ref: str = ""
    risk_type: str = ""             # Revenue Fraud / Expense Fraud
    score: float = 0.0
    threshold: float = 0.0
    severity: str = "LOW"           # HIGH / MEDIUM / LOW
    flagged: bool = False
    signals: list[dict] = field(default_factory=list)   # 触发的信号
    breakdown: dict = field(default_factory=dict)       # 信号分解
    reason: Optional[str] = None
    created_at: str = ""

    def __post_init__(self):
        if not self.finding_id:
            import uuid
            self.finding_id = uuid.uuid4().hex[:12]
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.severity or self.severity == "LOW":
            if self.score >= 15:
                self.severity = "HIGH"
            elif self.score >= 8:
                self.severity = "MEDIUM"

    def to_markdown(self) -> str:
        """生成 Finding 的 Markdown 说明"""
        lines = [
            f"### Finding: {self.risk_type}",
            f"**Score:** {self.score} / {self.threshold} (threshold) — {'FLAGGED' if self.flagged else 'OK'}",
            f"**Severity:** {self.severity}",
        ]
        if self.reason:
            lines.append(f"**Reason:** {self.reason}")
        if self.signals:
            lines.append(f"\n**Signals ({len(self.signals)} detected):**")
            for s in self.signals:
                lines.append(f"- [{s['severity']}] {s['signal']} (score: {s['score']})")
                if s.get("explanation"):
                    lines.append(f"  - {s['explanation']}")
                if s.get("evidence"):
                    lines.append(f"  - Evidence: {', '.join(s['evidence'])}")
                if s.get("recommendation"):
                    lines.append(f"  - Recommendation: {s['recommendation']}")
        return "\n".join(lines)
