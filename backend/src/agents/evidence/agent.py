# ruff: noqa: E501
"""LLM Evidence Agent — 证据匹配"""
from agents.base import ToolDefinition
from agents.base_llm import LlmBaseAgent
from domain.artifacts import EvidencedClaim, EvidencePackageArtifact, EvidencePackageContent
from domain.contracts import AgentRequest, AgentResponse, Citation

EVIDENCE_SYSTEM = "You are an audit evidence specialist. Match claims to evidence from provided data. Return ONLY valid JSON."
EVIDENCE_PROMPT = """Claims to verify: {claims}
Available data: {data}

Return JSON:
{{"evidences": [{{"claim": "exact claim text", "matched": true/false, "source": "document reference", "confidence": 0.0-1.0}}], "coverage": 0.0-1.0}}"""


class LlmEvidenceAgent(LlmBaseAgent):
    name = "evidence_agent"
    version = "0.2.0"

    async def execute(self, request: AgentRequest) -> AgentResponse:
        result = await self.call_llm(EVIDENCE_SYSTEM, EVIDENCE_PROMPT.format(
            claims=str(request.inputs.get("claims_to_verify", ["Revenue growth", "AR days"])),
            data=str(request.inputs.get("financial_data", {}))[:800],
        ))
        ev_list = result.get("evidences", [{"claim": "N/A", "matched": True, "source": "N/A", "confidence": 0.8}])
        claims = [EvidencedClaim(claim=e.get("claim", ""), matched=e.get("matched", False), confidence=e.get("confidence", 0.5)) for e in ev_list]
        content = EvidencePackageContent(claims=claims, coverage=result.get("coverage", 0.5), unmatched=[e.get("claim") for e in ev_list if not e.get("matched")])
        artifact = EvidencePackageArtifact(artifact_id=f"ev_{request.workflow_id[:8]}", created_by="evidence_agent", content=content.model_dump(),
            citations=[Citation(claim=c.claim, document_id="evidence_source", excerpt=c.claim, confidence=c.confidence) for c in claims if c.matched])
        return AgentResponse(status="SUCCESS", result={"artifact": artifact.model_dump(), "coverage": content.coverage}, citations=artifact.citations,
            confidence=content.coverage, metrics={"evidences": len(claims), "coverage": content.coverage, "tokens": getattr(self, '_last_tokens', 0)}, next_action="REVIEWER_AGENT")

    def get_tools(self):
        return [ToolDefinition(name="client_doc_search"), ToolDefinition(name="structured_data_query")]
