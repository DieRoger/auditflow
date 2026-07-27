"""Grounding Checker 测试"""

import pytest

from infrastructure.evidence.collector import Citation
from infrastructure.evidence.grounding import GroundingChecker


@pytest.mark.asyncio
async def test_verify_with_valid_citations():
    checker = GroundingChecker()
    citations = [
        Citation(claim="Revenue up 45%", document_id="report.pdf", excerpt="Revenue 2025: $145M", confidence=0.95),
        Citation(claim="Revenue up 45%", document_id="notes.pdf",  # noqa: E501
                 excerpt="Growth driven by new contracts", confidence=0.88),
    ]
    result = await checker.verify("Revenue increased 45%", citations)
    assert result.grounded is True
    assert result.score >= 0.5
    assert result.hallucination_risk < 0.5


@pytest.mark.asyncio
async def test_verify_no_citations():
    checker = GroundingChecker()
    result = await checker.verify("Unsupported claim", [])
    assert result.grounded is False
    assert result.hallucination_risk == 1.0


@pytest.mark.asyncio
async def test_verify_low_confidence():
    checker = GroundingChecker()
    citations = [
        Citation(claim="Test", document_id="doc.pdf", excerpt="...", confidence=0.1),
    ]
    result = await checker.verify("Test claim", citations)
    assert result.grounded is False


@pytest.mark.asyncio
async def test_verify_dict_citations():
    checker = GroundingChecker()
    from infrastructure.evidence.collector import Citation
    citations = [Citation(document_id="doc.pdf", excerpt="data", confidence=0.9, claim="test")]
    result = await checker.verify("Dict claim", citations)
    assert result.grounded is True
