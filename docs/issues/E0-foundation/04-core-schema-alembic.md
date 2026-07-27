# 0.2.1 — Core Schema + Alembic

- **Epic:** E0 — Foundation
- **Labels:** `database`, `phase-0`
- **Depends on:** 0.1.2
- **Estimate:** —

## Description
初始化核心数据库 Schema 并通过 Alembic 管理迁移。首批表：tenants、users、audit_projects、documents。`alembic upgrade head` 可运行即可。

## Acceptance Criteria
- [ ] tenants 表初始化
- [ ] users 表初始化
- [ ] audit_projects 表初始化
- [ ] documents 表初始化
- [ ] `alembic upgrade head` 可运行

## I/O Interface
N/A — infrastructure/configuration task
