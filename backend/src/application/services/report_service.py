"""Report Application Service — 工作底稿 + 审计报告生成 Use Case"""

import structlog

from services.workpaper_generator import WorkpaperGenerator, WorkpaperSection
from services.report_generator import ReportGenerator

logger = structlog.get_logger(__name__)


class ReportService:
    """审计报告生成 Use Case"""

    def __init__(self):
        self._workpaper_gen = WorkpaperGenerator()
        self._report_gen = ReportGenerator()

    async def generate_workpaper(self, agent_results: dict, client: str = "Client") -> str:
        """从 Agent 结果生成工作底稿"""
        risk_result = agent_results.get("risk", {}).get("result", {})
        risk_content = risk_result.get("artifact", {}).get("content", {})
        evidence_result = agent_results.get("evidence", {}).get("result", {})

        sections = [
            WorkpaperSection(section_id="summary", title="Engagement Summary",
                             content=f"Client: {client}\nArea: {risk_content.get('area', 'N/A')}"),
            WorkpaperSection(section_id="risk", title="Risk Assessment",
                             content=risk_content.get("title", "N/A"),
                             citations=risk_content.get("indicators", [])),
            WorkpaperSection(section_id="evidence", title="Evidence Analysis",
                             content=f"Coverage: {evidence_result.get('coverage', 0)}"),
        ]
        wp = self._workpaper_gen.generate(
            title=f"Workpaper — {risk_content.get('area', 'Audit')}",
            client=client, period="2024", sections=sections,
        )
        return wp.to_markdown()

    async def generate_report(self, agent_results: dict, client: str = "Client") -> str:
        """从 Agent 结果生成审计报告"""
        reviewer = agent_results.get("reviewer", {}).get("result", {})
        review_content = reviewer.get("artifact", {}).get("content", {})
        risk_content = agent_results.get("risk", {}).get("result", {}).get("artifact", {}).get("content", {})

        report = self._report_gen.generate(
            client=client, period="2024",
            opinion="Qualified" if (review_content.get("hallucination_risk") or 0) > 0.3 else "Unqualified",
            findings=[{"area": risk_content.get("title", "N/A"), "severity": risk_content.get("severity", "MEDIUM")}],
        )
        report.sections.append(type(report.sections[0])(
            title="AI Quality Review",
            content=f"Score: {review_content.get('quality_score', 0):.0%} | Hallucination: {review_content.get('hallucination_risk', 0):.0%}",
        ))
        return report.to_markdown()
