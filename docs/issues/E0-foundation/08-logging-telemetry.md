# 0.3.3 — Logging & Telemetry

- **Epic:** E0 — Foundation
- **Labels:** `observability`, `phase-0`
- **Depends on:** 0.1.2
- **Estimate:** —

## Description
搭建统一日志和遥测基础设施：structlog JSON 格式输出，trace_id 贯穿全链路（Agent → Service → DB），确保不记录任何 Secrets。

## Acceptance Criteria
- [ ] structlog JSON 格式
- [ ] trace_id 贯穿全链路
- [ ] 不记录 Secrets

## I/O Interface
N/A — infrastructure/configuration task
