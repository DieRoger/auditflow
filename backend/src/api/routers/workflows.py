"""Workflow API Router — 创建/查询/控制 Workflow"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from agents.base import AgentRegistry
from workflows.engine import WorkflowEngine
from workflows.models import AgentNode, ApprovalDecision, Edge, GraphDefinition

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])


class WorkflowCreateRequest(BaseModel):
    project_id: str
    audit_area: str = "Revenue Recognition"
    financial_data: dict = {}
    firm_id: str = "default"


class ApprovalSubmitRequest(BaseModel):
    workflow_id: str
    reviewer_id: str
    decision: str  # APPROVED | REJECTED | MODIFY
    comment: str = ""


_ENGINE: WorkflowEngine | None = None


def _get_engine() -> WorkflowEngine:
    """返回单例 WorkflowEngine — 状态在进程内持久（create/start/trace 共享）"""
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE

    registry = AgentRegistry()
    from agents.planner.agent import LlmPlannerAgent
    from agents.knowledge.agent import LlmKnowledgeAgent
    from agents.risk.agent import LlmRiskAgent
    from agents.evidence.agent import LlmEvidenceAgent
    from agents.reviewer.agent import LlmReviewerAgent
    from agents.anomaly_detection.agent import AnomalyDetectionAgent
    registry.register(LlmPlannerAgent)
    registry.register(LlmKnowledgeAgent)
    registry.register(LlmRiskAgent)
    registry.register(LlmEvidenceAgent)
    registry.register(LlmReviewerAgent)
    registry.register(AnomalyDetectionAgent)
    _ENGINE = WorkflowEngine(registry)
    return _ENGINE


def _build_graph(audit_area: str, financial_data: dict) -> GraphDefinition:
    return GraphDefinition(
        nodes=[
            AgentNode(id="planner", agent_name="planner_agent", input_mapping={
                "audit_area": audit_area, "project_context": {"financial_data": str(financial_data)[:500]}}),
            AgentNode(id="knowledge", agent_name="knowledge_agent", input_mapping={"audit_area": audit_area}),
            AgentNode(id="anomaly_detection", agent_name="anomaly_detection_agent",
                      input_mapping={"transactions": financial_data.get("transactions", [])}),
            AgentNode(id="risk", agent_name="risk_agent", input_mapping={
                "audit_area": audit_area, "financial_data": financial_data}),
            AgentNode(id="evidence", agent_name="evidence_agent", input_mapping={"claims_to_verify": ["Audit risks"]}),
            AgentNode(id="reviewer", agent_name="reviewer_agent", input_mapping={}),
        ],
        edges=[Edge(source="planner", target="knowledge"), Edge(source="knowledge", target="anomaly_detection"),
               Edge(source="anomaly_detection", target="risk"), Edge(source="risk", target="evidence"),
               Edge(source="evidence", target="reviewer")],
        entry_point="planner", end_nodes=["reviewer"],
    )


@router.post("", status_code=201)
async def create_workflow(req: WorkflowCreateRequest):
    """创建并启动审计 Workflow"""
    engine = _get_engine()
    graph = _build_graph(req.audit_area, req.financial_data)
    wf_id = await engine.create(graph)
    state = engine.get_state(wf_id)
    return {"workflow_id": wf_id, "status": state.status, "project_id": req.project_id}


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str):
    """查询 Workflow 状态和结果"""
    engine = _get_engine()
    try:
        state = engine.get_state(workflow_id)
    except KeyError:
        raise HTTPException(404, "Workflow not found")

    return {
        "workflow_id": workflow_id,
        "status": state.status,
        "current_node": state.current_node,
        "error": state.error,
        "agent_results": {k: {"status": v.get("status"), "result_summary": str(v.get("result", {}))[:200]}
                          for k, v in state.agent_results.items()},
    }


@router.post("/{workflow_id}/start")
async def start_workflow(workflow_id: str):
    """启动指定的 Workflow"""
    engine = _get_engine()
    try:
        state = await engine.run(workflow_id)
        return {"workflow_id": workflow_id, "status": state.status, "error": state.error}
    except KeyError:
        raise HTTPException(404, "Workflow not found")


@router.get("/{workflow_id}/trace")
async def get_trace(workflow_id: str):
    """获取 Workflow 执行轨迹"""
    engine = _get_engine()
    traces = await engine.get_traces(workflow_id)
    return {
        "workflow_id": workflow_id,
        "traces": [{"agent": t.agent_name, "event": t.event_type, "step": t.step,
                     "duration_ms": t.duration_ms, "error": t.error} for t in traces],
    }


@router.post("/approvals")
async def submit_approval(decision: ApprovalSubmitRequest):
    """提交人工审批决策"""
    engine = _get_engine()
    try:
        dec = ApprovalDecision(
            workflow_id=decision.workflow_id, reviewer_id=decision.reviewer_id,
            decision=decision.decision, comment=decision.comment,
        )
        await engine.submit_decision(dec)
        state = engine.get_state(decision.workflow_id)
        return {"workflow_id": decision.workflow_id, "status": state.status, "decision": decision.decision}
    except KeyError:
        raise HTTPException(404, "Workflow not found")
