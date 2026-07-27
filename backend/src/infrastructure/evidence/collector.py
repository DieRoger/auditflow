"""Evidence Collector + Citation Builder"""

import uuid

import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class EvidenceSource(BaseModel):
    document_id: str
    page: int | None = None
    chunk_id: str | None = None
    excerpt: str = ""


class Evidence(BaseModel):
    evidence_id: str = ""
    claim: str
    source: EvidenceSource
    confidence: float = 0.0
    verified: bool = False


class Citation(BaseModel):
    claim: str
    document_id: str
    page: int | None = None
    chunk_id: str | None = None
    excerpt: str = ""
    confidence: float = 0.0


class EvidenceCollector:
    """证据收集器 — 将检索结果封装为结构化 Evidence"""

    async def collect(self, claim: str, sources: list[EvidenceSource]) -> list[Evidence]:
        """为一条 claim 收集证据"""
        evidences = []
        for src in sources:
            ev = Evidence(
                evidence_id=uuid.uuid4().hex[:12],
                claim=claim,
                source=src,
                confidence=0.8,
            )
            evidences.append(ev)
        logger.info("evidence_collected", claim=claim[:50], count=len(evidences))
        return evidences

    async def collect_batch(self, claims: list[str], sources_map: dict[str, list[EvidenceSource]]) -> list[Evidence]:
        """批量收集证据"""
        all_evidences = []
        for claim in claims:
            sources = sources_map.get(claim, [])
            evs = await self.collect(claim, sources)
            all_evidences.extend(evs)
        return all_evidences


class CitationBuilder:
    """Citation 构建器 — 将 Evidence 映射为标准 Citation 格式"""

    def build(self, evidences: list[Evidence]) -> list[Citation]:
        """从 Evidence 列表构建 Citation 列表"""
        citations = []
        for ev in evidences:
            cit = Citation(
                claim=ev.claim,
                document_id=ev.source.document_id,
                page=ev.source.page,
                chunk_id=ev.source.chunk_id,
                excerpt=ev.source.excerpt[:200],
                confidence=ev.confidence,
            )
            citations.append(cit)
        logger.info("citations_built", count=len(citations))
        return citations
