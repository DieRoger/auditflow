"""AuditFlow — FastAPI Application Entry Point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.middleware.trace import TraceIDMiddleware
from api.middleware.rate_limit import RateLimitMiddleware
from api.routers.agents import router as agents_router
from api.routers.documents import router as documents_router
from api.routers.workflows import router as workflows_router
from api.routers.knowledge import router as knowledge_router
from api.websocket.handler import router as ws_router
from shared.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):  # noqa: ARG001
    """应用生命周期 — 启动时初始化数据库"""
    from sqlalchemy import create_engine
    from infrastructure.database.base import Base
    engine = create_engine("sqlite:///dev.db")
    Base.metadata.create_all(engine)
    logger.info("database_initialized", engine="sqlite:///dev.db")
    yield


app = FastAPI(
    title="AuditFlow API",
    version="0.1.0",
    description="AI-Native Enterprise Audit Intelligence Platform",
    lifespan=lifespan,
)

app.add_middleware(TraceIDMiddleware)
app.add_middleware(RateLimitMiddleware, default_limit=100, window_seconds=60)
# 开发环境 CORS — 允许 Vite dev server (:3000) 跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(agents_router)
app.include_router(documents_router)
app.include_router(workflows_router)
app.include_router(knowledge_router)
app.include_router(ws_router)


@app.get("/health")
async def health_check():
    logger.info("health_check_ok")
    return {"status": "ok", "version": "0.1.0"}
