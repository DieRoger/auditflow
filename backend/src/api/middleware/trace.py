"""FastAPI Middleware — trace_id 注入 + 请求日志."""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request

from shared.logging import get_logger
from shared.telemetry import set_trace_id


class TraceIDMiddleware(BaseHTTPMiddleware):
    """为每个请求注入 trace_id"""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        trace_id = request.headers.get("X-Trace-ID") or set_trace_id()
        set_trace_id(trace_id)

        logger = get_logger("http")
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            trace_id=trace_id,
        )

        try:
            response = await call_next(request)
            response.headers["X-Trace-ID"] = trace_id
            logger.info(
                "request_completed",
                status_code=response.status_code,
                trace_id=trace_id,
            )
            return response
        except Exception as exc:
            logger.error(
                "request_failed",
                error=str(exc),
                trace_id=trace_id,
            )
            raise
