"""Rate Limiting Middleware — 基于时间窗口的请求频率限制

使用内存计数器（生产环境应替换为 Redis）。
支持按路由配置不同限额。
"""

import time
import structlog
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """速率限制中间件 — 滑动窗口算法"""

    def __init__(self, app, default_limit: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self._default_limit = default_limit
        self._window = window_seconds
        self._windows: dict[str, list[float]] = defaultdict(list)
        # 白名单路由（不限速）
        self._whitelist = {"/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self._whitelist:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # 清理过期记录
        self._windows[client_ip] = [t for t in self._windows[client_ip] if now - t < self._window]

        if len(self._windows[client_ip]) >= self._default_limit:
            logger.warning("rate_limit_exceeded", ip=client_ip, path=request.url.path)
            raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")

        self._windows[client_ip].append(now)
        return await call_next(request)
