"""ArtifactRegistry 测试"""

import pytest

from domain.artifacts import (
    ArtifactRegistry,
    AuditArtifact,
    RiskFindingArtifact,
)


def test_create_default():
    registry = ArtifactRegistry.create_default()
    types = registry.list_types()
    assert len(types) == 4
    assert "risk_finding" in types


def test_get_type():
    registry = ArtifactRegistry.create_default()
    cls = registry.get("risk_finding")
    assert cls == RiskFindingArtifact


def test_get_unknown_type():
    registry = ArtifactRegistry.create_default()
    with pytest.raises(KeyError):
        registry.get("nonexistent")


def test_register_duplicate():
    registry = ArtifactRegistry()
    registry.register(RiskFindingArtifact)
    with pytest.raises(ValueError, match="已注册"):
        registry.register(RiskFindingArtifact)


def test_register_custom():
    class CustomArtifact(AuditArtifact):
        __artifact_type__ = "custom_type"
        artifact_type: str = "custom_type"

    registry = ArtifactRegistry()
    registry.register(CustomArtifact)
    assert "custom_type" in registry.list_types()
