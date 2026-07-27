"""Audit Services 测试"""

import pytest

from services.report_generator import ReportGenerator
from services.workpaper_generator import WorkpaperGenerator, WorkpaperSection


def test_workpaper_generator():
    g = WorkpaperGenerator()
    sections = [WorkpaperSection(section_id="s1", title="Objective", content="Verify revenue")]
    wp = g.generate("Test WP", "Client A", "FY2025", sections)
    assert wp.title == "Test WP"
    assert len(wp.sections) == 1
    assert "Objective" in wp.to_markdown()


def test_workpaper_from_risk():
    g = WorkpaperGenerator()
    risk = {"area": "Revenue Recognition", "title": "Aggressive Revenue",
            "indicators": ["45% growth"], "suggested_procedures":  # noqa: E501
            [{"type": "Inspection", "steps": ["Review contracts"]}]}
    wp = g.generate_from_risk_finding(risk, "Client A", "FY2025")
    assert "Revenue Recognition" in wp.title
    assert len(wp.sections) >= 3


def test_report_generator():
    g = ReportGenerator()
    report = g.generate(client="Client A", period="FY2025", opinion="Unqualified")
    assert report.title == "Independent Auditor's Report — Client A"
    assert report.requires_human_review is True
    assert "Unqualified" in report.to_markdown()


def test_report_invalid_opinion():
    g = ReportGenerator()
    with pytest.raises(ValueError):
        g.generate(client="A", period="FY2025", opinion="InvalidOp")
