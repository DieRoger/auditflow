"""Retrieval + Evidence 测试"""

import pytest

from infrastructure.retrieval.hybrid_search import HybridResult, Reranker
from infrastructure.retrieval.keyword_search import ScoredHit


@pytest.mark.asyncio
async def test_reranker_sorts_by_score():
    r = Reranker()
    hits = [
        ScoredHit(chunk_id="a", source_type="doc", source_id="1", content="a", score=0.5),
        ScoredHit(chunk_id="b", source_type="doc", source_id="2", content="b", score=0.9),
        ScoredHit(chunk_id="c", source_type="doc", source_id="3", content="c", score=0.3),
    ]
    result = await r.rerank("test", hits, top_k=2)
    assert len(result) == 2
    assert result[0].chunk_id == "b"
    assert result[1].chunk_id == "a"


def test_scored_hit_model():
    hit = ScoredHit(chunk_id="c1", source_type="CLIENT_DOCUMENT", source_id="doc_1",
                    content="Revenue increased 45%", score=0.95)
    assert hit.chunk_id == "c1"
    assert hit.score == 0.95


def test_hybrid_result_model():
    hr = HybridResult(hits=[], total_before_merge=50)
    assert hr.total_before_merge == 50
    assert len(hr.hits) == 0
