"""AuditFlow — FastAPI Application Entry Point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.middleware.trace import TraceIDMiddleware
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
app.include_router(agents_router)
app.include_router(documents_router)
app.include_router(workflows_router)
app.include_router(knowledge_router)
app.include_router(ws_router)


@app.get("/health")
async def health_check():
    logger.info("health_check_ok")
    return {"status": "ok", "version": "0.1.0"}
