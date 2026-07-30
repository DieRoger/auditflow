"""Finding — Audit Core 的可解释审计发现

Finding 是整个 AuditFlow 的统一语言 (Canonical Audit Finding):
  Risk Agent → Finding → Procedure Agent → Evidence Graph → Working Paper
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class EvidenceRef:
    """证据引用"""
    document_id: str = ""
    page: Optional[int] = None
    excerpt: str = ""


@dataclass
class ProcedureRef:
    """程序引用"""
    procedure_id: str = ""
    name: str = ""


@dataclass
class Assertion:
    """审计认定"""
    name: str = ""  # OCCURRENCE, COMPLETENESS, CUTOFF, etc.


@dataclass
class Finding:
    """统一审计发现 — AuditFlow 标准中间对象"""
    finding_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    risk_type: str = ""
    severity: str = "LOW"
    confidence: float = 0.0
    score: float = 0.0
    triggered_signals: list[dict] = field(default_factory=list)
    evidence_refs: list[EvidenceRef] = field(default_factory=list)
    recommended_procedures: list[ProcedureRef] = field(default_factory=list)
    affected_assertions: list[Assertion] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_markdown(self) -> str:
        lines = [
            f"### Finding: {self.risk_type}",
            f"**Severity:** {self.severity} | **Score:** {self.score} | **Confidence:** {self.confidence:.0%}",
        ]
        if self.triggered_signals:
            lines.append(f"\n**Signals ({len(self.triggered_signals)}):**")
            for s in self.triggered_signals:
                lines.append(f"- [{s['severity']}] {s['signal']}: {s.get('explanation', '')}")
        if self.evidence_refs:
            lines.append(f"\n**Evidence:**")
            for e in self.evidence_refs:
                lines.append(f"- doc={e.document_id} page={e.page}")
        if self.recommended_procedures:
            lines.append(f"\n**Procedures:**")
            for p in self.recommended_procedures:
                lines.append(f"- {p.name}")
        return "\n".join(lines)
