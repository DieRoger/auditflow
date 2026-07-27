"""Execution Trace + Checkpoint 单元测试"""

import pytest

from workflows.trace import (
    Checkpoint,
    ExecutionTrace,
    InMemoryCheckpointStore,
    InMemoryTraceStore,
)


@pytest.mark.asyncio
async def test_trace_append_and_query():
    store = InMemoryTraceStore()
    trace = ExecutionTrace(
        workflow_id="wf_001", agent_name="risk_agent",
        event_type="AGENT_START", input={"query": "revenue risk"},
    )
    await store.append(trace)
    traces = await store.query("wf_001")
    assert len(traces) == 1
    assert traces[0].agent_name == "risk_agent"


@pytest.mark.asyncio
async def test_trace_replay():
    store = InMemoryTraceStore()
    await store.append(ExecutionTrace(workflow_id="wf_001", agent_name="planner", event_type="AGENT_START"))
    await store.append(ExecutionTrace(
        workflow_id="wf_001", agent_name="planner", event_type="AGENT_COMPLETE", duration_ms=1200,
    ))
    report = await store.replay("wf_001")
    assert len(report) == 2
    assert report[0]["agent"] == "planner"


@pytest.mark.asyncio
async def test_checkpoint_save_and_load():
    store = InMemoryCheckpointStore()
    cp = Checkpoint(workflow_id="wf_001", agent_name="risk_agent", state_snapshot={"status": "RUNNING"})
    await store.save(cp)

    loaded = await store.load(cp.checkpoint_id)
    assert loaded is not None
    assert loaded.state_snapshot["status"] == "RUNNING"


@pytest.mark.asyncio
async def test_checkpoint_load_latest():
    store = InMemoryCheckpointStore()
    cp1 = Checkpoint(workflow_id="wf_001", agent_name="planner", state_snapshot={})
    cp2 = Checkpoint(workflow_id="wf_001", agent_name="risk_agent", state_snapshot={})
    await store.save(cp1)
    await store.save(cp2)
    latest = await store.load_latest("wf_001")
    assert latest is not None
    assert latest.agent_name == "risk_agent"


@pytest.mark.asyncio
async def test_checkpoint_not_found():
    store = InMemoryCheckpointStore()
    result = await store.load("nonexistent")
    assert result is None
