# Changelog

All notable changes to AuditFlow are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [SemVer](https://semver.org/spec/v2.0.0.html)

## [Unreleased] — 0.5.0 (Architecture Freeze)

### Added — Architecture Freeze v0.5

- **Assessment Layer** (`application/assessment/`):
  - `Assessment` — 统一风险评估对象（narrative risk + detected findings）
  - `AssessmentPolicy` — 8 条显式规则，Evidence dominates narrative（Rule 1-8, FROZEN ≤10）
  - `AssessmentService` — RiskFindingArtifact + FindingArtifact 融合（原 AssessmentBuilder）
- **DetectionFacade** (`application/detection/`) — 多引擎检测门面，Agent → Facade → RiskScoringEngine
- **AnomalyDetectionAgent** (`agents/anomaly_detection/`) — Rule Engine 的 Agent Adapter，无 LLM 依赖
- **ProcedurePlanningService** (`application/audit/`) — Assessment → AuditProgram（3 档抽样策略）
- **ReviewQueue** (`application/assessment/review_queue.py`) — HITL 三态：ACCEPT / DISMISS / NEED_MORE_EVIDENCE
- **RiskContext** (`application/assessment/risk_context.py`) — ISA 520: Ratio(7) + Trend(6) + Significant Accounts → Risk Agent 结构化输入
- **Signal Lifecycle** — Signal 基类 `mode` (score/info/disabled) + `precision`；registry `score_signals()`/`info_signals()`
- **FindingArtifact** (`domain/artifacts.py`) — Finding 进入 Workflow Context 的 artifact 类型

### Changed

- **Anomaly Detection 重构调优**: F1 25.4% → **60.1%**（Signal Audit: 3 信号降级 info，Profile 权重重校）
- **Workflow DAG**: Planner → Knowledge → **AnomalyDetection** → Risk → Evidence → Reviewer
  （Risk Agent 消费 upstream anomaly findings, ISA 240/315）
- **Procedure templates**: Purchase/Expense profiles 补 `procedure_template`（Mapping Coverage 33% → 100%）
- **Backend**: CORS middleware；WorkflowEngine 模块级单例（修复 create/start 状态丢失）；API 注册 AnomalyDetectionAgent
- **Benchmark 报告**: + Review Reduction (89%)、Balanced Accuracy (60.6%)、Confusion Matrix、漏斗图

### Evaluation (Benchmark v1.0 — FROZEN)

| Capability | Result | Ground Truth |
|------------|--------|--------------|
| Review Reduction | 89.0% | Abnormal_Label |
| Assessment Accuracy (Balanced) | 79.1% (60.6%) | Risk_Class |
| Evidence Reference Completeness | 100.0% | Required Fields |
| Procedure Mapping Coverage | 100.0% | Rule Mapping |
| Detection F1 | 60.1% | Abnormal_Label |
| Workflow Success Rate | 100.0% (9/9 stages) | Expected Pipeline |

- 四层 Pipeline Evaluation（`scripts/kaggle_pipeline_validation.py` + `scripts/run_pipeline_evaluation.py`）
- Error Analysis（`scripts/error_analysis.py` → `docs/engineering/ERROR_ANALYSIS.md`）
- CI Evaluation Gate（`scripts/eval_gate.py`，指标跌破 v1.0 → CI Fail）

### Frontend

- `services/api.js` — FastAPI client
- Dashboard (Live) / Trace (Live) / Evidence Search (Live) 三个真实 API 页面

### Docs

- ADR-0007 (Assessment 在 Application 层)
- Engineering: SVR_CHECKLIST / BENCHMARK_KPI / BENCHMARK_FROZEN / EVALUATION_MATRIX / EVALUATION_REPORT / KAGGLE_VALIDATION / ERROR_ANALYSIS
- Blog: beyond-f1.md（第 7 篇）
- README: Evaluation Pyramid + Benchmark Dashboard + 2 张图 + Philosophy

## [0.4.0] — 2026-07-30 (Prototype)

### Added
- Anomaly Detection 架构重构：Signal → Detection → Registry → RiskProfile → Finding 四层
- Kaggle Integration（5 数据集下载，Kaggle #1 Benchmark 初版）
- Multi-period Analysis + Confirmation Manager
- Golden Dataset Factory（50K transactions, 8 implanted risks）

### Changed
- F1 因重构暂降 64.6% → 25.4%（本版本记录，0.5.0 恢复至 60.1%）

## [0.3.0] — 2026-07 (Sprint 3-5)

### Added
- Full Integration Demo（PDF → 5 Agents → Workpaper → Audit Report）
- Evaluation & Baseline（L1/L2/L3 Metrics, Human Eval, Consistency Test）
- Production Readiness（Docker Compose, FastAPI 4 routers, WebSocket, CI/CD, Audit Log, Prompt Injection Defense）
- Journal Entry Testing + Materiality Engine（ISA 320）

## [0.2.0] — 2026-06 (Sprint 1-2)

### Added
- 5 个 Real LLM Agents（DeepSeek）+ Workflow Engine（DAG + HITL + Trace + Checkpoint + Retry + TokenBudget）
- Document Pipeline（PyMuPDF + RapidOCR + Semantic Chunking + PGVector + Hybrid Search）
- Phase A-E Revenue Cutoff 垂直切片（Import → Sampling → Evidence Graph → Misstatement → Completion）

## [0.1.0] — 2026-05 (Foundation)

### Added
- Project scaffolding, DDD + Clean Architecture baseline
- Canonical Audit Schema（Transaction/Document/Party）RFC 冻结
- Docker Compose（PostgreSQL/PGVector, MinIO, Redis）
- CI/CD pipeline
