# ruff: noqa: E501
"""Report Generator — 审计报告生成

确定性 Service — ISA 700 标准结构 + 强制 HITL。
"""

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

OPINION_TYPES = ["Unqualified", "Qualified", "Adverse", "Disclaimer", "Modified"]


class ReportSection(BaseModel):
    title: str
    content: str = ""
    citations: list[str] = Field(default_factory=list)


class AuditReport(BaseModel):
    title: str = ""
    opinion: str = "Unqualified"
    client: str = ""
    period: str = ""
    sections: list[ReportSection] = Field(default_factory=list)
    requires_human_review: bool = True

    def to_markdown(self) -> str:
        lines = [f"# {self.title}", f"**Opinion:** {self.opinion}", f"**Client:** {self.client} | **Period:** {self.period}", "---"]
        for sec in self.sections:
            lines.append(f"## {sec.title}")
            lines.append(sec.content)
        lines.append("---")
        lines.append("*This report was AI-assisted and requires human review and signature.*")
        return "\n".join(lines)


class ReportGenerator:
    """审计报告生成器 — ISA 700 标准结构

    强制 next_action = HUMAN_REVIEW，禁止自动批准。
    """

    def generate(self, client: str, period: str, opinion: str = "Unqualified",
                 findings: list[dict] | None = None) -> AuditReport:
        if opinion not in OPINION_TYPES:
            raise ValueError(f"Unsupported opinion: {opinion}. Must be one of {OPINION_TYPES}")

        sections = [
            ReportSection(title="Audit Opinion", content=f"We have audited the financial statements of {client} for the period {period}."),
            ReportSection(title="Basis for Opinion", content="We conducted our audit in accordance with ISA."),
            ReportSection(title="Key Audit Matters", content="; ".join([f.get("area", "") for f in (findings or [])]) if findings else "None identified."),
            ReportSection(title="Management Responsibilities", content="Management is responsible for the preparation and fair presentation of the financial statements."),
            ReportSection(title="Auditor Responsibilities", content="Our objectives are to obtain reasonable assurance about whether the financial statements as a whole are free from material misstatement."),
        ]

        report = AuditReport(
            title=f"Independent Auditor's Report — {client}",
            opinion=opinion, client=client, period=period,
            sections=sections, requires_human_review=True,
        )
        logger.info("report_generated", client=client, opinion=opinion)
        return report
