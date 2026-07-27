"""Risk Application Service — 风险分析 Use Case

协调 Workflow Engine + Agents 完成端到端风险分析。
"""

import structlog

from agents.base import AgentRegistry
from workflows.engine import WorkflowEngine
from workflows.models import AgentNode, Edge, GraphDefinition

logger = structlog.get_logger(__name__)


class RiskService:
    """风险分析 Use Case"""

    def __init__(self, registry: AgentRegistry):
        self._registry = registry

    async def analyze(self, audit_area: str, financial_data: dict = None,
                      document_chunks: list[dict] = None) -> dict:
        """执行端到端风险分析 Workflow"""
        engine = WorkflowEngine(self._registry)
        graph = self._build_graph(audit_area, financial_data or {})
        wf_id = await engine.create(graph)

        # 注入 document_chunks
        if document_chunks:
            state = engine.get_state(wf_id)
            state.agent_results["document_chunks"] = document_chunks

        state = await engine.run(wf_id)

        risk_result = state.agent_results.get("risk", {})
        return {
            "workflow_id": wf_id,
            "status": state.status,
            "risk": risk_result.get("result", {}).get("artifact", {}).get("content", {}),
            "citations": risk_result.get("citations", []),
            "reviewer_score": state.agent_results.get("reviewer", {}).get("result", {}).get("artifact", {}).get("content", {}).get("quality_score"),
        }

    def _build_graph(self, audit_area: str, financial_data: dict) -> GraphDefinition:
        return GraphDefinition(
            nodes=[
                AgentNode(id="planner", agent_name="planner_agent", input_mapping={
                    "audit_area": audit_area, "project_context": {"financial_data": financial_data}}),
                AgentNode(id="knowledge", agent_name="knowledge_agent", input_mapping={"audit_area": audit_area}),
                AgentNode(id="risk", agent_name="risk_agent", input_mapping={
                    "audit_area": audit_area, "financial_data": financial_data}),
                AgentNode(id="evidence", agent_name="evidence_agent", input_mapping={
                    "claims_to_verify": ["Audit risks and evidence"]}),
                AgentNode(id="reviewer", agent_name="reviewer_agent", input_mapping={}),
            ],
            edges=[Edge(source="planner", target="knowledge"), Edge(source="knowledge", target="risk"),
                   Edge(source="risk", target="evidence"), Edge(source="evidence", target="reviewer")],
            entry_point="planner", end_nodes=["reviewer"],
        )
