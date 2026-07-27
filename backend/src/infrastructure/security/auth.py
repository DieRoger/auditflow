# ruff: noqa: B008
"""JWT 认证 — Token 生成/验证 + FastAPI 依赖注入"""

import os
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

try:
    from jose import JWTError, jwt
except ImportError:
    jwt = None  # type: ignore

from .rbac import has_permission

SECRET_KEY = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

security = HTTPBearer(auto_error=False)


class TokenPayload(BaseModel):
    sub: str  # user_id
    tenant_id: str = ""
    role: str = "viewer"
    exp: datetime | None = None


def create_access_token(user_id: str, tenant_id: str = "", role: str = "viewer") -> str:
    """创建 JWT access token"""
    if jwt is None:
        raise ImportError("python-jose is required for JWT support. Install: pip install python-jose[cryptography]")
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user_id, "tenant_id": tenant_id, "role": role, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> TokenPayload:
    """解码 JWT token"""
    if jwt is None:
        raise ImportError("python-jose is required")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return TokenPayload(
            sub=payload.get("sub", ""),
            tenant_id=payload.get("tenant_id", ""),
            role=payload.get("role", "viewer"),
            exp=datetime.fromtimestamp(payload.get("exp", 0)) if payload.get("exp") else None,
        )
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> TokenPayload | None:
    """FastAPI 依赖 — 获取当前用户（可选 — 未认证时返回 None）"""
    if credentials is None:
        return None
    return decode_token(credentials.credentials)


async def require_role(required_role: str):
    """FastAPI 依赖工厂 — 要求最低角色"""
    async def role_checker(current_user: TokenPayload | None = Depends(get_current_user)) -> TokenPayload:
        if current_user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        roles_order = ["viewer", "auditor", "reviewer", "admin"]
        if roles_order.index(current_user.role) < roles_order.index(required_role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Requires role: {required_role}")
        return current_user
    return role_checker


async def require_permission(permission: str):
    """FastAPI 依赖工厂 — 要求指定权限"""
    async def permission_checker(current_user: TokenPayload | None = Depends(get_current_user)) -> TokenPayload:
        if current_user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        if not has_permission(current_user.role, permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing permission: {permission}")
        return current_user
    return permission_checker
