"""Agent Contract 序列化/反序列化验证测试"""

import json

from domain.contracts import AgentError, AgentRequest, AgentResponse, Citation


def test_agent_request_serialization():
    req = AgentRequest(
        workflow_id="wf_001",
        project_id="proj_001",
        task_id="task_001",
        firm_id="firm_001",
        client_id="client_001",
        engagement_id="eng_001",
        inputs={"audit_area": "Revenue"},
    )
    data = json.loads(req.model_dump_json())
    assert data["workflow_id"] == "wf_001"
    assert data["inputs"]["audit_area"] == "Revenue"


def test_agent_response_with_citations():
    resp = AgentResponse(
        status="SUCCESS",
        result={"risk_level": "HIGH"},
        citations=[
            Citation(
                claim="Revenue increased 45%",
                document_id="doc_001",
                page=32,
                excerpt="Revenue increased from 100M to 145M",
                confidence=0.96,
            )
        ],
        confidence=0.92,
        metrics={"tokens": 450, "cost": 0.02},
        next_action="HUMAN_REVIEW",
    )
    data = json.loads(resp.model_dump_json())
    assert data["status"] == "SUCCESS"
    assert len(data["citations"]) == 1
    assert data["citations"][0]["document_id"] == "doc_001"


def test_agent_error():
    err = AgentError(
        reason="LLM timeout after 30s",
        recoverable=True,
        retry_context={"retry_count": 1},
    )
    data = json.loads(err.model_dump_json())
    assert data["status"] == "FAILED"
    assert data["recoverable"] is True


def test_citation_defaults():
    cit = Citation(
        claim="Test claim",
        document_id="doc_001",
        excerpt="Test excerpt",
    )
    assert cit.page is None
    assert cit.chunk_id is None
    assert cit.confidence == 0.0
