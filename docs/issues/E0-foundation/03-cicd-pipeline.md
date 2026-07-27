# 0.1.3 — CI/CD Pipeline

- **Epic:** E0 — Foundation
- **Labels:** `infra`, `phase-0`
- **Depends on:** 0.1.1
- **Estimate:** —

## Description
搭建 CI/CD Pipeline：PR 触发 lint + test + type-check；main 分支合并后触发 docker build；任一步骤失败则阻止 merge。

## Acceptance Criteria
- [ ] PR → lint + test + type-check
- [ ] main merge → docker build
- [ ] 失败阻止 merge

## I/O Interface
N/A — infrastructure/configuration task
