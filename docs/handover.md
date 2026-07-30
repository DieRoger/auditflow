# AuditFlow — Project Handover

**文档版本:** v1.0
**生成日期:** 2026-07-30
**交接人:** Tech Lead
**接收人:** 新 Codex 对话

> 本文档是新对话的唯一上下文。阅读完本文档后，你应能理解项目的完整架构、当前状态、所有重要决策、已知问题，并直接开始下一步开发。

---

# PROJECT_BRIEF

## 一句话介绍

AuditFlow 是一个 **Evidence-Driven AI Audit Execution Platform** — 从 Excel/PDF 数据导入到 ISA 合规审计意见的全自动管线。

## 项目目标

构建一个 AI-native 的审计执行系统，证明 AI 可以完成完整的审计生命周期：数据导入 → 风险评估 → 审计程序执行 → 证据收集 → 错报评价 → 审计意见。

## 目标用户

- 硕士申请作品集（首要用途）
- AI / Data Science / CS 研究生申请材料
- GitHub 开源展示
- 对未来企业级审计 AI 平台的原型验证

## 核心价值

1. **Evidence-driven**: 每一个结论都有可追溯的证据。Citation 不是 LLM 生成的，而是从真实检索结果中来的
2. **Evaluation-driven**: 每一次开发都有量化指标（Precision/Recall/F1）衡量效果
3. **Full pipeline**: 从 Excel 导入到 ISA 705 审计意见，30 秒内完成

## 四个最重要的模块

| 模块 | 说明 |
|------|------|
| **Document Pipeline** | PDF → Parse → OCR → Chunk → Embed → PGVector (67 PDFs, 2950 chunks) |
| **Workflow Engine** | DAG 编排 5 Agent (Planner/Knowledge/Risk/Evidence/Reviewer) + HITL + Trace |
| **Anomaly Detection** | 12 Signal Detectors → Risk Scoring Engine → Finding (F1 64.6% on Kaggle) |
| **Evidence Grounding** | Citation must come from real documents, not LLM hallucination |

## 当前版本

v0.4.0 (Prototype stage)

## 当前开发阶段

**Architecture Review → System Verification Review (SVR)**

已完成所有核心模块的 MVP 闭环，当前重点是：真实数据测试、评估体系完善、代码质量提升。

---

# PROJECT_CONTEXT

## 项目当前状态

**全部服务运行中:**
- Docker: PostgreSQL + PGVector (5432), MinIO (9000), Redis (6379) — 全部 healthy
- Backend: FastAPI on localhost:8000
- Frontend: Vite React on localhost:3000

**测试:**
- 77 unit tests passing (pytest)
- 10 workflow integration tests
- 12 document pipeline integration tests
- 0 regression across all changes

## 完成了哪些模块

### 核心 Agent 管线 (Sprint 1)
- 5 个 Real LLM Agents (Planner, Knowledge, Risk, Evidence, Reviewer) — 全部调用 DeepSeek API
- Workflow Engine (DAG + HITL + Trace + Checkpoint + Retry + Token Budget + Sandbox)
- AgentRegistry + ToolRegistry + RBAC
- Agent-to-Workflow 集成（`scripts/bringup.py`）

### Document Pipeline (Sprint 2)
- PDF Parser (PyMuPDF) + OCR (RapidOCR, 95% 中文识别) + Semantic Chunking
- PGVector Store with HNSW index
- Local Embedding (BGE-small-en-v1.5, 384-dim, zero API cost)
- Hybrid Search (Keyword + Vector + RRF Reranker)

### Full Integration Demo (Sprint 3)
- End-to-end pipeline: PDF → 5 Agents → Workpaper → Audit Report
- Evidence-based Knowledge Agent (2436 tokens output from retrieved chunks)

### Evaluation & Baseline (Sprint 4)
- Evaluation Framework (L1/L2/L3 Metrics, Runner, ExperimentTracker, PromptRegistry)
- Human Evaluation (10 annotated cases)
- Consistency Testing (8 cases × 2 runs)
- Citation Support LLM Judge

### Production Readiness (Sprint 5)
- Docker Compose (PostgreSQL, MinIO, Redis, Prometheus, Grafana)
- FastAPI with 4 routers (Agents, Documents, Workflows, Knowledge)
- WebSocket (real-time Workflow event push)
- Rate Limiting middleware
- Nginx reverse proxy + TLS 1.3 config
- CI/CD (GitHub Actions: lint, test, Bandit security, AI Evaluation gate)
- Audit Log (append-only `audit_logs` table)
- Prompt injection defense (`UNTRUSTED_DATA` wrapper)

### Revenue Cutoff Vertical Slice (Phase A-E)
- **Phase A**: Excel Import → Canonical Schema (Transaction/Document/Party), Import Framework (ImportSession/ImportRecord/MappingProfile)
- **Phase B**: Audit Program → Sampling Engine (MUS/random/all) → CutoffProcedureExecutor (29 txns, 4 exceptions found)
- **Phase C**: Evidence Graph (Assertion → Evidence → Sufficiency, CUTOFF 50%/OCC 33%)
- **Phase D**: Misstatement Engine (Known/Likely/Projected → AJE/RJE, $215K total → EXCEEDS $50K tolerable → 4 AJE)
- **Phase E**: Audit Completion (Partner Review, EQCR, Opinion DISCLAIMER, Management Rep Letter, Archive)

### Financial Analytics (Phase F)
- RatioEngine (7 ratios: Current, Quick, Gross Margin, Net Margin, AR Turnover, Inventory Turnover, Debt Ratio)
- TrendEngine (YoY comparison + anomaly detection at 30% threshold)
- AccountAnalyzer (significant account identification at 5% threshold)
- Multi-period Analysis (3+ year trend, 6 pattern types)

### Anomaly Detection — Risk Scoring Engine
- 12 Signal Detectors (Detection pattern, not score)
- Signal Registry (register-based, additive)
- Risk Profile (Revenue/Purchase/Expense with severity_mapping/procedure_template)
- Finding Layer (Canonical Audit Finding — evidence_refs/procedure_refs/assertions)
- Evaluation Benchmark (Per-signal, per-risk, confusion matrix, JSON/MD reports)

### Procedure Library
- 7 procedure templates (Revenue Cutoff, Revenue Occurrence, Revenue Completeness, AR Aging, AP Existence, Inventory Valuation, Cash Reconciliation)

### Materiality Engine
- ISA 320: 4 bases (PBT/Revenue/Assets/Equity), 3 tiers (Overall/Performance/Trivial), risk-adjusted

### Confirmation Manager
- AR Confirmation: generate → send → receive → difference → alternative procedures

### Data/Datasets
- 67 audit PDFs indexed to PGVector (2,950 chunks) — CAS/CSAS/IAASB Handbooks/ISA 315
- Synthetic Data Factory (50,060 transactions, 3 years, 8 implanted audit risks)
- Kaggle Dataset #1 (7,000 rows, 955 anomalies, F1 64.6%)
- 5 Kaggle datasets downloaded to D:\audit_data\

### Frontend
- React + Vite (plain JSX, no TypeScript — TS transform failed on dev machine)
- Pages: Dashboard, Document Center, Evidence Graph, Agent Trace Viewer, Risk Matrix, Approvals
- Importmap-based module resolution (bare imports → `/node_modules/.vite/deps/`)

### Documentation & Blog
- 6 engineering blog articles (following blog_rules.md)
- README repositioned as "Evidence-Driven Audit Execution Prototype"
- Architecture RFCs: CANONICAL_AUDIT_SCHEMA.md, IMPORT_FRAMEWORK.md
- PHASE_BLOG_RULE.md (enforced blog writing policy)

## 未完成哪些模块

| 模块 | 状态 | 原因 |
|------|------|------|
| ERP Adapter (SAP/Oracle/Kingdee) | ❌ | 产品化阶段，开发成本极高 |
| Multi-tenant Deployment | ❌ | 超出 MVP 范围 |
| SSO Identity | ❌ | 超出 MVP 范围 |
| 全部 8 个业务循环的程序 | ❌ | 只有 Revenue Cutoff 完整实现，其余 7 个只有模板 |
| Neo4j Ontology | ❌ 冻结 | SQL Graph Ready，等需要时再迁移 |
| Anomaly Detection 权重调优 | ⚠️ | 架构已完成，Profile 权重需重新校准 |
| Frontend → Backend 真实 API 对接 | ⚠️ | 页面组件存在但使用 mock 数据 |

## 当前 Milestone

**Milestone: Evaluation & Hardening**

- 已完成: 架构重构完成、Evaluation 框架就绪
- 进行中: Anomaly Detection 权重调优 (F1 需要恢复到 60%+)
- 下一步: Kaggle 数据集的完整评估报告

## Known Issues

1. **Vite TypeScript 不工作**: 开发机上 `@vitejs/plugin-react` 无法转换 TSX/TS。前端已改为纯 JSX + `React.createElement`。如果新开发机支持 TypeScript，可以恢复。
2. **GitHub 推送不稳定**: 网络间歇性无法连接 github.com。commit 成功后偶尔需要重试 push。
3. **test_document_api.py 预存失败**: MinIO 连接 + SQLite 表创建问题（与本次修改无关，之前就存在）。
4. **Anomaly Detection F1 从 64.6% 降至 25.4%**: 架构重构后（SignalResult→Detection + Registry + RiskProfile 重新设计）weight 体系变化，需要重新调优。底层 Signal 质量未变。
5. **Python 3.7 默认版本问题**: 系统 PATH 中有 Python 3.7，需要使用 `py -3.11` 指定版本。

## Technical Debt

| 债务 | 严重程度 | 说明 |
|------|---------|------|
| Prompt 硬编码在 Python 代码中 | MEDIUM | `prompts/` 目录存在但为空。`LlmBaseAgent.load_prompt()` 已实现但未被调用 |
| `application/` 层服务未通过 API 使用 | MEDIUM | DocumentService/RiskService/ReportService 三个 Application Service 存在但 API 直接调用 Infrastructure |
| PostgreSQL 持久化不完整 | LOW | WorkflowState 和 Trace 有 PG 表但 engine 仍用内存存储 |
| 前端未启用后端 API | LOW | 页面组件存在但使用 mock 数据 |
| 测试覆盖不足 | LOW | Anomaly Detection、Materiality、Procedure Engine 主要靠 demo 验证，缺乏正式单元测试 |

## Risk

| 风险 | 概率 | 影响 |
|------|------|------|
| DeepSeek API Key 过期 | HIGH | 所有 Agent 不可用。备用: OpenAI |
| GitHub 长期不可达 | MEDIUM | 代码可本地备份，但无法展示 |
| 依赖库版本冲突 (NumPy/PyTorch) | MEDIUM | fastembed 工作正常但扩展 ML 模型可能触发 |
| OCR 中文识别依赖网络 | LOW | RapidOCR 模型本地缓存后离线可用 |

---

# CURRENT ARCHITECTURE

## 系统架构

```
用户界面 (React + Vite, port 3000)
        │
        ▼
API Gateway (FastAPI, port 8000)
        │
   ┌────┴─────┬──────────┬──────────┐
   ▼          ▼          ▼          ▼
Documents  Workflows  Knowledge  WebSocket
   │          │          │          │
   └──────────┴──────────┴──────────┘
        │
        ▼
   Application Services (Use Case 编排)
        │
   ┌────┴─────────────────┐
   ▼                      ▼
Domain (Finance)    Domain (Audit)
Transaction         AuditProgram
Document            AuditProcedure
Party               AuditFinding
Detection           EvidenceGraph
Finding             Misstatement
                    AuditCompletion
        │
        ▼
Infrastructure
LLM/Vector/OCR/Parser/Storage/Excel/Security/Sandbox
        │
        ▼
PostgreSQL (PGVector) + MinIO + Redis + Docker
```

## 模块划分

### 领域层 (Domain)

| 上下文 | 模块 | 位置 |
|--------|------|------|
| **Finance** | Transaction, Document, Party, AccountEntry (预留) | `domain/finance/entities/` |
| **Finance** | RatioEngine, TrendEngine, AccountAnalyzer, MultiPeriodAnalyzer | `domain/finance/services/` |
| **Finance** | ImportSession, ImportRecord, MappingProfile | `domain/finance/entities/import_framework.py` |
| **Finance** | RiskScoringEngine, Signal/Detection, Finding | `domain/finance/anomaly/` |
| **Audit** | AuditProgram, AuditProcedure, AuditAssertion, SamplingConfig | `domain/audit/entities/procedure.py` |
| **Audit** | EvidenceGraph, AssertionNode, EvidenceNode, EvidenceMapper | `domain/audit/entities/evidence_graph.py` |
| **Audit** | Misstatement, AdjustmentEntry, MisstatementSummary, MisstatementEngine | `domain/audit/entities/misstatement.py` |
| **Audit** | AuditCompletion, PartnerReview, EQCR, AuditOpinion, ManagementRepresentation | `domain/audit/entities/completion.py` |
| **Audit** | ConfirmationRequest, ConfirmationRegister, ConfirmationManager | `domain/audit/entities/confirmation.py` |

### 基础设施层 (Infrastructure)

| 模块 | 文件 | 说明 |
|------|------|------|
| LLM | `deepseek_provider.py`, `openai_provider.py`, `router.py` | DeepSeek primary, OpenAI fallback |
| Vector | `local_embedding.py`, `pgvector_store.py`, `chunking.py` | BGE 384-dim local + PGVector |
| OCR | `ocr_service.py`, `rapid_ocr.py`, `paddle_ocr.py` | Tesseract/RapidOCR/PaddleOCR |
| PDF | `pdf_parser.py`, `layout.py` | PyMuPDF parser with OCR detection |
| Excel | `excel_adapter.py` | Excel → ImportSession → Transaction |
| Security | `sanitizer.py`, RBAC in `agents/base.py` | Prompt injection defense + role-permission |
| Sandbox | `sandbox.py` | AsyncTimeoutSandbox + SubprocessSandbox stub |
| Database | `models/audit_log.py`, `models/workflow.py` | SQLAlchemy persistent models |

### Workflows

| 模块 | 文件 | 说明 |
|------|------|------|
| Engine | `engine.py` | DAG execution + HITL + Trace + Checkpoint + Retry + TokenBudget + Sandbox |
| Models | `models.py` | GraphDefinition, AgentNode, Edge, WorkflowState, ApprovalDecision |
| Context | `context.py` | ContextManager — build, compress, summarization |
| Memory | `memory.py` | In-memory cross-agent session memory |
| Trace | `trace/` | InMemoryTraceStore + PgTraceStore (optional PG persistence) |
| Budget | `budget/tracker.py` | TokenBudgetTracker |

## 数据流

```
完整审计管线 (Revenue Cutoff Demo):

Excel Import (50,060 rows)
    ↓
ImportSession → ImportRecord → Validation → Canonical Transaction
    ↓
Financial Analytics (Ratio/Trend/Significant Account)
    ↓
Risk Assessment (LLM Agent: HIGH severity identified)
    ↓
Audit Program (Procedure: CUTOFF_TEST, Sampling: ALL)
    ↓
Procedure Execution (29 transactions → 4 cutoff exceptions, 13.8%)
    ↓
Evidence Graph (CUTOFF 50%, OCCURRENCE 33% → PARTIALLY SATISFIED)
    ↓
Misstatement Engine ($215K known → EXCEEDS $50K tolerable → 4 AJE)
    ↓
Audit Completion (Partner APPROVED, EQCR APPROVED)
    ↓
Audit Opinion (DISCLAIMER per ISA 705)
```

## 数据库

- **PostgreSQL 17** + PGVector (HNSW index)
- 主要表: `documents`, `embedding_items` (384-dim vector), `ontology_nodes`, `ontology_edges`, `execution_traces`, `workflow_checkpoints`, `audit_logs`
- 开发环境: `DATABASE_URL=postgresql+asyncpg://auditflow:auditflow@localhost:5432/auditflow`
- 迁移: Alembic (`backend/migrations/`)

## Agent 列表

| Agent | 文件 | 版本 | LLM 调用 | 说明 |
|-------|------|------|---------|------|
| Planner | `agents/planner/agent.py` | v0.2 | DeepSeek | 任务拆解 |
| Knowledge | `agents/knowledge/agent.py` | v0.3 | DeepSeek | 准则检索（支持 context.document_chunks） |
| Risk | `agents/risk/agent.py` | v1.0 | DeepSeek | 风险识别（citation grounded） |
| Evidence | `agents/evidence/agent.py` | v0.2 | DeepSeek | 证据匹配 |
| Reviewer | `agents/reviewer/agent.py` | v0.2 | DeepSeek | 质量审查 |

## API

| 路由 | 端点 | 说明 |
|------|------|------|
| Agents | `GET /api/v1/agents` | 列出 5 个 Agent |
| Agents | `POST /api/v1/agents/{name}/execute` | 执行单个 Agent |
| Documents | `GET/POST /api/v1/documents` | 文档 CRUD |
| **Workflows** | `POST /api/v1/workflows` | 创建审计 Workflow |
| **Workflows** | `GET /api/v1/workflows/{id}` | 查询状态 |
| **Workflows** | `POST /api/v1/workflows/{id}/start` | 启动 |
| **Workflows** | `GET /api/v1/workflows/{id}/trace` | 执行轨迹 |
| **Workflows** | `POST /api/v1/workflows/approvals` | 提交审批 |
| **Knowledge** | `POST /api/v1/knowledge/search` | 语义检索 |
| WebSocket | `/api/v1/ws/workflows/{id}` | 实时事件推送 |

## 目录结构

```
auditflow/
├── backend/
│   ├── src/
│   │   ├── agents/              5 LLM Agents
│   │   ├── workflows/           Workflow Engine + HITL + Trace
│   │   ├── domain/
│   │   │   ├── finance/         Canonical Schema + Analytics + Anomaly Detection
│   │   │   └── audit/           Procedure + Evidence + Misstatement + Completion
│   │   ├── infrastructure/      LLM/Vector/OCR/Parser/Excel/Security/Sandbox/Storage
│   │   ├── evaluation/          Metrics/Runner/Experiment/PromptRegistry
│   │   ├── application/         Use Case Services (Document/Risk/Report/AuditLog)
│   │   ├── api/                 FastAPI routers + middleware + WebSocket
│   │   └── main.py              FastAPI entry point
│   ├── scripts/                 15+ 演示/评估/工具脚本
│   ├── tests/                   77 unit + integration tests
│   └── prompts/                 Agent prompt 目录 (占位)
├── frontend/                    React + Vite (JSX, no TS)
├── datasets/                    67 审计 PDFs
├── docs/
│   ├── architecture/            CANONICAL_AUDIT_SCHEMA.md, IMPORT_FRAMEWORK.md
│   ├── blog/                    6 篇工程博客
│   └── issues/                  架构文档 / ADR
├── docker-compose.yml           基础设施 (PG+MinIO+Redis+Prometheus+Grafana)
├── docker-compose.prod.yml      生产环境 (含 Nginx)
├── .github/workflows/ci.yml     CI/CD
└── README.md                    重定位为 Evidence-Driven Audit Execution Prototype
```

## 为什么这样设计

**分层原则:** DDD + Clean Architecture。Domain 层无基础设施代码，Agent 之间不直接通信，Workflow Engine 统一编排。

**数据先于模型:** Canonical Audit Schema 先于代码冻结（RFC 文档在 docs/architecture/），确保所有模块对 Transaction/Document/Party 的理解一致。

**评估驱动:** 每个模块必须有量化指标。Anomaly Detection 有 Precision/Recall，Risk Agent 有人工标注基准。

**证据优先:** 所有 AI 输出必须可追溯。Citation 从检索结果生成，不是 LLM 编的。

---

# IMPORTANT DECISIONS

## 决策 1: PDF Pipeline 保留，增加 Structured Data Channel

**背景:** 最初系统只有 PDF Pipeline。后发现在真实审计中，大量数据是结构化（TB/GL/明细账）。

**方案:** 不废弃 PDF Pipeline，而是增加 Canonical Schema + Import Framework，形成两个并行输入通道。

**Trade-off:** 增加了系统复杂度（多一个数据模型层），但使 Risk Agent 能同时访问结构化数据和非结构化文档。

## 决策 2: 嵌入方案从 OpenAI → 本地 fastembed (BGE)

**背景:** OpenAI embedding 需要额外 API Key 和费用。

**方案:** 切换到 BAAI/bge-small-en-v1.5 (384-dim, ONNX, fastembed)。零成本、零外部依赖、本地运行。

**Trade-off:** 精度略低于 `text-embedding-3-large` (3072-dim)，但成本优势远超精度损失。

**影响:** 本地部署可行，无 API 瓶颈。`LocalEmbeddingProvider` 实现于 `infrastructure/vector/local_embedding.py`。

## 决策 3: LLM 从 OpenAI → DeepSeek

**背景:** 成本控制。

**方案:** DeepSeek 通过 OpenAI-compatible API 接入。系统保留 OpenAI 作为 fallback。

**Trade-off:** DeepSeek 在某些审计知识上可能略弱，但价格便宜 10x。

## 决策 4: Canonical Audit Schema 冻结后编码

**背景:** 审计数据模型影响所有后续模块。如果直接开始编码，后期返工成本高。

**方案:** 先写两份 RFC 文档（`CANONICAL_AUDIT_SCHEMA.md` + `IMPORT_FRAMEWORK.md`），在团队确认冻结后再实现代码。

**Trade-off:** 前期投入 2 天写出全面规范，但后期零返工。

## 决策 5: ImportRecord → 0..1 Transaction (非 1:1)

**背景:** Excel 导入可能有验证失败的行。如果 ImportRecord 与 Transaction 是 1:1，则验证失败的行没有对应实体。

**方案:** ImportRecord → 0..1 Canonical Object（通过 `canonical_refs`）。raw_data 永久保存，用户可修正 Mapping 后重新生成 Transaction，无需重新上传。

**影响:** 这是企业 ETL 的标准模式（SAP/Oracle 都这样做）。

## 决策 6: 重要性计算用算术不用 LLM

**背景:** ISA 320 提供了清晰的百分比基准。用 LLM 判断重要性会引入不必要的黑盒。

**方案:** MaterialityEngine 实现为纯算术函数 (overall = min(base × ISA%)、performance = overall × risk_factor、trivial = overall × 5%)。

## 决策 7: Evidence Graph 用规则表不用 LLM

**背景:** 证据充分性判断需要透明的逻辑。每类 Assertion 需要哪些 Evidence 是审计准则明确规定的。

**方案:** `EvidenceMapper.REQUIRED_EVIDENCE` 固定映射表（CUTOFF→[INVOICE, DELIVERY], OCCURRENCE→[INVOICE, CONTRACT, DELIVERY]）。LLM 负责找证据，Graph 负责判充分性。

## 决策 8: Prompt Injection 防御用规则不用 LLM

**背景:** 外部文档可能包含注入指令。

**方案:** `sanitizer.py` 用正则模式检测 + `UNTRUSTED_DATA` 包装。不使用 LLM 检测注入（因为 LLM 本身可能被注入）。

## 决策 9: 前端放弃 TypeScript → 纯 JavaScript

**背景:** 开发机上 `@vitejs/plugin-react` + TypeScript 的 esbuild 转换不工作（`VITE v5.4.21` 无法编译 TSX）。

**方案:** 全部前端文件改为 `.jsx` + `React.createElement`（无 JSX 语法）。使用 importmap 解决 bare import 问题。

**Trade-off:** 失去类型检查，但页面可正常工作。如果新开发环境支持 TS，可恢复。

---

# CURRENT IMPLEMENTATION

## 已实现模块（约 60 个）

**Agent 层:** 5 个 Agent + AgentRegistry + ToolRegistry + RBAC

**Workflow 层:** DAG Engine + HITL + Trace + Checkpoint + Retry(≤3) + TokenBudget + Sandbox + 16 EventTypes

**Domain Finance 层:** Transaction, Document, Party, AccountEntry, ImportSession, ImportRecord, MappingProfile, RatioEngine, TrendEngine, AccountAnalyzer, MultiPeriodAnalyzer, 12 Signal Detectors, RiskScoringEngine, RiskProfile(×3), Finding

**Domain Audit 层:** AuditProgram, AuditProcedure, AuditAssertion, SamplingEngine, CutoffProcedureExecutor, EvidenceGraph, EvidenceMapper, Misstatement, AdjustmentEntry, MisstatementSummary, MisstatementEngine, AuditCompletion, PartnerReview, EQCR, AuditOpinion, ManagementRepresentation, ConfirmationManager, MaterialityEngine

**Infrastructure 层:** DeepSeekProvider, OpenAIProvider, LocalEmbeddingProvider, PGVectorStore, SemanticChunking, PyMuPDFParser, RapidOCRService, TesseractOCRService, PaddleOCRService, ExcelAdapter, AuditLogService, SubprocessSandbox, PromptSanitizer

**API 层:** 4 REST Routers + 1 WebSocket + RateLimitMiddleware + TraceMiddleware + TenantMiddleware

**Evaluation 层:** L1/L2/L3 Metrics, EvaluationRunner, ExperimentTracker, PromptRegistry, Human Evaluation, Consistency Test, Golden Dataset Benchmark

**Frontend:** Dashboard, DocumentCenter, EvidenceGraph, AgentTraceViewer, RiskMatrix, Approvals

## 已实现测试

- 77 unit tests (agents, workflow, evaluation, grounding, services)
- 10 workflow integration tests
- 12 document pipeline integration tests
- Golden Dataset Evaluation (8 implanted risks, 100% Recall)

## 已实现页面

- Navigation bar with 7 tabs
- Evidence Chain visualization
- Agent Execution Trace table

---

# ROADMAP STATUS

## 已经完成

✅ V1: Revenue Cutoff 全闭环 (Phase A-E)
✅ V2: Financial Analytics + Procedure Library + Evidence Graph
✅ V3: Journal Entry Testing + Materiality Engine
✅ V4: Multi-period Analysis + Confirmation Manager
✅ System Bring-up (Sprint 1)
✅ Pipeline Validation (Sprint 2)
✅ Full Integration Demo (Sprint 3)
✅ Evaluation & Baseline (Sprint 4)
✅ Production Readiness (Sprint 5)
✅ Golden Dataset Factory (50K transactions)
✅ Kaggle Integration (5 datasets downloaded)
✅ Anomaly Detection Architecture (12 Signals, Registry, RiskProfile, Finding)
✅ 6 Engineering Blog Articles

## 正在开发

🔄 Anomaly Detection 权重调优 (F1 需恢复到 60%+)
🔄 GitHub 推送 (commit 已保存, 网络恢复后手动 push)

## 未来计划

⬜ Anomaly Detection 权重调优 (Profile re-tuning for new Detection architecture)
⬜ 扩展 Procedure Library 到 7 个其余业务循环 (Inventory, AR, AP, Cash, Payroll, Fixed Assets, Borrowing)
⬜ 前端 → 后端真实 API 对接
⬜ Prompt 外部化到 `prompts/` 目录
⬜ PostgreSQL 持久化 WorkflowState (当前内存)
⬜ Kaggle Dataset #2-5 评估
⬜ ERP Adapter (Kingdee/Yonyou) — 低优先级
⬜ Multi-tenant — 低优先级

---

# OPEN QUESTIONS

1. **Anomaly Detection Profile 权重**: 新的 Detection 架构下，Revenue/Purchase/Expense Profile 的最优权重值是多少？需要网格搜索还是启发式？

2. **Risk Agent prompt 微调**: 当前 8/8 Recall (100%) 但来自简单的场景描述。在真实复杂 TB 数据上是否保持？需要更多测试。

3. **Evidence Graph integration**: Finding → Procedure → Evidence Graph 的完整链路尚未端到端验证。

4. **Neo4j Ontology**: 用户明确说过 "冻结，等需要时再上"。但 SQL-based 的知识图谱在复杂多跳推理场景下确实有瓶颈。触发条件是什么？

---

# KNOWN BUGS

| Bug | 严重性 | 详情 |
|-----|--------|------|
| test_document_api.py 预存失败 | LOW | MinIO connection refused + SQLite table missing。与本次修改无关 |
| Vite TS 不工作 | MEDIUM | @vitejs/plugin-react esbuild 无法编译 TSX。已 workaround 为 JSX |
| Anomaly Detection F1 下降 | MEDIUM | 架构重构后 Profile 权重需重调，底层 Signal 精度未变 |
| GitHub push 间歇失败 | LOW | 网络问题。commit 成功，需重试 push |

---

# TECHNICAL DEBT

1. Prompt 在 Python 代码中硬编码 (MEDIUM)
2. `application/` 层 Service 已有但 API 未使用 (MEDIUM)
3. PG 持久化表存在但 engine 仍用内存 (LOW)
4. 前端 mock 数据 (LOW)
5. Anomaly Detection 的 Finding Layer 未集成到 Procedure Agent (LOW)
6. demo 脚本散落在 `scripts/` 中，未按功能组织 (LOW)

---

# ENGINEERING LESSONS

## 最重要的经验

1. **评估先于开发**: 第一次跑评估时发现 Agent 输出 0% 准确率——这在手动 demo 中是看不到的。自此所有新功能都先定义评估指标。

2. **Citation 必须来自检索，不是 LLM**: `document_id="llm_analysis"` 是一个分水岭 bug。修复后所有 Citation 都来自真实文档。这是整个系统可信性的基础。

3. **多 Agent 集成成本远大于单 Agent 开发**: Workflow Engine 花的时间比 5 个 Agent 加起来都多。

4. **Schema 冻结先于编码**: Canonical Audit Schema 的 RFC 是投入产出比最高的文档。编码时零返工。

5. **架构重构 > 调参优化**: 从 `JournalAnomalyDetector` 升级为 `RiskScoringEngine` 带来了 Signal/Profile/Registry/Finding 四层架构。F1 暂时下降是可接受的——架构价值超越单一指标。

## 踩坑

- **Windows GBK 编码**: 多次因 emoji/中文引起 `UnicodeEncodeError`。所有输出都改为 ASCII-safe。
- **Python 3.7 默认**: `match` 语法不支持，所有 `match/case` 改为 `if/elif`。
- **PowerShell 字符串转义**: `"` 和 `\` 需要额外处理。复杂 Python 代码优先写入 `.py` 文件。
- **load_dotenv 不覆盖已有变量**: 导致系统环境中的旧 API Key 被使用。修复: `load_dotenv(override=True)`。
- **PGVector `::vector` 语法**: asyncpg 不支持 `:param::vector` 语法。改为 `CAST(:param AS vector)`。

---

# BLOG ASSETS

## 已发布的 6 篇博客

1. `building-auditflow.md` — 整体工程回顾 (~3000 words)
2. `from-document-ai-to-audit-execution.md` — Phase A/B/C 架构 pivot
3. `misstatement-engine.md` — Phase D 错报引擎
4. `audit-completion-engine.md` — Phase E 审计完成
5. `journal-testing-materiality.md` — V3 (Journal Testing + Materiality)
6. `multi-period-confirmation.md` — V4 (Multi-period + Confirmation)

## 建议下一篇博客

**"Risk Scoring Engine: From Hand-Tuned Weights to Explainable Audit Findings"**
- 覆盖: Signal → Detection → Registry → RiskProfile → Finding 的完整架构决策
- 数据: Kaggle Benchmark 结果 (Per-Signal Precision 表)
- 关键词: explainability, anomaly detection, audit AI, domain architecture

---

# NEXT RECOMMENDED TASK

## 最高优先级: Anomaly Detection Profile 权重调优

**为什么**: 架构重构已完成（SignalResult → Detection + Registry + RiskProfile + Finding），但 Profile 的权重值还是旧架构的产物，需要为新 Detection 格式重新校准。

**怎么做**:
1. 运行 `py -3.11 -m domain.finance.anomaly.evaluation.benchmark` 查看当前 Baseline
2. 调整 `scoring/profile.py` 中 RevenueFraud 的 weights/threshold 参数
3. 用 Kaggle Dataset #1 (7,000 rows, 955 labels) 验证
4. 目标: F1 恢复到 60%+

## 次高优先级: Finding 层集成到 Procedure Agent

**为什么**: Finding 已经是整个 AuditFlow 的统一语言。Procedure Agent 当前不消费 Finding——它直接从 Risk Agent 的输出生成程序。

**怎么做**:
1. 修改 Procedure Agent 接受 `context.findings` 输入
2. 让 Finding 中的 `procedure_template` 和 `recommended_procedures` 成为 Procedure Agent 的输入
3. 端到端验证: Transaction → Detection → Finding → Procedure → Evidence Graph

---

*End of Handover Document*
