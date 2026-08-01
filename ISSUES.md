# AuditFlow — Epic → Milestone → Issue 体系 (v3.2 — Architecture Baseline v1.0 冻结)

> **v3.1 → v3.2 变更（第 5 轮 Architecture Gate Review）：**
> - Agent Runtime 增加执行限制（max_iterations / timeout / retry policy / human escalation）
> - 新增 **Artifact Registry**（统一 Artifact 类型注册与发现）
> - Prompt Registry 增加 **Prompt Version Evaluation**（区分 Prompt vs Model 的影响）
> - Audit Log 升级为 **Append-Only Hash Chain**（tamper-evident 防篡改）
> - Event Contract 增加 `AGENT_FAILED` 事件
> - MVP 边界增加 **Workpaper Draft**
>
> **此前变更历史：**
> - v2 → v3: Agent 8→4, E0 拆分, Ontology 升级, HITL 提前, Evaluation 四层, Benchmark 独立
> - v3 → v3.1: Risk 回归 Agent, Artifact/Event Contract, Ontology PG Graph Ready, Immutable Audit Log

---

# MVP Beta 边界定义（Grill #6 修正）

## 包含
- PDF 财报文档上传与解析
- 审计准则知识检索（ISA 315/330/500/240 + IFRS 15）
- 5 Agent 审计链（Planner → Knowledge → Risk → Evidence → Reviewer）
- 风险识别与评级 + Citation 追溯
- Human Review 审批闭环
- **工作底稿草稿生成**（Workpaper Draft — 含 Risk/Procedure/Evidence/Conclusion 结构）
- 审计报告草稿生成（Report Draft — ISA 700 标准结构）
- Evaluation 四层体系 + Benchmark 覆盖 7 领域
- Docker Compose 部署 + OpenTelemetry
- Append-Only Audit Log（tamper-evident hash chain）

## 不包含
- 自动出具最终审计意见（Human Final Authority）
- 复杂 Excel 财务模型（多维分析/合并报表）
- ERP 系统实时连接（SAP/Oracle）
- 多租户商业化权限（仅实现 RBAC 骨架）
- SSO / LDAP 企业认证
- 分布式部署 / K8s
- 知识图谱可视化（Graph DB 迁移延后）

---

# 总览

| Epic | 名称 | 周数 | 并行度 | API Freeze |
|------|------|------|--------|------------|
| E0 | Foundation | 1w | 串行先导 | — |
| E0.5 | Agent Kernel + Eval Core | 1.5w | 依赖 E0 | Agent Contract v1 |
| E1A | Document Intelligence | 3w | 与 E1B 并行 | Document API v1 |
| E1B | Audit Intelligence Model | 3w | 与 E1A 并行 | Knowledge API v1 |
| E2 | Retrieval & Evidence Engine | 3w | 依赖 E1A+E1B | Search API v1 / Evidence API v1 |
| E3 | Agent Core Runtime | 3.5w | 依赖 E2 | Agent Execution API v1 |
| E4 | Audit Services | 2.5w | 依赖 E3 | Approval API v1 / Report API v1 |
| E5 | Product Experience | 持续 | 跟随 E1A 起并行 | — |
| E6 | Production & Compliance | 2w | 贯穿 E0-E4 | — |
| E7 | Benchmark Expansion | 1.5w | 与 E1A 起并行 | — |
| **总计** | **9 个 Epic** | **~18w MVP** | | |

---

# 核心设计决策

## Agent vs Service 分类（Grill #3 修正 — Risk 回归 Agent）

| 组件 | 类型 | 自主决策循环 |
|------|------|-------------|
| **Planner** | Agent ✅ | 任务拆解策略 — 基于 Ontology 推理链选择子任务序列 |
| **Knowledge** | Agent ✅ | 检索策略选择 — 决定用 Vector/Keyword/Hybrid，如何过滤 |
| **Risk** | Agent ✅ | **风险等级判断 + 程序推荐 + 证据不足时迭代补充** |
| **Evidence** | Agent ✅ | 证据相关度选择 — 多个候选 Chunk 中筛选最相关的 |
| **Reviewer** | Agent ✅ | 质疑/退回/通过判断 — 是否要求上游重新执行 |
| Planning Engine | Service | 公式计算（Materiality/Sampling）+ 模板 |
| Workpaper Generator | Service | 模板渲染 + Citation 嵌入 |
| Report Generator | Service | 模板渲染 + 格式转换 |

> **原则不变：** 确定性计算/模板渲染/规则匹配 = Service。Risk 包含"证据不足→要求补充→重新评估"的迭代循环，因此是 Agent。

---

## Agent Contract v1（Grill #5 修正 — 增加 Artifact + Event）

### 基础 Contract（E0.5 锁定，不变）

```python
class AgentRequest(BaseModel):
    workflow_id: str
    project_id: str
    task_id: str
    firm_id: str
    client_id: str
    engagement_id: str
    context: dict
    inputs: dict
    memory: dict

class AgentResponse(BaseModel):
    status: Literal["SUCCESS", "PARTIAL", "FAILED", "NEEDS_HUMAN"]
    result: dict
    citations: list[Citation]
    confidence: float
    metrics: dict
    next_action: str
```

### Artifact Contract（v3.1 新增）

```python
class AuditArtifact(BaseModel):
    """所有 Agent/Service 的结构化产出 — 不是 text blob"""
    artifact_type: str          # "risk_finding" | "evidence_package" | "audit_plan" | ...
    artifact_id: str
    created_by: str             # agent_name
    schema_version: str         # "v1"
    content: dict               # 结构化 JSON
    citations: list[Citation]
    parent_artifact_id: str | None  # 溯源链

# 具体 Artifact 类型示例
class RiskFindingArtifact(AuditArtifact):
    artifact_type: Literal["risk_finding"]
    content: RiskFindingContent

class RiskFindingContent(BaseModel):
    area: str
    title: str
    severity: str               # CRITICAL | HIGH | MEDIUM | LOW
    probability: float
    indicators: list[str]
    related_standards: list[str]
    suggested_procedures: list[ProcedureSuggestion]
    reasoning: list[str]        # Agent 推理链

class EvidencePackageArtifact(AuditArtifact):
    artifact_type: Literal["evidence_package"]
    content: EvidencePackageContent

class EvidencePackageContent(BaseModel):
    claims: list[EvidencedClaim]
    coverage: float             # 有证据的 claim / 总 claim
    unmatched: list[str]

class AuditPlanArtifact(AuditArtifact):
    artifact_type: Literal["audit_plan"]
    content: AuditPlanContent

class AuditPlanContent(BaseModel):
    materiality: MaterialityCalc
    sampling_strategy: SamplingStrategy
    procedures: list[ProcedureDef]
    timeline: dict

class ReviewReportArtifact(AuditArtifact):
    artifact_type: Literal["review_report"]
    content: ReviewReportContent

class ReviewReportContent(BaseModel):
    review_result: str          # APPROVED | NEEDS_REVISION | REJECTED
    issues: list[ReviewIssue]
    quality_score: float
```

### Event Contract（v3.1 新增）

```python
# Workflow 事件 — WebSocket 推送 + 持久化
class WorkflowEvent(BaseModel):
    event_id: str
    workflow_id: str
    event_type: str             # 见下方枚举
    timestamp: datetime
    payload: dict

# 事件类型枚举（v3.2 冻结 — 11 种事件）
# AgentStarted        → {agent_name, task_summary}
# AgentThinking       → {agent_name, step_description}
# ToolCalled          → {agent_name, tool_name, params_summary}
# ToolCompleted       → {agent_name, tool_name, result_summary, duration_ms}
# RetrievalCompleted  → {query, hit_count, top_score}
# EvidenceFound       → {evidence_id, claim, source_summary}
# ArtifactCreated     → {artifact_id, artifact_type, created_by}
# RiskDetected        → {risk_id, area, severity}
# AgentCompleted      → {agent_name, duration_ms, tokens, confidence}
# AgentFailed         → {agent_name, error_type, retry_count, recoverable}
# ApprovalRequired    → {approval_id, agent_name, severity, summary}
# ApprovalSubmitted   → {approval_id, decision, comment}
# WorkflowPaused      → {reason}
# WorkflowResumed     → {}
# WorkflowCompleted   → {total_duration, total_tokens, total_cost}
# WorkflowFailed      → {error, recoverable}
```

---

## Evaluation 四层体系（E0.5 骨架 + E7 数据）

| Layer | 名称 | 指标 | 能力建设 | 数据来源 |
|-------|------|------|----------|----------|
| L1 | Retrieval | Recall@K, MRR, NDCG | E0.5 Evaluation Runner | E7 Benchmark |
| L2 | Agent | Risk Accuracy, Severity Accuracy, Reasoning Quality | E0.5 Evaluation Runner | E7 Benchmark (per Agent) |
| L3 | Grounding | Citation Precision, Citation Recall, Unsupported Claim Rate | E0.5 Evaluation Runner | E2 Grounding Checker |
| L4 | Workflow | Completion Rate, Human Intervention Count, Time Reduction | E4 完成后 | E7 End-to-End Cases |

---

## Backend Capability First Rule（Grill #8 修正）

| 规则 | 说明 |
|------|------|
| 前端只消费已冻结 API | 每个 Epic 完成时冻结对应 API v1，前端才能开始消费 |
| 前端不设计不存在的数据 | 禁止前端定义后端尚未实现的 Schema |
| Contract 变更双向通知 | API v1 冻结后如需变更 → 升级 v2 + 前端同步 |
| 前端可提前准备 Mock | 基于冻结的 API Contract 用 MSW 做 Mock 开发 |

---

# 依赖关系图

```
E0 Foundation (1w)
    │
    ▼
E0.5 Agent Kernel + Eval Core (1.5w)
    │  ├── Agent Contract v1 (Artifact + Event)
    │  ├── HITL 状态机
    │  ├── Evaluation Runner
    │  └── Vertical Slice V0
    │
    ├──────────────────────────────────────────────┐
    │                                              │
    ▼                                              ▼
E1A Document Intelligence (3w)         E1B Audit Intelligence Model (3w)
    │                                      │  ├── Ontology (Graph Ready PG)
    │   E7 Benchmark Expansion (并行 1.5w)  │  ├── Knowledge Ingestion
    │                                      │  └── Reasoning Chains
    └──────────────┬───────────────────────┘
                   │
                   ▼
              E2 Retrieval + Evidence (3w)
                   │
                   ▼
              E3 Agent Core (3.5w)
                   │  ├── Planner / Knowledge / Risk / Evidence / Reviewer
                   │  └── Artifact Pipeline
                   ▼
              E4 Audit Services (2.5w)
                   │  ├── Planning Engine / Workpaper / Report
                   │  └── HITL Dashboard
                   ▼
    E5 Product Experience (贯穿 E1A→E4)
    E6 Production + Compliance (贯穿 E0→E4 → E6 收敛)
```

---

# Epic 0 — Foundation (1w)

## 目标
让项目可以运行——纯工程基础，不涉及 Agent。

---

### Milestone 0.1: Repository & DevOps

#### Issue 0.1.1 — 仓库骨架初始化
- **Labels:** `infra`, `phase-0` · **Depends on:** 无

**AC:** AES §4.2–4.19 目录树 / `pyproject.toml` (Python 3.11+) / `.env.example` / `make install && make lint` 通过。

#### Issue 0.1.2 — Docker Compose 开发环境
- **Labels:** `infra`, `phase-0` · **Depends on:** 0.1.1

**AC:** PG+PGVector/Redis/MinIO/FastAPI(hot-reload)/Celery Worker。`docker compose up -d` 全部 healthy。

#### Issue 0.1.3 — CI/CD Pipeline
- **Labels:** `infra`, `phase-0` · **Depends on:** 0.1.1

**AC:** PR → lint+test+type-check。main merge → docker build。失败阻止 merge。

---

### Milestone 0.2: Database Foundation

#### Issue 0.2.1 — Core Schema + Alembic
- **Labels:** `database`, `phase-0` · **Depends on:** 0.1.2

**AC:** tenants / users / audit_projects / documents 初始化。`alembic upgrade head` 可运行。

#### Issue 0.2.2 — MinIO Object Storage
- **Labels:** `storage`, `phase-0` · **Depends on:** 0.1.2

**I/O:**
```python
class ObjectStorage(ABC):
    async def upload(self, tenant_id, project_id, category, filename, content: bytes) -> StoragePath: ...
    async def download(self, path: StoragePath) -> bytes: ...
    async def get_presigned_url(self, path: StoragePath, expires=3600) -> str: ...
# 路径: {tenant_id}/{project_id}/{category}/{filename}
```

---

### Milestone 0.3: AI Infrastructure

#### Issue 0.3.1 — LLM Adapter + Model Router
- **Labels:** `ai-infra`, `phase-0` · **Depends on:** 0.1.2

```python
class LLMProvider(ABC):
    async def generate(self, messages, tools=None, **kwargs) -> LLMResponse: ...
class ModelRouter:
    async def route(self, task_type: "simple"|"complex"|"sensitive") -> LLMProvider: ...
```

**AC:** OpenAI/DeepSeek 可切换，Key 仅环境变量，Token 自动记录。

#### Issue 0.3.2 — Embedding Service + VectorStore
- **Labels:** `ai-infra`, `phase-0` · **Depends on:** 0.1.2

```python
class EmbeddingProvider(ABC):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
    def dimension(self) -> int: ...

class EmbeddingItem(BaseModel):
    id: str
    firm_id: str              # 审计事务所
    client_id: str            # 被审计客户
    engagement_id: str        # 审计年度
    source_type: Literal["CLIENT_DOCUMENT","AUDIT_STANDARD","WORKPAPER","RISK_CASE"]
    source_id: str
    content: str
    embedding: list[float]
    metadata: dict
    security_level: str       # PUBLIC | INTERNAL | CONFIDENTIAL | RESTRICTED
    created_at: datetime

class VectorStore(ABC):
    async def insert(self, items) -> None: ...
    async def search(self, query_vector, top_k, filters) -> list[EmbeddingItem]: ...
```

**AC:** PGVector HNSW 索引，支持 firm_id/engagement_id/source_type/security_level 过滤。

#### Issue 0.3.3 — Logging & Telemetry
- **Labels:** `observability`, `phase-0` · **Depends on:** 0.1.2

**AC:** structlog JSON 格式，trace_id 贯穿全链路，不记录 Secrets。

---

# Epic 0.5 — Agent Kernel + Evaluation Core (1.5w)

## 目标
验证 AES 神经系统。锁定所有 Contract。建立 Evaluation 骨架。

**API Freeze: Agent Contract v1（Artifact + Event + 基础 Contract）**

---

### Milestone 0.5.1: Agent Contract（全项目锁定）

#### Issue 0.5.1.1 — AgentRequest / AgentResponse / Citation
- **Labels:** `agent-kernel`, `contract` · **Depends on:** 0.1.1

**内容：** 基础 Contract（见上文 §Agent Contract v1 — 基础 Contract）。

#### Issue 0.5.1.2 — Artifact Contract
- **Labels:** `agent-kernel`, `contract` · **Depends on:** 0.5.1.1

**内容：** AuditArtifact 基类 + RiskFinding / EvidencePackage / AuditPlan / ReviewReport 具体类型（见上文 §Artifact Contract）。

**AC:**
- 所有 Agent 输出必须是 Artifact 子类型
- Pydantic 序列化/反序列化验证
- `parent_artifact_id` 溯源链完整性

#### Issue 0.5.1.3 — Event Contract
- **Labels:** `agent-kernel`, `contract` · **Depends on:** 0.5.1.1

**内容：** WorkflowEvent 定义 + 10 个事件类型（见上文 §Event Contract）。

**AC:**
- 所有 Workflow 状态变更必须有对应 Event
- WebSocket 推送 + 数据库持久化
- Event 不可变

---

### Milestone 0.5.2: Agent Runtime

#### Issue 0.5.2.1 — Agent Base + Registry
- **Labels:** `agent-kernel`, `runtime` · **Depends on:** 0.5.1.1

```python
class BaseAgent(ABC):
    name: str; version: str
    async def execute(self, request: AgentRequest) -> AgentResponse: ...
    def get_tools(self) -> list[ToolDefinition]: ...
```

#### Issue 0.5.2.2 — Workflow Engine + HITL 状态机
- **Labels:** `agent-kernel`, `workflow`, `hitl` · **Depends on:** 0.5.2.1

**状态机：**
```
CREATED → QUEUED → RUNNING → WAITING_APPROVAL → (APPROVED→RUNNING | REJECTED→回退) → COMPLETED
                       → RETRYING(≤3) → FAILED
                       → FAILED(不可恢复)
                       72h 超时 → CANCELLED
```

```python
class WorkflowEngine:
    async def create(self, graph_def) -> str: ...
    async def start/pause/resume(self, workflow_id) -> None: ...
    async def request_approval(self, workflow_id, agent_response) -> None: ...
    async def submit_decision(self, workflow_id, decision: ApprovalDecision) -> None: ...

class ApprovalDecision(BaseModel):
    workflow_id: str; reviewer_id: str
    decision: Literal["APPROVED","REJECTED","MODIFY"]
    comment: str; modifications: dict | None
```

#### Issue 0.5.2.3 — Execution Trace + Checkpoint
- **Labels:** `agent-kernel`, `trace` · **Depends on:** 0.5.2.2

**AC:** 100% 执行记录 / Checkpoint 可恢复 / Replay 引擎。

#### Issue 0.5.2.4 — Tool Registry + Permission
- **Labels:** `agent-kernel`, `tool` · **Depends on:** 0.5.2.1

```yaml
# planner_agent: [ontology_query, agent_catalog]
# knowledge_agent: [standard_search, cross_reference]
# risk_agent: [evidence_search, standard_search, calculator, ontology_query]
# evidence_agent: [client_doc_search, structured_data_query]
# reviewer_agent: [evidence_search, standard_search, grounding_checker]
```

#### Issue 0.5.2.5 — Agent Runtime Limits（v3.2 新增 — Gate 1 修正）
- **Labels:** `agent-kernel`, `runtime` · **Depends on:** 0.5.2.2

**描述：** 每个 Agent 必须有执行限制，防止无限循环导致成本不可控。

```yaml
# agent_runtime_limits.yaml（每个 Agent 可覆盖）
defaults:
  max_iterations: 3           # Agent 推理循环上限
  timeout_seconds: 300        # 单次执行超时
  retry_policy:
    max_retries: 3
    backoff: exponential      # 1s → 2s → 4s
    retry_on: [LLM_TIMEOUT, API_ERROR, NETWORK_ERROR]
  human_escalation:
    after_failed_retries: true  # 重试耗尽 → WAITING_APPROVAL
    on_high_risk: true           # HIGH/CRITICAL 风险 → 强制人工

risk_agent:
  max_iterations: 3             # Evidence 不足时最多 3 次补充检索
  require_human_after_failure: true
```

**流程（Risk Agent 受限循环）：**
```
Risk Agent (iteration 1)
    ↓
Evidence 不足 → 请求补充
    ↓
Risk Agent (iteration 2)
    ↓
仍不足 → 再次补充
    ↓
Risk Agent (iteration 3)
    ↓
3 次仍无法判断 → WAITING_APPROVAL（人工介入）
```

**AC:**
- 所有 Agent 默认 max_iterations=3, timeout=300s
- 超时/超迭代 → 自动中断 + AGENT_FAILED 事件
- 重试耗尽 → WAITING_APPROVAL（而非静默失败）

---

### Milestone 0.5.3: Evaluation Core

#### Issue 0.5.3.1 — Evaluation Runner + Metric Engine
- **Labels:** `evaluation`, `agent-kernel` · **Depends on:** 0.5.1.1

```python
class Metric(ABC):
    name: str
    async def compute(self, prediction: AgentResponse, ground_truth: dict) -> float: ...

class EvaluationRunner:
    async def run(self, agent, benchmark) -> EvaluationReport: ...

class EvaluationReport(BaseModel):
    agent_name: str; benchmark_name: str
    metrics: dict[str, float]; baseline: dict[str, float]
    passed: bool  # 低于基线 = FAIL
    experiment_id: str  # 可追踪
```

#### Issue 0.5.3.2 — Prompt Registry + Prompt Version Evaluation（v3.2 增强 — Gate 5 修正）
- **Labels:** `agent-kernel`, `prompt` · **Depends on:** 0.5.1.1

**描述：** Prompt 版本化管理 + Evaluation 绑定。AI 系统最大变化来源不是代码而是 Prompt，必须区分"是 Prompt 变好了还是 Model 升级了"。

```python
class PromptVersion(BaseModel):
    agent_name: str
    version: str                     # "v1", "v2"
    content: str                     # Markdown 模板
    variables: list[str]
    model_name: str                  # 绑定的模型
    evaluation_score: float | None   # 当前 Benchmark 分数
    baseline_score: float | None     # 上一版本分数
    improvement: float | None        # delta
    created_at: datetime
    is_active: bool
```

**AC:**
- v1/v2 版本化，禁止覆盖，禁止删除已评估版本
- 每次 Prompt 变更 → 自动触发 Evaluation → 记录 score + delta
- 新版本分数 < baseline → 不可激活为 is_active
- CI 集成：Prompt 变更 PR 必须附带 Evaluation Report

#### Issue 0.5.3.3 — Artifact Registry（v3.2 新增 — Gate 2 修正）
- **Labels:** `agent-kernel`, `artifact` · **Depends on:** 0.5.1.2

**描述：** 统一 Artifact 类型注册——后续 Service（Report Generator 等）不读自然语言，直接消费结构化 Artifact。

```python
class ArtifactRegistry:
    """所有 Artifact 类型必须注册"""
    _registry: dict[str, type[AuditArtifact]] = {}

    def register(self, artifact_class: type[AuditArtifact]) -> None: ...
    def get(self, artifact_type: str) -> type[AuditArtifact]: ...
    def list_types(self) -> list[str]: ...

# 注册的 Artifact 类型（v3.2 冻结）
# RiskFindingArtifact      → risk_finding
# EvidencePackageArtifact  → evidence_package
# KnowledgePackageArtifact → knowledge_package
# AuditPlanArtifact        → audit_plan
# ReviewReportArtifact     → review_report
# WorkpaperArtifact        → workpaper
# ReportArtifact           → audit_report
```

**AC:**
- 所有 Agent/Service 产出必须是已注册 Artifact 类型
- 未注册类型拒绝序列化
- Artifact Registry 可查询（Report Generator 按类型发现上游产出）

#### Issue 0.5.3.4 — Experiment Tracker
- **Labels:** `evaluation`, `agent-kernel` · **Depends on:** 0.5.3.1

**AC:** 记录每次 Experiment（Prompt 版本 + Model + 日期 + Metrics），支持历史对比。

---

### Milestone 0.5.4: Vertical Slice V0

#### Issue 0.5.4.1 — Mock 5 Agent 闭环
- **Labels:** `agent-kernel`, `vertical-slice` · **Depends on:** 0.5.2.2, 0.3.1, 0.3.2

**流程：** Planner → Knowledge → Risk → Evidence → Reviewer → WAITING_APPROVAL

**AC:**
- 5 Mock Agent 全部实现 Agent Contract + Artifact Contract
- 10 个 Event 类型全部触发并持久化
- HITL 状态机完整流转
- **项目第一个可演示里程碑**
- **全部 Contract 在此 Issue 完成后冻结**

---

# Epic 1A — Document Intelligence (3w)

**API Freeze: Document API v1**

### Milestone 1A.1: Upload & Processing API
- **Issue 1A.1.1** — Document Upload API (`POST /api/v1/documents` → task_id, WebSocket 推送)
- **Issue 1A.1.2** — PDF Parser (PyMuPDF → ParsedDocument)
- **Issue 1A.1.3** — OCR Service (PaddleOCR, Celery Worker)

### Milestone 1A.2: Document Understanding
- **Issue 1A.2.1** — Layout Analysis + Table Extraction
- **Issue 1A.2.2** — Semantic Chunking (按 Section/Paragraph/Table 边界)
- **Issue 1A.2.3** — Metadata Extraction + Document → PGVector Pipeline (source_type=CLIENT_DOCUMENT)

### Milestone 1A.3: Document Frontend
- **Issue 1A.3.1** — Document Center Page (拖拽上传/列表/状态/预览/WebSocket)

---

# Epic 1B — Audit Intelligence Model (3w)

**API Freeze: Knowledge API v1**

**这是 AuditFlow 与普通 RAG 的分水岭。**

---

### Milestone 1B.1: Audit Ontology（一级核心资产）

#### Issue 1B.1.1 — Ontology Schema (Graph Ready PG — Grill #4 修正)

- **Labels:** `knowledge`, `ontology`, `core` · **Depends on:** 无（并行 E1A）

```sql
-- Graph Ready 设计：以后可迁 Neo4j，MVP 用 PostgreSQL
CREATE TABLE ontology_node (
    id UUID PRIMARY KEY,
    type VARCHAR NOT NULL,       -- AuditArea | Risk | Assertion | ProcedureType | EvidenceType | Standard
    name VARCHAR NOT NULL,
    properties JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE ontology_edge (
    id UUID PRIMARY KEY,
    source_id UUID REFERENCES ontology_node(id),
    target_id UUID REFERENCES ontology_node(id),
    relation VARCHAR NOT NULL,   -- HAS_RISK | VIOLATES | ADDRESSED_BY | PRODUCES | SUPPORTS | REFERENCES
    weight FLOAT DEFAULT 1.0,
    properties JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 索引优化图遍历
CREATE INDEX idx_edge_source ON ontology_edge(source_id);
CREATE INDEX idx_edge_target ON ontology_edge(target_id);
CREATE INDEX idx_edge_relation ON ontology_edge(relation);
```

**AC:**
- 节点覆盖 ≥5 AuditArea + 6 Assertion + 5 ProcedureType + 5 EvidenceType
- 边覆盖全部 6 种 relation
- 图查询：给定 AuditArea → 返回完整推理链（Risk → Assertion → Procedure → Evidence → Standard）
- 数据初始化脚本（YAML → SQL INSERT）

#### Issue 1B.1.2 — Reasoning Chains 定义

- **Labels:** `knowledge`, `ontology`, `core` · **Depends on:** 1B.1.1

```yaml
# knowledge/ontology/reasoning_chains.yaml
revenue_recognition:
  risk: "激进收入确认"
  assertions: [Existence, Accuracy, Cutoff]
  procedures:
    - type: Inspection
      steps: ["抽查年末前15天大额销售合同", "核对发货单日期与收入确认日期"]
      evidence_required: [sales_contracts, shipping_docs]
    - type: Confirmation
      steps: ["函证前5大客户交易额"]
      evidence_required: [customer_confirmations]
  related_standards: ["IFRS 15 ¶27", "ISA 240 ¶32", "ISA 500 ¶6"]

inventory_valuation: ...
ar_impairment: ...
expense_cutoff: ...
related_party: ...
```

**AC:** ≥5 Reasoning Chain，每个含完整 Risk→Assertion→Procedure→Evidence→Standard 链路。

---

### Milestone 1B.2: Knowledge Ingestion
- **Issue 1B.2.1** — 审计准则导入 (ISA 315/330/500/240 + IFRS 15)
- **Issue 1B.2.2** — Knowledge Embedding → PGVector (source_type=AUDIT_STANDARD)

### Milestone 1B.3: Knowledge Frontend
- **Issue 1B.3.1** — Knowledge Explorer Page

---

# Epic 2 — Retrieval & Evidence Engine (3w)

**API Freeze: Search API v1 / Evidence API v1**

### Milestone 2.1: Hybrid Search
- **Issue 2.1.1** — Vector Search + Keyword Search (PGVector HNSW + tsvector)
- **Issue 2.1.2** — Hybrid Merge + Reranker (RRB + CrossEncoder)

### Milestone 2.2: Evidence System
- **Issue 2.2.1** — Evidence Collector + Citation Builder
- **Issue 2.2.2** — Grounding Checker (L3 Evaluation 就绪)

### Milestone 2.3: Evidence Frontend
- **Issue 2.3.1** — Evidence Browser + Citation Graph (React Flow)

---

# Epic 3 — Agent Core Runtime (3.5w)

**API Freeze: Agent Execution API v1**

**5 个真 Agent — Grill #3 修正（Risk 回归 Agent）**

---

### Milestone 3.1: Runtime Production
- **Issue 3.1.1** — Context Manager + Memory
- **Issue 3.1.2** — Checkpoint + Replay 生产化
- **Issue 3.1.3** — Agent Execution API (`POST /internal/agents/{name}/execute`)

---

### Milestone 3.2: Core Agents

#### Issue 3.2.1 — Planner Agent
- **Labels:** `agent`, `planner` · **Depends on:** 3.1.2, 1B.1.1

**流程：** 审计目标 → 查询 Ontology.reasoning_chains → 拆解子任务 → 生成 Agent 序列。

**产出 Artifact:** `AuditPlanArtifact`（含步骤定义 + 所需证据类型）

**Tools:** `ontology_query`, `agent_catalog`

**Evaluation L2:** Plan Completeness, Ontology Alignment

---

#### Issue 3.2.2 — Knowledge Agent
- **Labels:** `agent`, `knowledge` · **Depends on:** 2.1.2, 1B.2.2

**流程：** 检索审计准则 → 返回原文 + LLM 解读。

**产出 Artifact:** `KnowledgePackageArtifact`（含 standards + interpretations + citations）

**Tools:** `standard_search`, `cross_reference`

**Evaluation L2:** Standard Retrieval Precision@5, Citation Accuracy

---

#### Issue 3.2.3 — Risk Agent（回归 Agent）
- **Labels:** `agent`, `risk`, `core` · **Depends on:** 3.1.2, 1B.1.1

**流程（含迭代循环）：**
```
1. 接收 Evidence Package + Knowledge Package
2. 查询 Ontology 推理链 → 匹配 Risk Indicators
3. 评估 Severity + Probability
4. 证据不足？→ 请求 Evidence Agent 补充 → 返回 step 2
5. 证据充分 → 推荐审计程序 → 输出 RiskFindingArtifact
```

**产出 Artifact:** `RiskFindingArtifact`（含 area/severity/probability/indicators/procedures/reasoning）

**Tools:** `evidence_search`, `standard_search`, `calculator`, `ontology_query`

**Evaluation L2:** Risk Classification Accuracy, Severity Accuracy, Reasoning Quality

**AC:**
- 自动匹配 Ontology 推理链
- 证据不足时主动请求补充（next_action="EVIDENCE_AGENT"）
- HIGH/CRITICAL → 强制 next_action="HUMAN_REVIEW"
- 所有 Indicators 有 Citation
- **AuditFlow 的核心价值 Agent**

---

#### Issue 3.2.4 — Evidence Agent
- **Labels:** `agent`, `evidence` · **Depends on:** 2.2.1

**流程：** 接收 claims_to_verify → Hybrid Search → Evidence 封装。

**产出 Artifact:** `EvidencePackageArtifact`（含 claims + sources + coverage）

**Tools:** `client_document_search`, `structured_data_query`

**Evaluation L2:** Evidence Coverage, Citation Source Accuracy

---

#### Issue 3.2.5 — Reviewer Agent
- **Labels:** `agent`, `reviewer` · **Depends on:** 3.1.2, 2.2.2

**流程：** 审查上游所有 Artifact → 检测遗漏/幻觉/弱逻辑 → 决定 APPROVED or NEEDS_REVISION。

**产出 Artifact:** `ReviewReportArtifact`（含 review_result + issues + quality_score）

**Tools:** `evidence_search`, `standard_search`, `grounding_checker`

**Evaluation L2:** Issue Detection Rate, False Positive Rate

**AC:**
- 检测 ≥3 类问题（无引用/弱逻辑/幻觉/证据不足）
- quality_score < 阈值 → 自动退回上游 Agent
- 审计质量的最后一道 AI 防线

---

### Milestone 3.3: 最小闭环验证
- **Issue 3.3.1** — Planner→Knowledge→Risk→Evidence→Reviewer→HITL 端到端

### Milestone 3.4: Agent Frontend
- **Issue 3.4.1** — Agent Trace Viewer + Workflow Monitor (React Flow DAG + WebSocket)

---

# Epic 4 — Audit Services (2.5w)

**API Freeze: Approval API v1 / Report API v1**

**3 个 Service（确定性计算/模板渲染）— 无自主决策循环**

---

### Milestone 4.1: Audit Services
- **Issue 4.1.1** — Planning Engine (Materiality/Sampling/Procedures/Timeline)
- **Issue 4.1.2** — Workpaper Generator (模板渲染 + Citation 嵌入 → Markdown/PDF)
- **Issue 4.1.3** — Report Generator (ISA 700 结构 → 强制 next_action=HUMAN_REVIEW)

### Milestone 4.2: HITL Dashboard
- **Issue 4.2.1** — Approval Management Page (待审批列表/决策卡片/WebSocket 实时推送)

### Milestone 4.3: Audit Frontend
- **Issues 4.3.1–4.3.3** — Risk Page / Workpaper Viewer / Report Page

---

# Epic 5 — Product Experience (持续并行)

**Backend Capability First — 前端只消费已冻结 API v1**

### Milestone 5.1: Core Pages
- **Issue 5.1.1** — Main Dashboard (KPI/时间线/待审批)
- **Issue 5.1.2** — Project Management Page

### Milestone 5.2: Polish
- **Issues 5.2.1–5.2.2** — 响应式/三态覆盖/暗色模式/a11y

---

# Epic 6 — Production & Compliance (2w, 贯穿 E0-E4)

## 目标
E0.5 建立 Evaluation 骨架，各 Agent 同步追加 Metric，E6 收敛 + 安全合规。

---

### Milestone 6.1: Evaluation System
- **Issue 6.1.1** — L1 Retrieval Evaluation (Recall@K, MRR, NDCG)
- **Issue 6.1.2** — L2 Agent Evaluation (per Agent metrics)
- **Issue 6.1.3** — L3 Grounding Evaluation (Citation Precision/Recall, Unsupported Claim Rate)
- **Issue 6.1.4** — L4 Workflow Evaluation (Completion Rate, Human Intervention, Time Reduction)

---

### Milestone 6.2: Observability
- **Issue 6.2.1** — OpenTelemetry + Prometheus + Grafana (全链路 Trace + Dashboard + Alert)

---

### Milestone 6.3: Append-Only Audit Log（v3.2 升级 — Gate 6 修正）

#### Issue 6.3.1 — 三张 Append-Only 日志表 + Hash Chain

**描述：** 普通数据库 UPDATE 仍可篡改。升级为 Append-Only + hash chain（tamper-evident）。

```sql
-- Agent 执行日志（Append-Only + Hash Chain）
CREATE TABLE agent_execution_log (
    id UUID PRIMARY KEY,
    workflow_id UUID NOT NULL,
    agent_name VARCHAR NOT NULL,
    prompt_version VARCHAR NOT NULL,
    event_type VARCHAR NOT NULL,       -- AGENT_STARTED | TOOL_CALLED | AGENT_COMPLETED | AGENT_FAILED
    payload JSONB NOT NULL,            -- 完整事件 payload
    payload_hash VARCHAR NOT NULL,     -- SHA256(payload::text)
    previous_hash VARCHAR,             -- 上一条日志的 payload_hash（链式）
    created_at TIMESTAMPTZ DEFAULT now()
    -- NO UPDATE, NO DELETE — 仅 INSERT + SELECT
);

-- 审批日志（Append-Only + Hash Chain）
CREATE TABLE approval_log (
    id UUID PRIMARY KEY,
    workflow_id UUID NOT NULL,
    reviewer_id UUID NOT NULL,
    agent_name VARCHAR NOT NULL,
    decision VARCHAR NOT NULL,
    comment TEXT,
    artifact_snapshot JSONB,
    payload_hash VARCHAR NOT NULL,
    previous_hash VARCHAR,
    created_at TIMESTAMPTZ DEFAULT now()
    -- NO UPDATE, NO DELETE
);

-- 文档访问日志（Append-Only + Hash Chain）
CREATE TABLE document_access_log (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    document_id UUID NOT NULL,
    operation VARCHAR NOT NULL,
    ip_address INET,
    payload_hash VARCHAR NOT NULL,
    previous_hash VARCHAR,
    created_at TIMESTAMPTZ DEFAULT now()
    -- NO UPDATE, NO DELETE
);

-- Hash Chain 示例:
-- event1: payload_hash=sha256(e1), previous_hash=NULL
-- event2: payload_hash=sha256(e2), previous_hash=sha256(e1)
-- event3: payload_hash=sha256(e3), previous_hash=sha256(e2)
-- 验证: 重新计算 hash chain，任何篡改都会断裂
```

**AC:**
- 三张表仅 INSERT + SELECT 权限（REVOKE UPDATE, DELETE）
- `previous_hash` 形成链式校验
- 提供 `verify_hash_chain(workflow_id)` 函数检测篡改
- 所有 Agent 执行/审批/文档访问自动写入
- 审批日志含完整 Artifact 快照（审批时的状态不可丢失）

---

### Milestone 6.4: Security
- **Issue 6.4.1** — RBAC (Admin/Auditor/Reviewer/Viewer)
- **Issue 6.4.2** — Tenant Data Isolation (PG RLS + 所有查询自动注入 firm_id/engagement_id)
- **Issue 6.4.3** — Secret Management (所有 Key → 环境变量，禁止硬编码)

---

### Milestone 6.5: Production Deployment
- **Issues 6.5.1–6.5.3** — Prod Docker Compose / PostgreSQL 每日备份(90天) / Locust 性能测试

---

# Epic 7 — Benchmark Expansion (1.5w, 与 E1A 起并行)

## 目标
E0.5 建 Evaluation 能力，E7 建业务数据资产。

**20 Cases × 7 领域（Grill #2 修正 — Risk Matrix Coverage）**

---

### Milestone 7.1: Benchmark Construction

#### Issue 7.1.1 — Benchmark Schema

```yaml
# benchmark/{scenario}/benchmark.yaml
name: revenue_audit_v1
scenario: Revenue Recognition Audit
cases:
  - id: rev_001
    description: "激进收入确认 — 收入增长 3x 行业均值"
    documents: [annual_report_sample.pdf, sales_contract_sample.pdf]
    input:
      financial_data: {revenue_growth: "45%", industry_avg: "10%", receivable_days: 120}
    expected:
      risks:
        - area: Revenue Recognition
          severity: HIGH
          indicators: ["revenue_growth > 3x avg", "receivable_days increased >30% YoY"]
      assertions: [Existence, Accuracy, Cutoff]
      procedures:
        - type: Inspection, target: [sales_contracts, shipping_docs]
        - type: Confirmation, target: [top5_customers]
      evidence_min_count: 3
      related_standards: ["IFRS 15 ¶27", "ISA 240 ¶32"]
    evaluation:
      primary_metric: risk_classification_accuracy
      secondary_metrics: [citation_completeness, procedure_coverage, reasoning_quality]
```

#### Issue 7.1.2 — 20 Cases × 7 领域

| 领域 | Cases | 核心风险 |
|------|-------|----------|
| Revenue Recognition | 5 | 激进确认、截止性、虚构收入、捆绑合同、可变对价 |
| AR Impairment | 3 | 坏账准备不足、账龄分类错误、虚构应收 |
| Inventory Valuation | 3 | 存货跌价、数量差异、成本核算错误 |
| Expense Cutoff | 3 | 费用资本化、跨期费用、关联方交易 |
| Fixed Asset | 2 | 折旧政策变更、减值测试缺失 |
| Control Testing | 2 | 职责分离缺失、审批绕过 |
| Fraud Risk | 2 | 管理层凌驾、收入舞弊 |

**AC:**
- 每个 Case 含模拟文档 + input + expected output
- 覆盖 ≥5 个 Reasoning Chain（E1B）
- 格式符合 EvaluationRunner 输入规范

#### Issue 7.1.3 — Baseline Evaluation Report

**AC:**
- Baseline Comparison 记录（GPT-4 Direct vs Naive RAG vs AuditFlow E3）
- CI 集成：新 Prompt 版本分数 < Baseline → PR Blocked

---

# Issue 统计 (v3.1)

| Epic | Milestones | Issues | 估算 | 并行 |
|------|-----------|--------|------|------|
| E0 Foundation | 3 | 7 | 1w | — |
| E0.5 Agent Kernel + Eval Core | 4 | 13 | 1.5w | — |
| E1A Document Intelligence | 3 | 7 | 3w | E1B |
| E1B Audit Intelligence Model | 3 | 5 | 3w | E1A |
| E2 Retrieval & Evidence | 3 | 5 | 3w | — |
| E3 Agent Core Runtime | 4 | 9 | 3.5w | — |
| E4 Audit Services | 3 | 7 | 2.5w | — |
| E5 Product Experience | 2 | 4 | 持续 | E1A→E4 |
| E6 Production & Compliance | 5 | 12 | 2w | E0→E4 |
| E7 Benchmark Expansion | 1 | 3 | 1.5w | E1A |
| **总计** | **31** | **74** | **~18w MVP** | |

---

# API Freeze 时机

| Epic 完成 | Freeze | 前端可用 |
|-----------|--------|----------|
| E0.5 | Agent Contract v1 (+ Artifact + Event) | — |
| E1A | `POST/GET /api/v1/documents/*` | Document Center |
| E1B | `POST/GET /api/v1/knowledge/*` | Knowledge Explorer |
| E2 | `POST /api/v1/search`, `GET /api/v1/evidence/*` | Evidence Browser |
| E3 | `POST /internal/agents/{name}/execute`, `WS /api/v1/ws/workflows/{id}` | Agent Trace + Workflow Monitor |
| E4 | `POST /api/v1/approvals`, `GET /api/v1/reports/*` | Approval Dashboard + Risk/Workpaper/Report Pages |

---

# 关键风险（优先级排序）

| # | 风险 | 缓解 |
|---|------|------|
| 1 | **Ontology 质量不足** → 系统成为"审计版 RAG" | E1B 至少 5 个完整 Reasoning Chain |
| 2 | **Risk Agent 迭代循环复杂** → 最可能超支 | Runtime Limits (max_iterations=3) + human escalation |
| 3 | **Benchmark 数据标注质量** → 垃圾进垃圾出 | 每个 Case 必须人工审核 expected output |
| 4 | **Audit Log 可篡改** → 审计合规风险 | Append-Only hash chain (tamper-evident) |
| 5 | **Prompt 变更不可追踪** → 无法归因优化 | Prompt Version Evaluation（Prompt vs Model 分离） |
| 6 | **个人开发 18 周偏乐观** | MVP Beta，Production 预估 22-26 周 |

