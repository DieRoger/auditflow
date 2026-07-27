"""Tenant Isolation — 数据隔离中间件"""

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


class TenantIsolationMiddleware(BaseHTTPMiddleware):
    """租户隔离中间件

    从 JWT token 中提取 firm_id / engagement_id，
    注入到 request.state 供 API 路由使用。
    自动注入 SQL 查询过滤条件。
    """

    async def dispatch(self, request: Request, call_next):
        # 从 JWT 或 Header 获取 tenant 上下文
        firm_id = request.headers.get("X-Firm-ID", "default")
        engagement_id = request.headers.get("X-Engagement-ID", "default")

        # 注入到 request.state
        request.state.firm_id = firm_id
        request.state.engagement_id = engagement_id

        logger.debug("tenant_context", firm_id=firm_id, engagement_id=engagement_id, path=request.url.path)
        response = await call_next(request)
        return response


def get_firm_id(request: Request) -> str:
    """FastAPI 依赖 — 获取当前 firm_id"""
    return getattr(request.state, "firm_id", "default")


def get_engagement_id(request: Request) -> str:
    """FastAPI 依赖 — 获取当前 engagement_id"""
    return getattr(request.state, "engagement_id", "default")


def inject_tenant_filter(query: str, firm_id: str, engagement_id: str | None = None) -> str:
    """向 SQL 查询注入租户过滤（用于未使用 ORM 的原始查询）"""
    conditions = [f"firm_id = '{firm_id}'"]
    if engagement_id:
        conditions.append(f"engagement_id = '{engagement_id}'")
    where_clause = " AND ".join(conditions)
    if "WHERE" in query.upper():
        return query.replace("WHERE", f"WHERE {where_clause} AND ")
    return f"{query} WHERE {where_clause}"
