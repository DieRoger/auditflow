# ruff: noqa: E501
"""LLM Planner Agent — 审计任务拆解"""
from agents.base import ToolDefinition
from agents.base_llm import LlmBaseAgent
from domain.artifacts import AuditPlanArtifact, AuditPlanContent
from domain.contracts import AgentRequest, AgentResponse

PLANNER_SYSTEM = "You are an audit planning expert. Decompose audit tasks into agent execution sequences. Return ONLY valid JSON."
PLANNER_PROMPT = """Audit area: {audit_area}
Project context: {context}

Return JSON:
{{"plan": [{{"step": N, "agent": "knowledge_agent|evidence_agent|risk_agent", "task": "description", "expected_output": "what to produce"}}]}}"""


class LlmPlannerAgent(LlmBaseAgent):
    name = "planner_agent"
    version = "0.2.0"

    async def execute(self, request: AgentRequest) -> AgentResponse:
        result = await self.call_llm(PLANNER_SYSTEM, PLANNER_PROMPT.format(
            audit_area=request.inputs.get("audit_area", "General"),
            context=str(request.inputs.get("project_context", {}))[:500],
        ))
        plan = result.get("plan", [{"step": 1, "agent": "knowledge_agent", "task": "检索审计准则"}])
        content = AuditPlanContent(materiality={"overall": "5M", "performance": "3.75M", "basis": "Total Assets"}, procedures=[{"procedure_id": f"p{p['step']}", "target_risk_id": "", "assertion": "", "steps": [p.get("task", "")]} for p in plan])
        artifact = AuditPlanArtifact(artifact_id=f"plan_{request.workflow_id[:8]}", created_by="planner_agent", content=content.model_dump(), citations=[])
        return AgentResponse(status="SUCCESS", result={"artifact": artifact.model_dump(), "plan": plan}, citations=[], confidence=0.85, metrics={"tasks": len(plan), "tokens": getattr(self, '_last_tokens', 0)}, next_action="KNOWLEDGE_AGENT")

    def get_tools(self):
        return [ToolDefinition(name="ontology_query"), ToolDefinition(name="agent_catalog")]
