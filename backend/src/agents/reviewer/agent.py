# ruff: noqa: E501
"""LLM Reviewer Agent — 审计质量审查"""
from agents.base import ToolDefinition
from agents.base_llm import LlmBaseAgent
from domain.artifacts import ReviewIssue, ReviewReportArtifact, ReviewReportContent
from domain.contracts import AgentRequest, AgentResponse

REVIEWER_SYSTEM = "You are an audit quality reviewer. Review upstream Agent outputs for completeness, accuracy, and hallucination. Return ONLY valid JSON."
REVIEWER_PROMPT = """Upstream artifacts: {artifacts}

Return JSON:
{{"review_result": "APPROVED|NEEDS_REVISION|REJECTED", "quality_score": 0.0-1.0, "hallucination_risk": 0.0-1.0,
 "issues": [{{"severity": "HIGH|MEDIUM|LOW", "issue_type": "UNSUPPORTED_CLAIM|MISSING_CITATION|WEAK_LOGIC|HALLUCINATION", "location": "where", "description": "what", "suggestion": "how to fix"}}]}}"""


class LlmReviewerAgent(LlmBaseAgent):
    name = "reviewer_agent"
    version = "0.2.0"

    async def execute(self, request: AgentRequest) -> AgentResponse:
        artifacts = [
            {"node": k, "type": v.get("artifact", {}).get("artifact_type", "unknown")}
            for k, v in request.context.items()
            if isinstance(v, dict)
        ] if request.context else [{"node": "upstream", "type": "unknown"}]
        result = await self.call_llm(REVIEWER_SYSTEM, REVIEWER_PROMPT.format(artifacts=str(artifacts)[:600]))
        issues = [ReviewIssue(severity=i.get("severity", "LOW"), issue_type=i.get("issue_type", "MISSING_CITATION"),
            location=i.get("location", "unknown"), description=i.get("description", ""), suggestion=i.get("suggestion", ""))
            for i in result.get("issues", [])]
        content = ReviewReportContent(review_result=result.get("review_result", "APPROVED"), issues=issues,
            quality_score=result.get("quality_score", 0.85), hallucination_risk=result.get("hallucination_risk", 0.1))
        artifact = ReviewReportArtifact(artifact_id=f"review_{request.workflow_id[:8]}", created_by="reviewer_agent", content=content.model_dump(), citations=[])
        return AgentResponse(status="SUCCESS", result={"artifact": artifact.model_dump(), "quality_score": content.quality_score},
            citations=[], confidence=content.quality_score, metrics={"issues": len(issues), "quality": content.quality_score, "tokens": getattr(self, '_last_tokens', 0)},
            next_action="HUMAN_REVIEW")

    def get_tools(self):
        return [ToolDefinition(name="evidence_search"), ToolDefinition(name="grounding_checker")]
