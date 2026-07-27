"""Prompt Registry 单元测试"""

import pytest

from evaluation.prompt_registry import PromptRegistry, PromptVersion


def test_register_and_get_active():
    registry = PromptRegistry()
    v1 = PromptVersion(agent_name="risk_agent", version="v1", content="Detect risks", evaluation_score=0.85)
    registry.register(v1)
    registry.activate("risk_agent", "v1")
    active = registry.get_active("risk_agent")
    assert active is not None
    assert active.version == "v1"
    assert active.is_active


def test_prevent_overwrite():
    registry = PromptRegistry()
    v1 = PromptVersion(agent_name="risk_agent", version="v1", content="v1")
    registry.register(v1)
    with pytest.raises(ValueError, match="已存在"):
        registry.register(PromptVersion(agent_name="risk_agent", version="v1", content="duplicate"))


def test_activate_below_baseline():
    registry = PromptRegistry()
    v1 = PromptVersion(agent_name="risk_agent", version="v1", content="v1", evaluation_score=0.90)
    v2 = PromptVersion(agent_name="risk_agent", version="v2", content="v2", evaluation_score=0.80)
    registry.register(v1)
    registry.register(v2)
    registry.activate("risk_agent", "v1")
    with pytest.raises(ValueError, match="低于基线"):
        registry.activate("risk_agent", "v2")


def test_improvement_auto_calc():
    registry = PromptRegistry()
    v1 = PromptVersion(agent_name="risk_agent", version="v1", content="v1", evaluation_score=0.80)
    v2 = PromptVersion(agent_name="risk_agent", version="v2", content="v2", evaluation_score=0.90)
    registry.register(v1)
    registry.register(v2)
    assert v2.baseline_score == 0.80
    assert v2.improvement == 0.10


def test_get_history():
    registry = PromptRegistry()
    registry.register(PromptVersion(agent_name="agent_x", version="v1", content=""))
    registry.register(PromptVersion(agent_name="agent_x", version="v2", content=""))
    history = registry.get_history("agent_x")
    assert len(history) == 2


def test_compare_versions():
    registry = PromptRegistry()
    registry.register(PromptVersion(agent_name="agent_x", version="v1", content="", evaluation_score=0.70))
    registry.register(PromptVersion(agent_name="agent_x", version="v2", content="", evaluation_score=0.85))
    result = registry.compare_versions("agent_x", "v1", "v2")
    assert result["delta"] == 0.15
