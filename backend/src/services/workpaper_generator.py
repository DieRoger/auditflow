# ruff: noqa: E501
"""Workpaper Generator — 审计工作底稿生成

确定性 Service — 模板渲染 + Citation 嵌入 → Markdown/PDF。
"""


import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class WorkpaperSection(BaseModel):
    section_id: str
    title: str
    content: str = ""
    table: list[dict] | None = None
    citations: list[str] = Field(default_factory=list)


class Workpaper(BaseModel):
    title: str
    client: str = ""
    period: str = ""
    prepared_by: str = ""
    sections: list[WorkpaperSection] = Field(default_factory=list)
    format: str = "markdown"

    def to_markdown(self) -> str:
        lines = [f"# {self.title}", f"**Client:** {self.client} | **Period:** {self.period} | **Prepared by:** {self.prepared_by}", "---"]
        for sec in self.sections:
            lines.append(f"## {sec.title}")
            lines.append(sec.content)
            if sec.table:
                for row in sec.table:
                    lines.append(f"- {row}")
            lines.append("")
        return "\n".join(lines)


class WorkpaperGenerator:
    """工作底稿生成器 — 基于模板的结构化底稿生成"""

    def generate(self, title: str, client: str, period: str, sections: list[WorkpaperSection]) -> Workpaper:
        wp = Workpaper(title=title, client=client, period=period, prepared_by="AuditFlow AI", sections=sections)
        logger.info("workpaper_generated", title=title, sections=len(sections))
        return wp

    def generate_from_risk_finding(self, risk_finding: dict, client: str, period: str) -> Workpaper:
        sections = [
            WorkpaperSection(section_id="objective", title="Audit Objective", content="验证相关认定的真实性和准确性"),
            WorkpaperSection(section_id="risk", title="Risk Assessment", content=risk_finding.get("title", ""), citations=risk_finding.get("indicators", [])),
            WorkpaperSection(section_id="procedures", title="Procedures Performed",
                             table=[{"procedure": p.get("type", ""), "steps": "; ".join(p.get("steps", []))} for p in risk_finding.get("suggested_procedures", [])]),
            WorkpaperSection(section_id="conclusion", title="Conclusion", content="待审计师审核确认"),
        ]
        return self.generate(title=f"Workpaper — {risk_finding.get('area', 'Audit')}", client=client, period=period, sections=sections)
