"""ToolRegistry 权限测试"""

import pytest

from agents.base import ToolDefinition, ToolRegistry


def test_default_tools_exist():
    registry = ToolRegistry.create_default()
    tools = registry.list_tools()
    assert len(tools) == 9
    assert "ontology_query" in tools
    assert "calculator" in tools


def test_planner_permissions():
    registry = ToolRegistry.create_default()
    allowed = registry.list_by_agent("planner_agent")
    assert len(allowed) == 2
    assert registry.is_allowed("planner_agent", "ontology_query")
    assert not registry.is_allowed("planner_agent", "evidence_search")


def test_risk_agent_permissions():
    registry = ToolRegistry.create_default()
    allowed = registry.list_by_agent("risk_agent")
    assert len(allowed) == 4
    names = [t.name for t in allowed]
    assert "evidence_search" in names and "calculator" in names


def test_permission_denied():
    registry = ToolRegistry.create_default()
    assert not registry.is_allowed("planner_agent", "grounding_checker")


@pytest.mark.asyncio
async def test_execute_unauthorized_tool():
    registry = ToolRegistry.create_default()
    with pytest.raises(PermissionError):
        await registry.execute("planner_agent", "evidence_search", {})


def test_register_custom_tool():
    registry = ToolRegistry.create_default()
    tool = ToolDefinition(name="custom_test", description="Test tool")
    registry.register_tool(tool)
    assert registry.get_tool("custom_test").name == "custom_test"


def test_custom_permissions():
    registry = ToolRegistry.create_default()
    registry.set_agent_permissions("custom_agent", ["calculator"])
    assert registry.is_allowed("custom_agent", "calculator")
    assert not registry.is_allowed("custom_agent", "ontology_query")
