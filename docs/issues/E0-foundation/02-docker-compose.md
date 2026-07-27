# 0.1.2 — Docker Compose 开发环境

- **Epic:** E0 — Foundation
- **Labels:** `infra`, `phase-0`
- **Depends on:** 0.1.1
- **Estimate:** —

## Description
使用 Docker Compose 搭建完整的本地开发环境，包含 PostgreSQL + PGVector、Redis、MinIO、FastAPI（hot-reload）和 Celery Worker，一键 `docker compose up -d` 全部服务 healthy。

## Acceptance Criteria
- [ ] PG + PGVector
- [ ] Redis
- [ ] MinIO
- [ ] FastAPI（hot-reload）
- [ ] Celery Worker
- [ ] `docker compose up -d` 全部 healthy

## I/O Interface
N/A — infrastructure/configuration task
