"""Workflow Engine 单元测试"""

import pytest

from agents.base import AgentRegistry, BaseAgent, ToolDefinition
from domain.contracts import AgentRequest, AgentResponse
from workflows.engine import WorkflowEngine
from workflows.models import AgentNode, ApprovalDecision, GraphDefinition


class MockAgent(BaseAgent):
    name = "mock_agent"
    version = "v1"

    async def execute(self, request: AgentRequest) -> AgentResponse:  # noqa: ARG002
        return AgentResponse(
            status="SUCCESS", result={}, citations=[],
            confidence=1.0, metrics={}, next_action="",
        )

    def get_tools(self) -> list[ToolDefinition]:
        return []


@pytest.mark.asyncio
async def test_workflow_create_and_state():
    registry = AgentRegistry()
    registry.register(MockAgent)
    engine = WorkflowEngine(registry)

    graph = GraphDefinition(
        nodes=[AgentNode(id="step_1", agent_name="mock_agent")],
        edges=[],
        entry_point="step_1",
        end_nodes=["step_1"],
    )
    wf_id = await engine.create(graph)
    assert wf_id.startswith("wf_")
    state = engine.get_state(wf_id)
    assert state.status == "CREATED"


@pytest.mark.asyncio
async def test_workflow_start():
    registry = AgentRegistry()
    registry.register(MockAgent)
    engine = WorkflowEngine(registry)

    graph = GraphDefinition(
        nodes=[AgentNode(id="step_1", agent_name="mock_agent")],
        edges=[],
        entry_point="step_1",
    )
    wf_id = await engine.create(graph)
    await engine.start(wf_id)
    state = engine.get_state(wf_id)
    assert state.status == "RUNNING"


@pytest.mark.asyncio
async def test_hitl_approval_flow():
    registry = AgentRegistry()
    engine = WorkflowEngine(registry)
    graph = GraphDefinition(nodes=[], edges=[], entry_point="start")
    wf_id = await engine.create(graph)

    await engine.request_approval(wf_id, "risk_agent", "HIGH", "Revenue risk detected")
    state = engine.get_state(wf_id)
    assert state.status == "WAITING_APPROVAL"

    decision = ApprovalDecision(
        workflow_id=wf_id, reviewer_id="user_001",
        decision="APPROVED", comment="Verified",
    )
    await engine.submit_decision(decision)
    state = engine.get_state(wf_id)
    assert state.status == "RUNNING"


@pytest.mark.asyncio
async def test_workflow_not_found():
    registry = AgentRegistry()
    engine = WorkflowEngine(registry)
    with pytest.raises(KeyError):
        engine.get_state("nonexistent")
