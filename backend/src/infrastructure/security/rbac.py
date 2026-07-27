"""RBAC 权限模型 — 角色枚举 + 权限矩阵"""

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    AUDITOR = "auditor"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


# 权限枚举
PERM_USER_MANAGE = "user:manage"
PERM_PROJECT_CREATE = "project:create"
PERM_DOCUMENT_UPLOAD = "document:upload"
PERM_WORKFLOW_RUN = "workflow:run"
PERM_AGENT_OUTPUT_READ = "agent_output:read"
PERM_REPORT_GENERATE = "report:generate"
PERM_REPORT_APPROVE = "report:approve"
PERM_REPORT_READ = "report:read"
PERM_APPROVAL_SUBMIT = "approval:submit"

# 权限矩阵：Role → [Permissions]
RBAC_MATRIX: dict[Role, list[str]] = {
    Role.ADMIN: [
        PERM_USER_MANAGE, PERM_PROJECT_CREATE, PERM_DOCUMENT_UPLOAD,
        PERM_WORKFLOW_RUN, PERM_AGENT_OUTPUT_READ, PERM_REPORT_GENERATE,
        PERM_REPORT_APPROVE, PERM_REPORT_READ, PERM_APPROVAL_SUBMIT,
    ],
    Role.AUDITOR: [
        PERM_PROJECT_CREATE, PERM_DOCUMENT_UPLOAD, PERM_WORKFLOW_RUN,
        PERM_AGENT_OUTPUT_READ, PERM_REPORT_GENERATE, PERM_REPORT_READ,
    ],
    Role.REVIEWER: [
        PERM_AGENT_OUTPUT_READ, PERM_REPORT_READ, PERM_REPORT_APPROVE,
        PERM_APPROVAL_SUBMIT,
    ],
    Role.VIEWER: [
        PERM_REPORT_READ, PERM_AGENT_OUTPUT_READ,
    ],
}


def has_permission(role: Role | str, permission: str) -> bool:
    """检查角色是否拥有指定权限"""
    if isinstance(role, str):
        try:
            role = Role(role)
        except ValueError:
            return False
    return permission in RBAC_MATRIX.get(role, [])


def get_permissions(role: Role | str) -> list[str]:
    """获取角色的所有权限"""
    if isinstance(role, str):
        try:
            role = Role(role)
        except ValueError:
            return []
    return RBAC_MATRIX.get(role, []).copy()
