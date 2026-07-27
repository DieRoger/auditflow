"""Evidence 层 — 证据收集 + Citation + Grounding"""

from .collector import Citation, CitationBuilder, Evidence, EvidenceCollector, EvidenceSource
from .grounding import GroundingChecker, GroundingResult

__all__ = [
    "EvidenceCollector", "CitationBuilder",
    "Evidence", "EvidenceSource", "Citation",
    "GroundingChecker", "GroundingResult",
]
