"""Workflow Engine — Agent 编排 + HITL 状态机 + Trace/Checkpoint"""

import uuid
from datetime import datetime

from agents.base import AgentRegistry
from domain.contracts import AgentRequest, AgentResponse
from domain.events import (
    WorkflowEvent,
    event_agent_completed,
    event_agent_failed,
    event_agent_started,
    event_approval_required,
    event_approval_submitted,
    event_workflow_completed,
    event_workflow_failed,
    event_workflow_paused,
    event_workflow_resumed,
)

from .models import AgentNode, ApprovalDecision, GraphDefinition, WorkflowState
from .trace import Checkpoint, CheckpointStore, ExecutionTrace, InMemoryCheckpointStore, InMemoryTraceStore, TraceStore


class WorkflowEngine:
    """Workflow 编排器

    负责 Agent 执行调度、状态管理、HITL 中断恢复、重试与超时。
    不包含业务逻辑 — 仅编排。
    """

    def __init__(
        self,
        agent_registry: AgentRegistry,
        trace_store: TraceStore | None = None,
        checkpoint_store: CheckpointStore | None = None,
    ):
        self._registry = agent_registry
        self._trace_store = trace_store or InMemoryTraceStore()
        self._checkpoint_store = checkpoint_store or InMemoryCheckpointStore()
        self._states: dict[str, WorkflowState] = {}
        self._graphs: dict[str, GraphDefinition] = {}
        self._event_listeners: list[callable] = []
        self._step_counter: dict[str, int] = {}

    def on_event(self, listener: callable) -> None:
        """注册事件监听器（用于 WebSocket 推送）"""
        self._event_listeners.append(listener)

    async def _emit(self, event: WorkflowEvent) -> None:
        """发布事件到所有监听器"""
        for listener in self._event_listeners:
            await listener(event)

    async def _record_trace(
        self, workflow_id: str, agent_name: str,
        event_type: str, input_data: dict | None = None,
        output: dict | None = None, error: str | None = None,
        duration_ms: int | None = None,
    ) -> None:
        self._step_counter[workflow_id] = self._step_counter.get(workflow_id, 0) + 1
        trace = ExecutionTrace(
            workflow_id=workflow_id,
            agent_name=agent_name,
            step=self._step_counter[workflow_id],
            event_type=event_type,
            input=input_data or {},
            output=output,
            duration_ms=duration_ms,
            error=error,
        )
        await self._trace_store.append(trace)

    async def _save_checkpoint(self, workflow_id: str, agent_name: str, state: WorkflowState) -> None:
        checkpoint = Checkpoint(
            workflow_id=workflow_id,
            agent_name=agent_name,
            state_snapshot=state.model_dump(),
        )
        await self._checkpoint_store.save(checkpoint)

    async def create(self, graph: GraphDefinition) -> str:
        """创建 Workflow 实例，返回 workflow_id"""
        workflow_id = f"wf_{uuid.uuid4().hex[:12]}"
        self._graphs[workflow_id] = graph
        self._states[workflow_id] = WorkflowState(
            workflow_id=workflow_id,
            status="CREATED",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )
        return workflow_id

    async def start(self, workflow_id: str) -> None:
        """启动 Workflow — 从 entry_point 开始执行"""
        state = self._get_state(workflow_id)
        graph = self._graphs[workflow_id]
        state.status = "RUNNING"
        state.current_node = graph.entry_point
        state.updated_at = datetime.now().isoformat()

    async def _execute_node(self, workflow_id: str, node: AgentNode) -> None:
        """执行单个 Agent 节点（含重试逻辑）"""
        state = self._get_state(workflow_id)
        state.current_node = node.id
        max_retries = (node.retry_policy or {}).get("max_retries", 3)

        for attempt in range(1, max_retries + 1):
            start_time = datetime.now()

            await self._record_trace(
                workflow_id, node.agent_name, "AGENT_START",
                input_data={"node_id": node.id, "attempt": attempt},
            )
            await self._emit(event_agent_started(
                uuid.uuid4().hex, workflow_id, node.agent_name, f"Executing {node.id} (attempt {attempt})"
            ))

            try:
                # 通过 AgentRegistry 获取并实例化 Agent
                agent_class = self._registry.get(node.agent_name)
                agent = agent_class()

                # 组装 AgentRequest：上游所有结果作为 context
                context = dict(state.agent_results)
                request = AgentRequest(
                    workflow_id=workflow_id,
                    project_id=state.project_id or "default",
                    task_id=f"{node.id}_task",
                    firm_id="default",
                    client_id="default",
                    engagement_id="default",
                    context=context,
                    inputs=node.input_mapping,
                    memory={},
                )

                response = await agent.execute(request)
                duration = int((datetime.now() - start_time).total_seconds() * 1000)
                state.agent_results[node.id] = response.model_dump()
                # 将 result 内容合并到顶层，便于下游 Agent 直接访问 artifact
                if isinstance(response.result, dict):
                    for k, v in response.result.items():
                        if k not in state.agent_results[node.id]:
                            state.agent_results[node.id][k] = v
                state.retry_count = attempt - 1

                await self._record_trace(
                    workflow_id, node.agent_name, "AGENT_COMPLETE",
                    output=response.model_dump(), duration_ms=duration,
                )
                await self._save_checkpoint(workflow_id, node.agent_name, state)
                await self._emit(event_agent_completed(
                    uuid.uuid4().hex, workflow_id, node.agent_name, duration,
                    response.metrics.get("tokens", 0), response.confidence
                ))
                return  # 成功，跳出重试循环

            except Exception as exc:
                duration = int((datetime.now() - start_time).total_seconds() * 1000)
                state.retry_count = attempt
                await self._record_trace(
                    workflow_id, node.agent_name, "AGENT_FAIL",
                    error=str(exc), duration_ms=duration,
                )
                await self._emit(event_agent_failed(
                    uuid.uuid4().hex, workflow_id, node.agent_name,
                    type(exc).__name__, attempt, attempt < max_retries
                ))
                if attempt >= max_retries:
                    state.status = "FAILED"
                    state.error = str(exc)
                    raise
                state.status = "RETRYING"

    # ── 图遍历与批量执行 ──────────────────────────────────────

    def _topological_order(self, graph: GraphDefinition) -> list[AgentNode]:
        """返回按拓扑排序的节点列表（线性链/DAG）"""
        node_map: dict[str, AgentNode] = {n.id: n for n in graph.nodes}
        in_degree: dict[str, int] = {n.id: 0 for n in graph.nodes}
        for edge in graph.edges:
            if edge.target in in_degree:
                in_degree[edge.target] += 1

        # Kahn 算法
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        # 确保 entry_point 在最前面
        if graph.entry_point in node_map and graph.entry_point not in queue:
            queue.insert(0, graph.entry_point)

        order: list[AgentNode] = []
        while queue:
            nid = queue.pop(0)
            if nid in node_map:
                order.append(node_map[nid])
            for edge in graph.edges:
                if edge.source == nid and edge.target in in_degree:
                    in_degree[edge.target] -= 1
                    if in_degree[edge.target] == 0:
                        queue.append(edge.target)

        return order

    async def run(self, workflow_id: str) -> WorkflowState:
        """执行完整 Workflow — 按拓扑顺序遍历所有节点

        每个节点通过 AgentRegistry 查找 Agent、注入上游 context 并执行。
        """
        state = self._get_state(workflow_id)
        graph = self._graphs[workflow_id]
        state.status = "RUNNING"

        node_order = self._topological_order(graph)
        for node in node_order:
            state.current_node = node.id
            state.updated_at = datetime.now().isoformat()
            try:
                await self._execute_node(workflow_id, node)
            except Exception:
                # _execute_node 已处理重试逻辑；重试耗尽后在此捕获
                if state.status == "FAILED":
                    return state
                raise

        await self.complete(workflow_id)
        state.updated_at = datetime.now().isoformat()
        return state

    async def pause(self, workflow_id: str) -> None:
        """暂停 Workflow"""
        state = self._get_state(workflow_id)
        state.status = "WAITING_APPROVAL"
        await self._emit(event_workflow_paused(uuid.uuid4().hex, workflow_id, "user_request"))

    async def resume(self, workflow_id: str) -> None:
        """恢复 Workflow"""
        state = self._get_state(workflow_id)
        state.status = "RUNNING"
        await self._emit(event_workflow_resumed(uuid.uuid4().hex, workflow_id))

    async def request_approval(self, workflow_id: str, agent_name: str, severity: str, summary: str) -> None:
        """请求人工审批 — 进入 WAITING_APPROVAL 状态"""
        state = self._get_state(workflow_id)
        state.status = "WAITING_APPROVAL"
        await self._emit(event_approval_required(
            uuid.uuid4().hex, workflow_id, agent_name, severity, summary
        ))

    async def submit_decision(self, decision: ApprovalDecision) -> None:
        """提交审批决策"""
        state = self._get_state(workflow_id := decision.workflow_id)
        await self._emit(event_approval_submitted(
            uuid.uuid4().hex, workflow_id, decision.decision, decision.comment
        ))
        if decision.decision == "APPROVED":
            state.status = "RUNNING"
        elif decision.decision == "REJECTED":
            state.status = "RUNNING"
            state.agent_results = {}
        elif decision.decision == "MODIFY":
            state.status = "RUNNING"

    async def complete(self, workflow_id: str) -> None:
        """标记 Workflow 完成"""
        state = self._get_state(workflow_id)
        state.status = "COMPLETED"
        await self._emit(event_workflow_completed(
            uuid.uuid4().hex, workflow_id, 0, 0, 0.0
        ))

    async def fail(self, workflow_id: str, error: str, recoverable: bool = False) -> None:
        """标记 Workflow 失败"""
        state = self._get_state(workflow_id)
        state.status = "FAILED" if not recoverable else "RETRYING"
        state.error = error
        await self._emit(event_workflow_failed(
            uuid.uuid4().hex, workflow_id, error, recoverable
        ))

    def get_state(self, workflow_id: str) -> WorkflowState:
        """获取 Workflow 状态"""
        return self._get_state(workflow_id)

    async def get_traces(self, workflow_id: str) -> list[ExecutionTrace]:
        """获取 Workflow 的 Trace"""
        return await self._trace_store.query(workflow_id)

    async def get_replay(self, workflow_id: str) -> list[dict]:
        """获取 Replay 报告"""
        return await self._trace_store.replay(workflow_id)

    def _get_state(self, workflow_id: str) -> WorkflowState:
        state = self._states.get(workflow_id)
        if state is None:
            raise KeyError(f"Workflow '{workflow_id}' 不存在")
        return state
