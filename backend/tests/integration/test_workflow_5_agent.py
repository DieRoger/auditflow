"""Workflow Engine 5 Agent 集成测试

验证:
  1. Agent 通过 AgentRegistry 注册和查找（不直接 new）
  2. 按拓扑顺序执行节点
  3. Context 在节点间正确传递
  4. Event + Trace 自动记录
  5. HITL 暂停/恢复
  6. 错误处理
"""

from dataclasses import dataclass

import pytest

from agents.base import AgentRegistry, BaseAgent, ToolDefinition
from domain.contracts import AgentRequest, AgentResponse, Citation
from workflows.engine import WorkflowEngine
from workflows.models import AgentNode, Edge, GraphDefinition


# ── 可追踪的 Mock Agent ─────────────────────────────────────

@dataclass
class AgentCallRecord:
    agent_name: str
    inputs: dict
    context_keys: list[str]


class TrackedMockAgent(BaseAgent):
    """Mock Agent — 记录每次调用，验证 context 传递"""

    name: str = "tracked_mock"
    version: str = "v1"
    _calls: list[AgentCallRecord] = []
    _return_result: dict = {"mock": True}

    @classmethod
    def reset(cls) -> None:
        cls._calls = []

    async def execute(self, request: AgentRequest) -> AgentResponse:
        self._calls.append(AgentCallRecord(
            agent_name=self.name,
            inputs=request.inputs,
            context_keys=list(request.context.keys()),
        ))
        return AgentResponse(
            status="SUCCESS",
            result={"artifact": {"artifact_type": "test", "content": self._return_result}},
            citations=[Citation(claim="test", document_id="test_doc", excerpt="test excerpt", confidence=0.9)],
            confidence=0.95,
            metrics={"tokens": 100, "model": "mock"},
            next_action="NEXT",
        )

    def get_tools(self) -> list[ToolDefinition]:
        return []


# ── 专用 Mock Agent 子类（AgentRegistry 按类名注册） ──────

class MockPlanner(TrackedMockAgent):
    name = "planner_agent"

class MockKnowledge(TrackedMockAgent):
    name = "knowledge_agent"

class MockRisk(TrackedMockAgent):
    name = "risk_agent"

class MockEvidence(TrackedMockAgent):
    name = "evidence_agent"

class MockReviewer(TrackedMockAgent):
    name = "reviewer_agent"


# ── Fixtures ─────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_calls():
    TrackedMockAgent.reset()


@pytest.fixture
def registry():
    r = AgentRegistry()
    r.register(MockPlanner)
    r.register(MockKnowledge)
    r.register(MockRisk)
    r.register(MockEvidence)
    r.register(MockReviewer)
    return r


@pytest.fixture
def five_agent_graph():
    return GraphDefinition(
        nodes=[
            AgentNode(id="planner", agent_name="planner_agent",
                      input_mapping={"audit_area": "Revenue Recognition"}),
            AgentNode(id="knowledge", agent_name="knowledge_agent",
                      input_mapping={"audit_area": "Revenue Recognition"}),
            AgentNode(id="risk", agent_name="risk_agent",
                      input_mapping={"audit_area": "Revenue Recognition",
                                     "financial_data": {"revenue_growth": "45%"}}),
            AgentNode(id="evidence", agent_name="evidence_agent",
                      input_mapping={"claims_to_verify": ["Revenue growth 45%"]}),
            AgentNode(id="reviewer", agent_name="reviewer_agent",
                      input_mapping={}),
        ],
        edges=[
            Edge(source="planner", target="knowledge"),
            Edge(source="knowledge", target="risk"),
            Edge(source="risk", target="evidence"),
            Edge(source="evidence", target="reviewer"),
        ],
        entry_point="planner",
        end_nodes=["reviewer"],
    )


# ── 测试 ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_agents_registered_via_registry(registry, five_agent_graph):
    """Agent 通过 AgentRegistry 注册和查找（不直接 new）"""
    engine = WorkflowEngine(registry)
    wf_id = await engine.create(five_agent_graph)
    state = await engine.run(wf_id)

    assert state.status == "COMPLETED"
    assert len(TrackedMockAgent._calls) == 5


@pytest.mark.asyncio
async def test_agent_inputs_passed_correctly(registry):
    """每个 Agent 收到正确的 inputs（来自 input_mapping）"""
    graph = GraphDefinition(
        nodes=[AgentNode(id="planner", agent_name="planner_agent",
                         input_mapping={"audit_area": "Revenue Recognition",
                                        "project_context": {"company": "TestCo"}})],
        edges=[], entry_point="planner", end_nodes=["planner"],
    )
    engine = WorkflowEngine(registry)
    wf_id = await engine.create(graph)
    await engine.run(wf_id)

    assert len(TrackedMockAgent._calls) == 1
    call = TrackedMockAgent._calls[0]
    assert call.inputs["audit_area"] == "Revenue Recognition"
    assert call.inputs["project_context"] == {"company": "TestCo"}


@pytest.mark.asyncio
async def test_context_passed_between_nodes(registry, five_agent_graph):
    """Context 在节点间正确传递 — 上游结果出现在下游 context 中"""
    engine = WorkflowEngine(registry)
    wf_id = await engine.create(five_agent_graph)
    await engine.run(wf_id)

    # 第 5 个节点 (reviewer) 应该能看到前面 4 个节点的结果
    reviewer_call = TrackedMockAgent._calls[4]
    assert "planner" in reviewer_call.context_keys
    assert "knowledge" in reviewer_call.context_keys
    assert "risk" in reviewer_call.context_keys
    assert "evidence" in reviewer_call.context_keys


@pytest.mark.asyncio
async def test_topological_order(registry, five_agent_graph):
    """节点按拓扑顺序执行"""
    engine = WorkflowEngine(registry)
    wf_id = await engine.create(five_agent_graph)
    await engine.run(wf_id)

    agent_names = [c.agent_name for c in TrackedMockAgent._calls]
    assert agent_names == ["planner_agent", "knowledge_agent", "risk_agent", "evidence_agent", "reviewer_agent"]


@pytest.mark.asyncio
async def test_trace_records_all_steps(registry, five_agent_graph):
    """每个 Agent 调用都产生 Trace 记录"""
    engine = WorkflowEngine(registry)
    wf_id = await engine.create(five_agent_graph)
    await engine.run(wf_id)

    traces = await engine.get_traces(wf_id)
    # 每个 Agent 有 AGENT_START + AGENT_COMPLETE = 10 条 trace
    assert len(traces) == 10
    event_types = [t.event_type for t in traces]
    assert event_types.count("AGENT_START") == 5
    assert event_types.count("AGENT_COMPLETE") == 5


@pytest.mark.asyncio
async def test_events_emitted(registry, five_agent_graph):
    """事件总线产生 agent_started / agent_completed / workflow_completed"""
    events: list[str] = []

    async def collect(event):
        events.append(event.event_type.value)

    engine = WorkflowEngine(registry)
    engine.on_event(collect)
    wf_id = await engine.create(five_agent_graph)
    await engine.run(wf_id)

    assert events.count("agent_started") == 5
    assert events.count("agent_completed") == 5
    assert "workflow_completed" in events


@pytest.mark.asyncio
async def test_state_transitions(registry, five_agent_graph):
    """Workflow 状态正确过渡: CREATED → RUNNING → COMPLETED"""
    engine = WorkflowEngine(registry)
    wf_id = await engine.create(five_agent_graph)

    assert engine.get_state(wf_id).status == "CREATED"

    state = await engine.run(wf_id)
    assert state.status == "COMPLETED"


@pytest.mark.asyncio
async def test_hitl_pause_resume(registry):
    """HITL: 请求审批 → 暂停 → 提交决策 → 恢复"""
    engine = WorkflowEngine(registry)
    graph = GraphDefinition(
        nodes=[AgentNode(id="n1", agent_name="planner_agent", input_mapping={})],
        edges=[], entry_point="n1", end_nodes=["n1"],
    )
    wf_id = await engine.create(graph)

    await engine.request_approval(wf_id, "risk_agent", "HIGH", "Test risk")
    assert engine.get_state(wf_id).status == "WAITING_APPROVAL"

    from workflows.models import ApprovalDecision
    decision = ApprovalDecision(
        workflow_id=wf_id, reviewer_id="user_001",
        decision="APPROVED", comment="ok",
    )
    await engine.submit_decision(decision)
    assert engine.get_state(wf_id).status == "RUNNING"


@pytest.mark.asyncio
async def test_agent_failure_stops_pipeline():
    """Agent 失败时管线终止并记录错误"""
    class FailingAgent(TrackedMockAgent):
        name = "failing_agent"

        async def execute(self, request: AgentRequest) -> AgentResponse:
            raise RuntimeError("simulated agent failure")

    r = AgentRegistry()
    r.register(FailingAgent)
    engine = WorkflowEngine(r)
    graph = GraphDefinition(
        nodes=[AgentNode(id="n1", agent_name="failing_agent", input_mapping={})],
        edges=[], entry_point="n1",
    )
    wf_id = await engine.create(graph)

    # run() 内部重试 3 次后标记 FAILED 并返回，不抛出异常
    state = await engine.run(wf_id)

    assert state.status == "FAILED"
    assert state.retry_count == 3

    traces = await engine.get_traces(wf_id)
    assert any(t.event_type == "AGENT_FAIL" for t in traces)


@pytest.mark.asyncio
async def test_agent_registry_rejects_duplicate(registry):
    """重复注册同名 Agent 抛出 ValueError"""
    with pytest.raises(ValueError, match="已注册"):
        registry.register(MockPlanner)
