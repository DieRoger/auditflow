"""RBAC + JWT 测试"""

from infrastructure.security.rbac import Role, get_permissions, has_permission


def test_admin_has_all_permissions():
    perms = get_permissions(Role.ADMIN)
    assert "user:manage" in perms
    assert "report:approve" in perms


def test_auditor_permissions():
    perms = get_permissions(Role.AUDITOR)
    assert "document:upload" in perms
    assert "user:manage" not in perms


def test_reviewer_permissions():
    perms = get_permissions(Role.REVIEWER)
    assert "report:approve" in perms
    assert "document:upload" not in perms


def test_viewer_read_only():
    perms = get_permissions(Role.VIEWER)
    assert "report:read" in perms
    assert "workflow:run" not in perms


def test_has_permission():
    assert has_permission("admin", "user:manage") is True
    assert has_permission("viewer", "report:approve") is False


def test_invalid_role():
    assert has_permission("unknown_role", "report:read") is False
    assert get_permissions("unknown_role") == []


def test_token_creation_and_decode():
    from infrastructure.security.auth import create_access_token, decode_token
    token = create_access_token(user_id="user_001", tenant_id="firm_a", role="auditor")
    assert token is not None
    payload = decode_token(token)
    assert payload.sub == "user_001"
    assert payload.role == "auditor"
    assert payload.tenant_id == "firm_a"
