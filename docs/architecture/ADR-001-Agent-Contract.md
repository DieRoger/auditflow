# ADR-001：Agent Contract v1.0 — 标准化多 Agent I/O 协议

> **状态：** 已接受（Architecture Baseline v1.0）  
> **日期：** 2026-07-26  
> **冻结里程碑：** E0.5 MileStone 0.5.4  
> **关联文档：** `auditflow/docs/api/agent-contract.md`、`auditflow/docs/api/artifact-schema.md`

---

## 1. 背景 (Context)

AuditFlow 是一个多 Agent 审计平台，由 5 个 Agent（Planner、Knowledge、Risk、Evidence、Reviewer）和 3 个 Service（Planning Engine、Workpaper Generator、Report Generator）组成。在系统设计之初，我们面临一个关键的架构问题：

> 如果没有标准化的 I/O 契约，每个 Agent 将定义自己的输入/输出格式，导致 Workflow Engine 无法通用路由、Evaluation Runner 无法统一测试、任何 Agent 变更都会引发下游级联改动。

传统 AI Agent 系统把"Agent 间通信"视为 impl detail —— 各个 Agent 直接在代码中互相调用。但在 AuditFlow 这种高合规性要求的审计场景下，这完全不可接受：**每一条推理判断都必须可追溯，每一次 Agent 调用都必须是可替换的"黑盒"**，Workflow Engine 不应知道 Agent 内部实现。

因此，在 E0.5 里程碑完成时，我们冻结了 Agent Contract v1.0 —— 任何 Agent 或 Service 的输入、输出、中间 Artifact 都服从同一套 Pydantic 模型。

---

## 2. 决策 (Decision)

所有 Agent 和 Service **必须**实现以下五份契约（于 E0.5 锁定）：

### 2.1 Contract 1：AgentRequest — 统一请求入口

```python
from pydantic import BaseModel, Field
from typing import Any
from datetime import datetime


class AgentRequest(BaseModel):
    """进入任意 Agent 的统一请求载荷。

    所有 Agent 通过此模型接收上游调用，Workflow Engine 负责组装。
    """

    # ── 全局标识 ──────────────────────────────────────────
    workflow_id: str = Field(
        ...,
        description="Workflow 全局唯一 ID，贯穿全链路。"
    )
    project_id: str = Field(
        ...,
        description="审计项目 ID，对应一个审计委托 (Engagement)。"
    )
    task_id: str = Field(
        ...,
        description="当前子任务 ID，在同一个 Workflow 内唯一。"
    )

    # ── 多租户标识 ──────────────────────────────────────
    firm_id: str = Field(
        ...,
        description="审计事务所 ID (Tenant)。数据隔离一级键。"
    )
    client_id: str = Field(
        ...,
        description="被审计客户 ID。数据隔离二级键。"
    )
    engagement_id: str = Field(
        ...,
        description="审计年度/委托 ID。数据隔离三级键。"
    )

    # ── 上下文 ──────────────────────────────────────────
    context: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Workflow 共享上下文，按 agent_name 索引上游 Artifact 引用。"
            "示例: {'planner': AuditPlanArtifact, 'knowledge': KnowledgePackageArtifact}"
        ),
    )
    inputs: dict[str, Any] = Field(
        default_factory=dict,
        description="本次任务的输入数据，内容取决于 Agent 类型。"
    )
    memory: dict[str, Any] = Field(
        default_factory=dict,
        description="跨轮次记忆，携带上一次迭代的状态。"
    )

    # ── 配置覆写 ────────────────────────────────────────
    runtime_limits: "AgentRuntimeLimits | None" = Field(
        default=None,
        description="运行时限制覆写。None 表示使用 Agent 默认配置。"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="请求创建时间 (UTC)。"
    )
```

### 2.2 Contract 2：AgentResponse — 统一响应格式

```python
from enum import Enum
from pydantic import BaseModel, Field
from typing import Any
from datetime import datetime


class AgentStatus(str, Enum):
    """Agent 执行终止状态。"""
    SUCCESS = "SUCCESS"          # 执行成功，result 含预期产出
    PARTIAL = "PARTIAL"          # 部分成功，核心输出已生成但部分子步骤未完成
    FAILED = "FAILED"            # 执行失败，无法产生有效产出
    NEEDS_HUMAN = "NEEDS_HUMAN"  # 推理完成但需人工审核（这是正常状态，非异常）


class AgentResponse(BaseModel):
    """Agent 统一响应。无论何种 status，所有字段均存在（非 None）。"""

    # ── 标识 ────────────────────────────────────────────
    workflow_id: str = Field(..., description="对应请求的 workflow_id。")
    task_id: str = Field(..., description="对应请求的 task_id。")
    agent_name: str = Field(..., description="产出 Agent 名称。")

    # ── 执行结果 ────────────────────────────────────────
    status: AgentStatus = Field(..., description="执行终止状态。")
    result: dict[str, Any] = Field(
        default_factory=dict,
        description="结构化执行结果。建议包含 artifact_id 引用。"
    )
    citations: list["Citation"] = Field(
        default_factory=list,
        description="本次推理引用的所有来源。"
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Agent 对自身输出的置信度 (0.0–1.0)。"
    )
    metrics: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "执行指标。标准键: duration_ms, tokens, cost, iterations, tool_calls。"
        ),
    )
    next_action: str = Field(
        default="",
        description="建议的下一步动作，供 WorkflowEngine 参考。"
    )

    # ── 错误 ────────────────────────────────────────────
    error: "AgentError | None" = Field(
        default=None,
        description="status=FAILED 时的结构化错误；其他状态为 None。"
    )

    # ── 时间戳 ──────────────────────────────────────────
    started_at: datetime | None = Field(default=None)
    completed_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True
```

### 2.3 Contract 3：Citation — 可追溯引用

```python
from pydantic import BaseModel, Field
from typing import Any
from datetime import datetime
from enum import Enum


class CitationSourceType(str, Enum):
    CLIENT_DOCUMENT = "CLIENT_DOCUMENT"
    AUDIT_STANDARD = "AUDIT_STANDARD"
    WORKPAPER = "WORKPAPER"
    RISK_CASE = "RISK_CASE"
    EXTERNAL_REGULATION = "EXTERNAL_REGULATION"


class Citation(BaseModel):
    """一条结构化引用——每一条推理判断必须指向具体证据来源。"""

    citation_id: str = Field(
        ...,
        description="引用全局唯一 ID，格式 'cit_{uuid_short}'。"
    )
    source_type: CitationSourceType = Field(
        ...,
        description="来源类型。"
    )
    source_id: str = Field(
        ...,
        description="来源标识：文档 ID / 标准段落号。"
    )
    source_name: str = Field(
        ...,
        description="人类可读来源名称，如 'ISA 315 ¶27'。"
    )

    # ── 定位 ────────────────────────────────────────────
    chunk_id: str | None = Field(
        default=None,
        description="检索 Chunk ID，用于前端高亮定位。"
    )
    page_number: int | None = Field(
        default=None,
        description="页码 (1-based)。"
    )
    section: str | None = Field(
        default=None,
        description="文档节标题或段落编号。"
    )
    text_snippet: str = Field(
        ...,
        description="引用文本片段 (≤500 字符)。"
    )

    # ── 置信度 ──────────────────────────────────────────
    relevance_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="检索/相关性评分。"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Agent 对此引用支撑力度的置信度。"
    )

    # ── 元数据 ──────────────────────────────────────────
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### 2.4 Contract 4：AuditArtifact — 结构化产出基类

```python
from pydantic import BaseModel, Field, field_validator
from typing import Any
from datetime import datetime
from uuid import uuid4


class AuditArtifact(BaseModel):
    """所有 Agent/Service 产出的抽象基类。禁止直接实例化——必须使用子类型。"""

    artifact_type: str = Field(
        ...,
        description="Artifact 类型标识符，由子类 Literal 约束。"
    )
    artifact_id: str = Field(
        default_factory=lambda: f"art-{uuid4().hex[:16]}",
        description="全局唯一 Artifact ID。"
    )
    created_by: str = Field(
        ...,
        description="产出者名称 (planner/knowledge_agent/risk_agent/evidence_agent/reviewer_agent)。"
    )
    schema_version: str = Field(
        default="v1",
        description="Schema 版本号，用于向前兼容。"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="创建时间 (UTC)。"
    )
    workflow_id: str = Field(..., description="所属 Workflow ID。")
    project_id: str = Field(..., description="所属审计项目 ID。")
    content: dict[str, Any] = Field(
        ...,
        description="结构化内容。子类通过范型约束为具体 Content Model。"
    )
    citations: list[Citation] = Field(
        ...,
        description="与此 Artifact 关联的引用列表（不可为空）。"
    )
    parent_artifact_id: str | None = Field(
        default=None,
        description="上游 Artifact ID——溯源链核心字段。根节点 (AuditPlanArtifact) 为 None。"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="扩展元数据 (耗时、token 用量、模型版本等)。"
    )

    @field_validator("citations")
    @classmethod
    def citations_must_not_be_empty(cls, v: list[Citation]) -> list[Citation]:
        if len(v) == 0:
            raise ValueError("Artifact.citations 不能为空")
        return v

    class Config:
        extra = "forbid"
```

> 当前冻结的 7 种 Artifact 子类型：`AuditPlanArtifact`、`KnowledgePackageArtifact`、`RiskFindingArtifact`、`EvidencePackageArtifact`、`ReviewReportArtifact`、`WorkpaperArtifact`、`ReportArtifact`。完整定义见 `auditflow/docs/api/artifact-schema.md`。

### 2.5 Contract 5：Agent Runtime Limits — 运行时限制

```python
from pydantic import BaseModel, Field


class AgentRuntimeLimits(BaseModel):
    """Agent 运行时安全围栏配置。"""

    class HumanEscalation(BaseModel):
        after_failed_retries: bool = Field(
            default=True,
            description="所有重试耗尽后强制升级到人工。"
        )
        on_high_risk: bool = Field(
            default=False,
            description="遇到 HIGH/CRITICAL 风险时立即升级。"
        )

    max_iterations: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Agent 推理循环最大次数。超过视为 FAILED。"
    )
    timeout_seconds: int = Field(
        default=300,
        ge=30,
        le=900,
        description="单次 execute() 最大执行时间 (秒)。"
    )
    retry_max_attempts: int = Field(
        default=3,
        ge=0,
        le=5,
        description="失败后最大重试次数。"
    )
    retry_backoff_base_seconds: float = Field(
        default=2.0,
        description="指数退避基数 (秒)。第 n 次重试延迟 = base × 2^(n-1)。"
    )
    retry_backoff_max_seconds: float = Field(
        default=60.0,
        description="单次退避上限 (秒)。"
    )
    human_escalation: HumanEscalation = Field(
        default_factory=HumanEscalation,
        description="人工升级策略。"
    )
```

**重试策略：**

| 重试次数 | 延迟 (base=2s) | 说明 |
|----------|----------------|------|
| 1 | 2s | 第 1 次重试 |
| 2 | 4s | 第 2 次重试 |
| 3 | 8s | 最后一次重试，之后 → `NEEDS_HUMAN` |

> 超时检测由 `WorkflowEngine` 的 asyncio 超时包装器执行，`Agent.execute()` 内部也可主动检查 `timeout_seconds`。

---

## 3. 影响 (Consequences)

### 3.1 正面影响

| 影响 | 说明 |
|------|------|
| **统一路由** | Workflow Engine 可路由**任何** Agent，无需知道内部实现——只需构造 `AgentRequest` 并消费 `AgentResponse`。 |
| **统一测试** | Evaluation Runner 可用同一套 `AgentRequest` / `AgentResponse` 接口测试所有 Agent，无需为每个 Agent 写专门的测试适配器。 |
| **可替换性** | 任何一个 Agent 的实现可以被替换（如切换底层 LLM、替换检索策略），只要遵守 contract，其余系统无感。 |
| **可追溯性** | 所有 Agent 产出通过 `parent_artifact_id` 构成完整溯源链；每一条判断通过 `citations` 指向具体证据片段。 |
| **安全围栏** | `AgentRuntimeLimits` 防止 Agent 无限循环（max_iterations=3）、无限等待（timeout=300s），并用指数退避重试 + 人工兜底保证系统韧性。 |

### 3.2 约束

| 约束 | 说明 |
|------|------|
| **Pydantic 强制** | 所有 Agent 输入/输出必须在 Pydantic 校验层通过，任何偏离都会立即被拒绝——开发时必须严格遵守字段名、类型、枚举值。 |
| **禁止自由文本输出** | 所有 Agent 产出必须是 `AuditArtifact` 子类型，不得返回非结构化自然语言文本块。这要求每个 Agent 在 Prompt 工程上做额外工作以产出结构化 JSON。 |
| **citations 不可为空** | 即使是 Planner（它通常不直接引用证据），也必须至少声明一条来源 Citation（如 Ontology 推理链），不加区分地允许空引用会导致下游审计师无法追溯。 |
| **冻结后不可随意修改** | E0.5 后 Contract 冻结为 v1.0.0。新增字段只能通过 MINOR bump (v1.1.0) 且必须是 Optional；删除/重命名字段需要 MAJOR bump (v2.0.0) 并附带 Migration Guide。 |

### 3.3 覆盖范围

受本 ADR 约束的组件：

```
┌────────────────────────────────────────────────────────────┐
│                    Agent Contract v1.0                      │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Planner  │  │Knowledge │  │   Risk   │  │ Evidence │   │
│  │  Agent   │  │  Agent   │  │  Agent   │  │  Agent   │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │              │              │              │        │
│  ┌────┴─────┐                                           │   │
│  │ Reviewer │                                           │   │
│  │  Agent   │                                           │   │
│  └────┬─────┘                                           │   │
│       │                                                   │   │
│  ┌────┴──────────┐  ┌──────────────┐  ┌──────────────┐   │   │
│  │   Planning    │  │  Workpaper   │  │   Report     │   │   │
│  │   Engine      │  │  Generator   │  │  Generator   │   │   │
│  │  (Service)    │  │  (Service)   │  │  (Service)   │   │   │
│  └───────────────┘  └──────────────┘  └──────────────┘   │   │
│                                                             │
│  共同契约：                                                 │
│  AgentRequest  →  AgentResponse  →  AuditArtifact          │
│  Citation  →  AgentRuntimeLimits                           │
└────────────────────────────────────────────────────────────┘
```

---

## 4. 附录：完整类型枚举

### 4.1 AgentStatus

```python
class AgentStatus(str, Enum):
    SUCCESS     = "SUCCESS"
    PARTIAL     = "PARTIAL"
    FAILED      = "FAILED"
    NEEDS_HUMAN = "NEEDS_HUMAN"
```

### 4.2 CitationSourceType

```python
class CitationSourceType(str, Enum):
    CLIENT_DOCUMENT     = "CLIENT_DOCUMENT"
    AUDIT_STANDARD      = "AUDIT_STANDARD"
    WORKPAPER           = "WORKPAPER"
    RISK_CASE           = "RISK_CASE"
    EXTERNAL_REGULATION = "EXTERNAL_REGULATION"
```

### 4.3 ArtifactType (7 种冻结类型)

```python
class ArtifactType(str, Enum):
    RISK_FINDING      = "risk_finding"
    EVIDENCE_PACKAGE  = "evidence_package"
    KNOWLEDGE_PACKAGE = "knowledge_package"
    AUDIT_PLAN        = "audit_plan"
    REVIEW_REPORT     = "review_report"
    WORKPAPER         = "workpaper"
    REPORT            = "report"
```

### 4.4 溯源链结构

```
AuditPlanArtifact          (parent_artifact_id = None)   ← 根节点
    │
    ▼
KnowledgePackageArtifact   (parent = AuditPlanArtifact)
    │
    ▼
RiskFindingArtifact        (parent = KnowledgePackageArtifact)
    │
    ▼
EvidencePackageArtifact    (parent = RiskFindingArtifact)
    │
    ▼
ReviewReportArtifact       (parent = EvidencePackageArtifact)
    │
    ▼
WorkpaperArtifact          (parent = ReviewReportArtifact)  ← Service 产出
    │
    ▼
ReportArtifact             (parent = WorkpaperArtifact)     ← Service 产出，强制 HITL
```

---

> **文档维护者：** AuditFlow Architecture Team  
> **最后更新：** 2026-07-26  
> **下次修订：** 若 Agent 职责变更导致 Content Schema 调整，需升级 `schema_version` → `v2` 并相应创建 ADR-002。
