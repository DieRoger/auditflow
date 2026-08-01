"""Agent Execution API — FastAPI Router"""

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.base import AgentRegistry
from agents.anomaly_detection.agent import AnomalyDetectionAgent
from agents.evidence.agent import LlmEvidenceAgent
from agents.knowledge.agent import LlmKnowledgeAgent
from agents.planner.agent import LlmPlannerAgent
from agents.reviewer.agent import LlmReviewerAgent
from agents.risk.agent import LlmRiskAgent
from domain.contracts import AgentRequest
from shared.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

_registry = AgentRegistry()
_registry.register(LlmPlannerAgent)
_registry.register(LlmKnowledgeAgent)
_registry.register(LlmRiskAgent)
_registry.register(LlmEvidenceAgent)
_registry.register(LlmReviewerAgent)
_registry.register(AnomalyDetectionAgent)


class ExecuteRequest(BaseModel):
    workflow_id: str = "api_call"
    project_id: str = "api"
    task_id: str = "api"
    firm_id: str = "default"
    client_id: str = "default"
    engagement_id: str = "default"
    inputs: dict = {}
    context: dict = {}
    memory: dict = {}


class ExecuteResponse(BaseModel):
    execution_id: str
    agent_name: str
    status: str
    result: dict = {}
    confidence: float = 0.0
    next_action: str = ""
    metrics: dict = {}


@router.post("/{agent_name}/execute", response_model=ExecuteResponse)
async def execute_agent(agent_name: str, req: ExecuteRequest):
    try:
        agent_class = _registry.get(agent_name)
    except KeyError:
        raise HTTPException(404, f"Agent '{agent_name}' not found") from None

    agent = agent_class()
    areq = AgentRequest(
        workflow_id=req.workflow_id, project_id=req.project_id, task_id=req.task_id,
        firm_id=req.firm_id, client_id=req.client_id, engagement_id=req.engagement_id,
        inputs=req.inputs, context=req.context, memory=req.memory,
    )
    resp = await agent.execute(areq)
    logger.info("agent_api_executed", agent=agent_name, status=resp.status)
    return ExecuteResponse(
        execution_id=uuid.uuid4().hex[:12], agent_name=agent_name,
        status=resp.status, result=resp.result, confidence=resp.confidence,
        next_action=resp.next_action, metrics=resp.metrics,
    )


@router.get("", response_model=list[str])
async def list_agents():
    return _registry.list_agents()
