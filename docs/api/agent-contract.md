# AuditFlow Agent Contract v1.0

> **版本：** v1.0（于 E0.5 冻结）  
> **冻结日期：** E0.5 MileStone 0.5.4 完成时锁定  
> **适用范围：** 所有 Agent 与 Service 均须实现本契约  
> **语言约定：** 中文说明，英文标识符（类名、字段名、方法名、类型名）

---

## 目录

1. [概述](#1-概述)
2. [AgentRequest — 请求模型](#2-agentrequest--请求模型)
3. [AgentResponse — 响应模型](#3-agentresponse--响应模型)
4. [Citation — 引用模型](#4-citation--引用模型)
5. [AgentError — 错误响应模型](#5-agenterror--错误响应模型)
6. [Agent Runtime Limits — 运行时限制配置](#6-agent-runtime-limits--运行时限制配置)
7. [BaseAgent — 抽象基类](#7-baseagent--抽象基类)
8. [AgentRegistry — Agent 注册中心接口](#8-agentregistry--agent-注册中心接口)
9. [ToolDefinition 与 ToolRegistry — 工具定义与注册接口](#9-tooldefinition-与-toolregistry--工具定义与注册接口)
10. [使用示例：Planner Agent 如何实现本契约](#10-使用示例planner-agent-如何实现本契约)
11. [附录：契约版本兼容性规则](#11-附录契约版本兼容性规则)

---

## 1. 概述

### 1.1 契约定位

本契约是 AuditFlow 系统中**所有 Agent 与 Service 之间通信的唯一标准**。任何 Agent 或 Service 的输入/输出必须符合本契约定义的 Pydantic 模型，否则将在类型校验阶段被拒绝。

### 1.2 核心原则

| 原则 | 说明 |
|------|------|
| **结构化输出** | 所有 Agent 产出必须是 `AuditArtifact` 的子类型，禁止返回非结构化自然语言文本 |
| **可追溯** | 每个产出通过 `parent_artifact_id` 形成溯源链，每一判断通过 `citations` 引用证据源 |
| **可观测** | 每一次状态变更产生对应的 `WorkflowEvent`，不可变、持久化、可 WebSocket 推送 |
| **安全围栏** | 每个 Agent 必须遵守 `AgentRuntimeLimits` 限制，超限自动中断 |
| **人工兜底** | `NEEDS_HUMAN` / `WAITING_APPROVAL` 是正常状态，不是异常；高风险判断强制人工 |

### 1.3 Agent vs Service 分类

| 组件 | 类型 | 自主决策循环 |
|------|------|-------------|
| **Planner** | Agent ✅ | 任务拆解策略 — 基于 Ontology 推理链选择子任务序列 |
| **Knowledge** | Agent ✅ | 检索策略选择 — 决定用 Vector/Keyword/Hybrid，如何过滤 |
| **Risk** | Agent ✅ | 风险等级判断 + 程序推荐 + 证据不足时迭代补充 |
| **Evidence** | Agent ✅ | 证据相关度选择 — 多个候选 Chunk 中筛选最相关的 |
| **Reviewer** | Agent ✅ | 质疑/退回/通过判断 — 是否要求上游重新执行 |
| Planning Engine | Service | 公式计算（Materiality/Sampling）+ 模板 |
| Workpaper Generator | Service | 模板渲染 + Citation 嵌入 |
| Report Generator | Service | 模板渲染 + 格式转换 |

> **判定规则：** 确定性计算 / 模板渲染 / 规则匹配 = Service。包含"证据不足→要求补充→重新评估"迭代循环的 = Agent。

---

## 2. AgentRequest — 请求模型

进入 Agent 的统一入口。所有 Agent 必须通过此模型接收上游调用。

```python
from pydantic import BaseModel, Field
from typing import Any
from datetime import datetime


class AgentRequest(BaseModel):
    """进入任意 Agent 的统一请求载荷。

    字段分为三类：
    - 标识类 (identity)：贯穿 Workflow 全生命周期的追踪 ID。
    - 上下文类 (context)：上游 Agent 产出的结构化 Artifact，以及当前 Workflow 共享状态。
    - 配置类 (config)：Agent 特定的运行时配置覆写。
    """

    # ── 标识类 ──────────────────────────────────────────
    workflow_id: str = Field(
        ...,
        description="Workflow 全局唯一 ID，由 WorkflowEngine 在创建时分配，贯穿全链路。",
    )
    task_id: str = Field(
        ...,
        description="当前子任务 ID，在同一 Workflow 中唯一。Planner 拆分后分配给每个子任务。",
    )
    project_id: str = Field(
        ...,
        description="审计项目 ID，对应一个审计委托（Engagement）。",
    )

    # ── 多租户标识 ──────────────────────────────────────
    firm_id: str = Field(
        ...,
        description="审计事务所 ID（Tenant）。数据隔离的一级键。",
    )
    client_id: str = Field(
        ...,
        description="被审计客户 ID。数据隔离的二级键。",
    )
    engagement_id: str = Field(
        ...,
        description="审计年度/委托 ID。数据隔离的三级键。",
    )

    # ── 上下文类 ─────────────────────────────────────────
    context: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Workflow 当前共享上下文。由 WorkflowEngine 在 Agent 间传递，"
            "包含上游 Agent 产出的 artifact 引用（按 agent_name 索引）。"
            "示例: {'planner': AuditPlanArtifact, 'knowledge': KnowledgePackageArtifact}"
        ),
    )
    inputs: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "本次任务的具体输入数据。内容取决于 Agent 类型。"
            "示例 for Risk Agent: {'area': 'revenue_recognition', "
            "'document_ids': ['doc_001', 'doc_002']}"
        ),
    )
    memory: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Agent 跨轮次记忆。在同一 Workflow 的多次迭代中携带上一次的状态。"
            "示例: {'iteration': 2, 'previous_findings': [...]}"
        ),
    )

    # ── 配置覆写（可选）────────────────────────────────
    runtime_limits: "AgentRuntimeLimits | None" = Field(
        default=None,
        description="本次执行特定的运行时限制覆写。None 表示使用 Agent 默认配置。",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="请求创建时间。用于超时计算和审计日志。",
    )
```

---

## 3. AgentResponse — 响应模型

Agent 执行完毕后的统一输出。

```python
from enum import Enum
from typing import Literal
from datetime import datetime


class AgentStatus(str, Enum):
    """Agent 执行终止状态。"""

    SUCCESS = "SUCCESS"
    # 执行成功，result 中包含预期的结构化产出。

    PARTIAL = "PARTIAL"
    # 部分成功：核心输出已生成，但部分子步骤未能完成。
    # 示例：Risk Agent 识别了 3/5 个风险领域，剩余 2 个因证据不足标记为 uncertain。

    FAILED = "FAILED"
    # 执行失败，无法产生有效产出。详见 error 字段。
    # 可能原因：LLM 不可达、输入数据损坏、内部逻辑错误。

    NEEDS_HUMAN = "NEEDS_HUMAN"
    # Agent 完成推理但需要人工审核或决策才能继续。
    # 示例：Risk Agent 判断某风险为 CRITICAL → 触发强制人工审批。
    # 这是正常状态，不是异常。WorkflowEngine 收到后进入 WAITING_APPROVAL。


class AgentResponse(BaseModel):
    """Agent 的统一响应格式。

    无论 SUCCESS / PARTIAL / FAILED / NEEDS_HUMAN，
    所有字段都存在（非 None），只是部分字段在特定状态下有明确语义。
    """

    # ── 标识 ────────────────────────────────────────────
    workflow_id: str = Field(
        ...,
        description="对应请求的 workflow_id。",
    )
    task_id: str = Field(
        ...,
        description="对应请求的 task_id。",
    )
    agent_name: str = Field(
        ...,
        description="产生此响应的 Agent 名称，如 'planner' / 'risk' / 'reviewer'。",
    )

    # ── 执行结果 ─────────────────────────────────────────
    status: AgentStatus = Field(
        ...,
        description="执行终止状态。",
    )
    result: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "结构化执行结果。对于 SUCCESS/PARTIAL，包含 agent 产出的核心数据。"
            "对于 FAILED，包含错误上下文。"
            "强烈建议 result 中包含 artifact_id 引用，而非完整 artifact 内联。"
        ),
    )
    citations: list["Citation"] = Field(
        default_factory=list,
        description="本次推理中引用的所有来源。即使 result 为空，citations 也可能非空（证据搜索记录）。",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description=(
            "Agent 对自身输出的置信度 (0.0–1.0)。"
            "SUCCESS 时通常 ≥ 0.7；PARTIAL 时通常 0.3–0.7；FAILED 时为 0.0。"
            "Reviewer Agent 可据此决定是否退回。"
        ),
    )
    next_action: str = Field(
        default="",
        description=(
            "建议的下一步动作，供 Planner 或 WorkflowEngine 参考。"
            "示例: 'proceed_to_evidence_collection' / 'request_additional_documents' / "
            "'escalate_to_reviewer' / ''"
        ),
    )

    # ── 性能与诊断 ──────────────────────────────────────
    metrics: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "执行指标。标准键："
            " 'duration_ms' — 执行耗时（毫秒）；"
            " 'tokens' — LLM Token 消耗（含 prompt + completion）；"
            " 'cost' — 预估美元成本；"
            " 'iterations' — Agent 推理循环次数；"
            " 'tool_calls' — 工具调用总次数。"
        ),
    )
    error: "AgentError | None" = Field(
        default=None,
        description="当 status=FAILED 时，包含结构化错误信息。其他状态为 None。",
    )

    # ── 时间戳 ──────────────────────────────────────────
    started_at: datetime | None = Field(
        default=None,
        description="Agent 开始执行的时间。",
    )
    completed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Agent 完成执行的时间。",
    )

    class Config:
        use_enum_values = True
```

---

## 4. Citation — 引用模型

每一条推理判断必须指向具体证据来源。Citation 是 AuditArtifact 和 AgentResponse 的组成部分。

```python
from enum import Enum
from datetime import datetime


class CitationSourceType(str, Enum):
    """Citation 来源类型。"""
    CLIENT_DOCUMENT = "CLIENT_DOCUMENT"
    # 被审计客户提供的文档（财报、合同、发票等）。

    AUDIT_STANDARD = "AUDIT_STANDARD"
    # 审计准则（ISA 315/330/500/240 等）。

    WORKPAPER = "WORKPAPER"
    # 工作底稿中的历史发现。

    RISK_CASE = "RISK_CASE"
    # 历史风险案例库。

    EXTERNAL_REGULATION = "EXTERNAL_REGULATION"
    # 外部法规（IFRS 15、SEC 规则等）。


class Citation(BaseModel):
    """一条结构化引用。

    每个 Citation 精确指向一个证据片段，支持前端高亮定位和审计追溯。
    """

    citation_id: str = Field(
        ...,
        description="引用全局唯一 ID。格式: 'cit_{uuid_short}'。",
    )
    source_type: CitationSourceType = Field(
        ...,
        description="来源类型。",
    )
    source_id: str = Field(
        ...,
        description="来源文档/标准 ID。如 'doc_001' 或 'ISA_315_R21'。",
    )
    source_name: str = Field(
        ...,
        description="来源人类可读名称。如 'FY2024 审计报告 第21页' 或 'ISA 315 第21段'。",
    )

    # ── 定位 ────────────────────────────────────────────
    chunk_id: str | None = Field(
        default=None,
        description="检索到的 Chunk ID。用于后端定位，前端通过此 ID 获取高亮坐标。",
    )
    page_number: int | None = Field(
        default=None,
        description="页码（如适用）。1-based。",
    )
    section: str | None = Field(
        default=None,
        description="文档节标题或段落编号。如 '2.3 Revenue Recognition Policy'。",
    )
    text_snippet: str = Field(
        ...,
        description="引用文本片段（≤500 字符）。前端展示用，支持高亮。",
    )

    # ── 相关性 ──────────────────────────────────────────
    relevance_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="检索/相关性评分 (0.0–1.0)。用于排序和过滤低质量引用。",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Agent 对此引用支撑力度的置信度 (0.0–1.0)。",
    )

    # ── 元数据 ──────────────────────────────────────────
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="扩展元数据。如 {'standard_paragraph': 'R21', 'ifrs_ref': 'IFRS15.47'}。",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="引用创建时间。",
    )
```

---

## 5. AgentError — 错误响应模型

当 `AgentResponse.status == FAILED` 时，必须提供结构化的错误信息。

```python
from enum import Enum


class ErrorType(str, Enum):
    """Agent 错误分类。"""

    LLM_TIMEOUT = "LLM_TIMEOUT"
    # LLM 调用超时。

    LLM_RATE_LIMIT = "LLM_RATE_LIMIT"
    # LLM 速率限制。

    LLM_CONTENT_FILTER = "LLM_CONTENT_FILTER"
    # LLM 内容安全过滤。

    API_ERROR = "API_ERROR"
    # 外部 API 调用错误。

    NETWORK_ERROR = "NETWORK_ERROR"
    # 网络不可达。

    TOOL_ERROR = "TOOL_ERROR"
    # 工具执行内部错误。

    VALIDATION_ERROR = "VALIDATION_ERROR"
    # 输入数据不符合 Schema。

    INTERNAL_ERROR = "INTERNAL_ERROR"
    # Agent 内部未预期错误。

    ITERATION_EXCEEDED = "ITERATION_EXCEEDED"
    # 推理循环次数超过 max_iterations。

    TIMEOUT_EXCEEDED = "TIMEOUT_EXCEEDED"
    # 执行时间超过 timeout_seconds。

    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    # 证据不足以支撑判断（Risk Agent 特有）。


class AgentError(BaseModel):
    """Agent 执行失败的结构化错误信息。"""

    error_type: ErrorType = Field(
        ...,
        description="错误分类。",
    )
    message: str = Field(
        ...,
        description="人类可读的错误描述。用于日志和前端展示。",
    )
    detail: dict[str, Any] | None = Field(
        default=None,
        description=(
            "机器可读的错误详情。"
            "示例: {'provider': 'openai', 'model': 'gpt-4', 'status_code': 429}"
        ),
    )

    # ── 恢复信息 ─────────────────────────────────────────
    recoverable: bool = Field(
        default=True,
        description="是否可重试恢复。True 表示 WorkflowEngine 可触发 RETRYING。",
    )
    retry_count: int = Field(
        default=0,
        description="已重试次数。首次失败时值为 0。",
    )
    retry_after_seconds: int | None = Field(
        default=None,
        description="建议的重试等待秒数。LLM_RATE_LIMIT 时来自 Retry-After 头。",
    )

    # ── 人工升级 ─────────────────────────────────────────
    escalate_to_human: bool = Field(
        default=False,
        description=(
            "是否应升级为人工介入。"
            "True 的条件：不可恢复错误，或重试已耗尽。"
            "WorkflowEngine 收到后进入 WAITING_APPROVAL。"
        ),
    )
    escalation_reason: str | None = Field(
        default=None,
        description="人工升级原因说明。仅在 escalate_to_human=True 时有意义。",
    )

    # ── 时间戳 ──────────────────────────────────────────
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="错误发生时间。",
    )
```

---

## 6. Agent Runtime Limits — 运行时限制配置

每个 Agent 必须遵守执行限制，防止无限循环导致成本不可控。默认值适用于所有 Agent，允许按 Agent 覆写。

### 6.1 配置模型

```python
from enum import Enum
from pydantic import BaseModel, Field


class RetryBackoff(str, Enum):
    """重试退避策略。"""
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"


class AgentRuntimeLimits(BaseModel):
    """Agent 运行时限制配置。

    全局默认值（适用于所有 Agent）：
    - max_iterations: 3
    - timeout_seconds: 300
    - retry_policy.max_retries: 3
    - retry_policy.backoff: exponential
    - retry_policy.retry_on: [LLM_TIMEOUT, API_ERROR, NETWORK_ERROR]
    - human_escalation.after_failed_retries: true
    - human_escalation.on_high_risk: false（全局默认 false，由 Risk Agent 覆写为 true）
    """

    # ── 循环限制 ─────────────────────────────────────────
    max_iterations: int = Field(
        default=3,
        ge=1,
        le=10,
        description=(
            "Agent 推理循环最大次数。"
            "每次循环 = 一次 LLM 调用 + 可选的工具调用。"
            "超过此值 → 自动中断 + 返回 FAILED (ITERATION_EXCEEDED)。"
        ),
    )
    timeout_seconds: int = Field(
        default=300,
        ge=30,
        le=3600,
        description=(
            "单次 Agent.execute() 调用的最大执行时间（秒）。"
            "超时 → 自动中断 + 返回 FAILED (TIMEOUT_EXCEEDED)。"
        ),
    )

    # ── 重试策略 ─────────────────────────────────────────
    class RetryPolicy(BaseModel):
        max_retries: int = Field(
            default=3,
            ge=0,
            le=5,
            description="Agent 级别最大重试次数。耗尽 → escalate_to_human。",
        )
        backoff: RetryBackoff = Field(
            default=RetryBackoff.EXPONENTIAL,
            description="重试退避策略。exponential: 1s → 2s → 4s。",
        )
        retry_on: list[ErrorType] = Field(
            default_factory=lambda: [
                ErrorType.LLM_TIMEOUT,
                ErrorType.API_ERROR,
                ErrorType.NETWORK_ERROR,
            ],
            description="触发自动重试的错误类型白名单。不在列表中的错误 → 直接 FAILED 不重试。",
        )

    retry_policy: RetryPolicy = Field(
        default_factory=RetryPolicy,
        description="Agent 级重试策略。",
    )

    # ── 人工升级策略 ─────────────────────────────────────
    class HumanEscalation(BaseModel):
        after_failed_retries: bool = Field(
            default=True,
            description="重试耗尽后是否自动进入 WAITING_APPROVAL（而非静默 FAILED）。",
        )
        on_high_risk: bool = Field(
            default=False,
            description=(
                "当 Agent 判断结果包含 HIGH 或 CRITICAL 风险等级时，"
                "是否强制进入 WAITING_APPROVAL。"
                "Risk Agent 覆写为 True。"
            ),
        )

    human_escalation: HumanEscalation = Field(
        default_factory=HumanEscalation,
        description="人工升级策略。",
    )
```

### 6.2 按 Agent 的推荐覆盖

```yaml
# agent_runtime_limits.yaml — 每个 Agent 可覆写默认值

global_defaults:
  max_iterations: 3
  timeout_seconds: 300
  retry_policy:
    max_retries: 3
    backoff: exponential
    retry_on: [LLM_TIMEOUT, API_ERROR, NETWORK_ERROR]
  human_escalation:
    after_failed_retries: true
    on_high_risk: false

planner_agent:
  max_iterations: 3
  timeout_seconds: 300
  # 使用默认值

knowledge_agent:
  max_iterations: 3
  timeout_seconds: 300
  # 使用默认值

risk_agent:
  max_iterations: 3
  timeout_seconds: 300
  human_escalation:
    on_high_risk: true
    # ↑ CRITICAL/HIGH 风险必须人工审批

evidence_agent:
  max_iterations: 3
  timeout_seconds: 300
  # 使用默认值

reviewer_agent:
  max_iterations: 3
  timeout_seconds: 300
  # 使用默认值
```

### 6.3 受限循环流程（以 Risk Agent 为例）

```
Risk Agent (iteration 1)
    │
    ▼
判断: Evidence 不足 → 触发 Evidence Agent 补充检索
    │
    ▼
Risk Agent (iteration 2)
    │
    ▼
判断: 仍不足 → 再次触发补充检索
    │
    ▼
Risk Agent (iteration 3)
    │
    ▼
判断: 3 次迭代后仍无法判定
    │
    ▼
返回 AgentResponse(status=NEEDS_HUMAN, error=AgentError(
    error_type=INSUFFICIENT_EVIDENCE,
    escalate_to_human=True,
    retry_count=3
))
    │
    ▼
WorkflowEngine → WAITING_APPROVAL（审计师人工介入）
```

### 6.4 超时中断流程

```
Agent.execute() 开始
    │
    ▼
timeout_seconds 计时开始
    │
    ▼  (执行中...)
    │
    ▼ timeout_seconds 到期
    │
    ▼
WorkflowEngine 中断 Agent 执行
    │
    ▼
触发 AGENT_FAILED Event
    → {agent_name, error_type: "TIMEOUT_EXCEEDED", retry_count: N}

    ├─ retry_count < max_retries → 进入 RETRYING
    │
    └─ retry_count >= max_retries → 进入 WAITING_APPROVAL
```

---

## 7. BaseAgent — 抽象基类

所有 Agent 必须继承此基类并实现 `execute` 方法。

```python
from abc import ABC, abstractmethod
from typing import final


class BaseAgent(ABC):
    """Agent 抽象基类。

    所有 Agent 必须实现此接口。框架通过此接口统一调度 Agent。
    """

    # ── 元数据（子类覆写）────────────────────────────────

    name: str
    """Agent 唯一名称。如 'planner' / 'knowledge' / 'risk' / 'evidence' / 'reviewer'。"""

    version: str = "1.0.0"
    """Agent 语义化版本。用于 Prompt 版本追踪和 Evaluation 关联。"""

    description: str = ""
    """Agent 功能简述。Registry 展示用。"""

    # ── 运行时限制（子类可覆写）──────────────────────────

    runtime_limits: AgentRuntimeLimits = AgentRuntimeLimits()
    """Agent 默认运行时限制。可在 AgentRequest.runtime_limits 中覆写。"""

    # ── 抽象方法（子类必须实现）──────────────────────────

    @abstractmethod
    async def execute(self, request: AgentRequest) -> AgentResponse:
        """执行 Agent 核心逻辑。

        Args:
            request: 统一请求载荷。

        Returns:
            AgentResponse: 统一响应格式。

        Raises:
            永远不应向外抛出未捕获异常 —
            所有异常必须被捕获并封装为 AgentResponse(status=FAILED, error=AgentError(...))。
        """
        ...

    # ── 工具接口（子类覆写）───────────────────────────────

    def get_tools(self) -> list["ToolDefinition"]:
        """返回此 Agent 声明的工具列表。

        Returns:
            ToolDefinition 列表。默认返回空列表。
            Agent 框架使用此列表进行 Tool Permission 校验 —
            如果 Agent 调用了未在此列表中的工具，调用将被拒绝。
        """
        return []

    # ── 可用但不强制覆写的钩子 ───────────────────────────

    async def on_before_execute(self, request: AgentRequest) -> None:
        """执行前钩子。可在此做日志记录、资源预加载等。"""
        pass

    async def on_after_execute(
        self, request: AgentRequest, response: AgentResponse
    ) -> None:
        """执行后钩子。可在此做清理、post-processing 等。"""
        pass

    # ── 框架方法（禁止覆写）───────────────────────────────

    @final
    async def run(self, request: AgentRequest) -> AgentResponse:
        """框架入口。包裹 execute，增加 before/after 钩子和异常安全保障。

        子类不得覆写此方法 — 只覆写 execute()。
        """
        await self.on_before_execute(request)
        try:
            response = await self.execute(request)
        except Exception as exc:
            response = AgentResponse(
                workflow_id=request.workflow_id,
                task_id=request.task_id,
                agent_name=self.name,
                status=AgentStatus.FAILED,
                result={"exception_type": type(exc).__name__},
                error=AgentError(
                    error_type=ErrorType.INTERNAL_ERROR,
                    message=str(exc),
                    detail={"exception_type": type(exc).__name__},
                    recoverable=False,
                    escalate_to_human=True,
                    escalation_reason=f"Unhandled exception in {self.name}: {type(exc).__name__}",
                ),
                confidence=0.0,
            )
        await self.on_after_execute(request, response)
        return response
```

---

## 8. AgentRegistry — Agent 注册中心接口

所有 Agent 必须在 AgentRegistry 中注册后方可被 WorkflowEngine 调度。

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator


class AgentRegistry(ABC):
    """Agent 注册中心。

    在应用启动时注册所有 Agent 实例。WorkflowEngine 通过此接口按名称查找 Agent。
    实现必须是线程安全的。
    """

    @abstractmethod
    async def register(self, agent: BaseAgent) -> None:
        """注册一个 Agent 实例。

        Args:
            agent: 已实例化的 BaseAgent 子类。

        Raises:
            ValueError: 同名 Agent 已注册。
            TypeError: agent 不是 BaseAgent 子类。
        """
        ...

    @abstractmethod
    async def unregister(self, name: str) -> None:
        """注销一个 Agent。

        Args:
            name: Agent 名称。

        Raises:
            KeyError: 指定名称的 Agent 未注册。
        """
        ...

    @abstractmethod
    async def get(self, name: str) -> BaseAgent:
        """按名称获取 Agent 实例。

        Args:
            name: Agent 名称。

        Returns:
            BaseAgent 实例。

        Raises:
            KeyError: 指定名称的 Agent 未注册。
        """
        ...

    @abstractmethod
    def list_agents(self) -> list[str]:
        """列出所有已注册的 Agent 名称。

        Returns:
            Agent 名称列表，按注册顺序排列。
        """
        ...

    @abstractmethod
    async def get_agent_info(self, name: str) -> dict[str, Any]:
        """获取 Agent 的元信息（名称、版本、描述、工具列表、运行时限制）。

        Args:
            name: Agent 名称。

        Returns:
            包含 name/version/description/tools/runtime_limits 的字典。

        Raises:
            KeyError: 指定名称的 Agent 未注册。
        """
        ...

    @abstractmethod
    def iterate_agents(self) -> AsyncIterator[BaseAgent]:
        """异步迭代所有已注册的 Agent。

        Yields:
            已注册的 Agent 实例。
        """
        ...


# ── 具体实现骨架 ─────────────────────────────────────────

class InMemoryAgentRegistry(AgentRegistry):
    """AgentRegistry 的内存实现。用于开发/测试环境。"""

    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}

    async def register(self, agent: BaseAgent) -> None:
        if agent.name in self._agents:
            raise ValueError(f"Agent '{agent.name}' is already registered")
        if not isinstance(agent, BaseAgent):
            raise TypeError(f"Expected BaseAgent, got {type(agent).__name__}")
        self._agents[agent.name] = agent

    async def unregister(self, name: str) -> None:
        if name not in self._agents:
            raise KeyError(f"Agent '{name}' not registered")
        del self._agents[name]

    async def get(self, name: str) -> BaseAgent:
        if name not in self._agents:
            raise KeyError(f"Agent '{name}' not registered")
        return self._agents[name]

    def list_agents(self) -> list[str]:
        return list(self._agents.keys())

    async def get_agent_info(self, name: str) -> dict[str, Any]:
        agent = await self.get(name)
        return {
            "name": agent.name,
            "version": agent.version,
            "description": agent.description,
            "tools": [t.dict() for t in agent.get_tools()],
            "runtime_limits": agent.runtime_limits.dict(),
        }

    async def iterate_agents(self) -> AsyncIterator[BaseAgent]:
        for agent in self._agents.values():
            yield agent
```

---

## 9. ToolDefinition 与 ToolRegistry — 工具定义与注册接口

### 9.1 ToolDefinition

```python
from enum import Enum


class ToolPermission(str, Enum):
    """工具权限等级。"""
    READ_ONLY = "READ_ONLY"
    # 只读操作：搜索、查询、检索。不会产生副作用。

    WRITE = "WRITE"
    # 写操作：创建记录、更新状态。会产生副作用。

    ADMIN = "ADMIN"
    # 管理操作：修改配置、删除数据。仅系统管理员可用。


class ToolDefinition(BaseModel):
    """Agent 工具的声明式定义。

    每个 Tool 必须注册其签名和权限等级。
    WorkflowEngine 在 Agent 调用工具前进行权限校验。
    """

    name: str = Field(
        ...,
        description="工具唯一名称。如 'ontology_query' / 'standard_search' / 'evidence_search'。",
    )
    description: str = Field(
        ...,
        description="工具功能描述。用于 LLM function-calling 的 description 字段。",
    )
    permission: ToolPermission = Field(
        default=ToolPermission.READ_ONLY,
        description="工具所需权限等级。",
    )

    # ── JSON Schema 参数定义 ──────────────────────────────
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "JSON Schema 格式的参数定义。"
            "与 OpenAI function-calling 的 parameters 字段兼容。"
            "示例: {'type': 'object', 'properties': {...}, 'required': [...]}"
        ),
    )

    # ── 元数据 ────────────────────────────────────────────
    version: str = Field(
        default="1.0.0",
        description="工具语义化版本。",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="工具分类标签。如 ['search', 'ontology', 'risk']。",
    )
```

### 9.2 ToolRegistry

```python
class ToolRegistry(ABC):
    """工具注册中心。

    管理所有 Agent 可用工具的定义与权限。
    Agent 声明的工具 get_tools() 必须与 ToolRegistry 中注册的定义一致。
    """

    @abstractmethod
    async def register(self, tool: ToolDefinition) -> None:
        """注册一个工具定义。

        Args:
            tool: 工具定义。

        Raises:
            ValueError: 同名工具已注册。
        """
        ...

    @abstractmethod
    async def unregister(self, name: str) -> None:
        """注销一个工具。

        Args:
            name: 工具名称。

        Raises:
            KeyError: 工具未注册。
        """
        ...

    @abstractmethod
    async def get(self, name: str) -> ToolDefinition:
        """获取工具定义。

        Args:
            name: 工具名称。

        Returns:
            ToolDefinition 实例。

        Raises:
            KeyError: 工具未注册。
        """
        ...

    @abstractmethod
    def list_tools(self, permission: ToolPermission | None = None) -> list[str]:
        """列出已注册工具名称。可按权限过滤。

        Args:
            permission: 可选权限过滤。None 表示返回全部。

        Returns:
            工具名称列表。
        """
        ...

    @abstractmethod
    async def validate_agent_tools(self, agent: BaseAgent) -> list[str]:
        """校验 Agent 声明的工具是否在 Registry 中注册且权限匹配。

        如果 Agent 调用未声明的工具，将在运行时被拒绝。
        如果 Agent 声明的工具未注册，应在此处报告警告。

        Args:
            agent: Agent 实例。

        Returns:
            校验失败的警告列表。空列表表示全部通过。
        """
        ...


# ── 具体实现骨架 ─────────────────────────────────────────

class InMemoryToolRegistry(ToolRegistry):
    """ToolRegistry 的内存实现。用于开发/测试环境。"""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    async def register(self, tool: ToolDefinition) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool

    async def unregister(self, name: str) -> None:
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not registered")
        del self._tools[name]

    async def get(self, name: str) -> ToolDefinition:
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not registered")
        return self._tools[name]

    def list_tools(self, permission: ToolPermission | None = None) -> list[str]:
        if permission is None:
            return list(self._tools.keys())
        return [n for n, t in self._tools.items() if t.permission == permission]

    async def validate_agent_tools(self, agent: BaseAgent) -> list[str]:
        warnings: list[str] = []
        for tool_def in agent.get_tools():
            registered = self._tools.get(tool_def.name)
            if registered is None:
                warnings.append(
                    f"Agent '{agent.name}' declares tool '{tool_def.name}' "
                    f"which is not in ToolRegistry"
                )
            elif registered.permission != tool_def.permission:
                warnings.append(
                    f"Agent '{agent.name}' tool '{tool_def.name}' "
                    f"permission mismatch: declared {tool_def.permission}, "
                    f"registry has {registered.permission}"
                )
        return warnings
```

### 9.3 Agent → Tool 权限映射（v1.0 冻结）

```yaml
# 每个 Agent 允许调用的工具白名单
planner_agent:
  tools:
    - ontology_query     # 查询审计 Ontology 推理链
    - agent_catalog      # 查询可用 Agent 能力

knowledge_agent:
  tools:
    - standard_search    # 审计准则语义检索
    - cross_reference    # 跨准则交叉引用
    - standard_lookup    # 精确段落查询

risk_agent:
  tools:
    - evidence_search    # 证据语义检索
    - standard_search    # 审计准则检索
    - calculator         # Materiality/Sampling 计算
    - ontology_query     # 查询 Ontology 推理链

evidence_agent:
  tools:
    - client_doc_search       # 客户文档语义检索
    - structured_data_query   # 结构化财务数据查询
    - table_extract           # 表格数据提取

reviewer_agent:
  tools:
    - evidence_search    # 验证证据相关度
    - standard_search    # 验证标准引用准确性
    - grounding_checker  # 检查 Citation 是否支撑 Claim
```

---

## 10. 使用示例：Planner Agent 如何实现本契约

以下是一个完整的 Planner Agent 实现示例，展示如何正确使用 Agent Contract 中的所有核心概念。

```python
from datetime import datetime
from typing import Any


class PlannerAgent(BaseAgent):
    """Planner Agent: 任务拆解与编排。

    职责：
    1. 接收审计委托，基于 Ontology 推理链拆解为子任务序列。
    2. 为每个子任务分配目标 Agent 和输入上下文。
    3. 产出 AuditPlanArtifact 供下游 Agent 消费。

    不负责：
    - 执行具体子任务（由 WorkflowEngine 调度）
    - 风险判断（Risk Agent）
    - 证据收集（Evidence Agent）
    """

    name = "planner"
    version = "1.0.0"
    description = "Task decomposition and orchestration based on audit ontology reasoning chains"

    # Planner 的推理循环较简单，保留默认限制
    runtime_limits = AgentRuntimeLimits(
        max_iterations=3,
        timeout_seconds=300,
        human_escalation=AgentRuntimeLimits.HumanEscalation(
            after_failed_retries=True,
            on_high_risk=False,  # Planner 不产生风险判断
        ),
    )

    # ── 工具声明 ──────────────────────────────────────────

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="ontology_query",
                description="Query the audit ontology to find reasoning chains for a given audit area",
                permission=ToolPermission.READ_ONLY,
                parameters={
                    "type": "object",
                    "properties": {
                        "area": {
                            "type": "string",
                            "description": "Audit area, e.g. 'revenue_recognition'",
                        },
                        "standards": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Applicable standards, e.g. ['ISA_315', 'IFRS_15']",
                        },
                    },
                    "required": ["area"],
                },
                tags=["ontology", "planning"],
            ),
            ToolDefinition(
                name="agent_catalog",
                description="List available agents and their capabilities",
                permission=ToolPermission.READ_ONLY,
                parameters={
                    "type": "object",
                    "properties": {},
                },
                tags=["planning"],
            ),
        ]

    # ── 核心逻辑 ──────────────────────────────────────────

    async def execute(self, request: AgentRequest) -> AgentResponse:
        started_at = datetime.utcnow()
        iteration = request.memory.get("iteration", 0) + 1

        # 1. 检查迭代限制
        effective_limits = request.runtime_limits or self.runtime_limits
        if iteration > effective_limits.max_iterations:
            return AgentResponse(
                workflow_id=request.workflow_id,
                task_id=request.task_id,
                agent_name=self.name,
                status=AgentStatus.FAILED,
                error=AgentError(
                    error_type=ErrorType.ITERATION_EXCEEDED,
                    message=f"Exceeded max_iterations ({effective_limits.max_iterations})",
                    detail={"iteration": iteration},
                    recoverable=False,
                    escalate_to_human=True,
                    escalation_reason="Planner exceeded iteration limit — human review required",
                ),
                confidence=0.0,
                started_at=started_at,
                metrics={"iterations": iteration},
            )

        # 2. 查询 Ontology — 确定推理链
        try:
            ontology_result = await self._query_ontology(
                area=request.inputs.get("area", "general"),
                client_industry=request.context.get("client_industry"),
            )
        except Exception as exc:
            return AgentResponse(
                workflow_id=request.workflow_id,
                task_id=request.task_id,
                agent_name=self.name,
                status=AgentStatus.FAILED,
                error=AgentError(
                    error_type=ErrorType.TOOL_ERROR,
                    message=f"Ontology query failed: {exc}",
                    detail={"tool": "ontology_query"},
                    recoverable=True,
                    retry_count=request.memory.get("retry_count", 0),
                ),
                confidence=0.0,
                started_at=started_at,
                metrics={"iterations": iteration},
            )

        # 3. 构建子任务序列
        subtasks = self._decompose(ontology_result, request.inputs)
        citations = self._build_citations(ontology_result)

        # 4. 产出 AuditPlanArtifact
        audit_plan = {
            "workflow_id": request.workflow_id,
            "materiality": request.inputs.get("materiality"),
            "areas": ontology_result.get("areas", []),
            "subtasks": subtasks,
            "reasoning": ontology_result.get("reasoning_chain", []),
            "created_by": self.name,
            "created_at": datetime.utcnow().isoformat(),
        }

        # 5. 返回成功响应
        return AgentResponse(
            workflow_id=request.workflow_id,
            task_id=request.task_id,
            agent_name=self.name,
            status=AgentStatus.SUCCESS,
            result={
                "artifact_type": "audit_plan",
                "artifact_id": f"plan_{request.workflow_id}",
                "content": audit_plan,
            },
            citations=citations,
            confidence=0.85,
            next_action="start_risk_assessment",  # 提示 WorkflowEngine 下一步
            metrics={
                "duration_ms": (datetime.utcnow() - started_at).total_seconds() * 1000,
                "iterations": iteration,
                "tool_calls": 2,  # ontology_query + agent_catalog
                "subtasks_generated": len(subtasks),
                "areas_covered": len(ontology_result.get("areas", [])),
            },
            started_at=started_at,
        )

    # ── 内部方法 ──────────────────────────────────────────

    async def _query_ontology(
        self, area: str, client_industry: str | None
    ) -> dict[str, Any]:
        """调用 ontology_query 工具。实际实现通过 LLM function-calling。"""
        # 此处为示意
        return {
            "areas": ["revenue_recognition", "going_concern", "related_parties"],
            "reasoning_chain": [
                "Step 1: Identify applicable standards (ISA 315, IFRS 15)",
                "Step 2: Determine risk indicators for revenue recognition",
                "Step 3: Map to evidence requirements",
            ],
        }

    def _decompose(
        self, ontology_result: dict[str, Any], inputs: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """将 Ontology 推理链拆解为可调度的子任务。"""
        subtasks = []
        for area in ontology_result.get("areas", []):
            subtasks.append({
                "task_id": f"{area}_knowledge_retrieval",
                "area": area,
                "agent": "knowledge",
                "description": f"Retrieve applicable audit standards for {area}",
                "input": {"area": area, "standards": ["ISA_315", "IFRS_15"]},
            })
            subtasks.append({
                "task_id": f"{area}_risk_assessment",
                "area": area,
                "agent": "risk",
                "description": f"Assess risk for {area}",
                "input": {"area": area},
                "depends_on": [f"{area}_knowledge_retrieval"],
            })
        return subtasks

    def _build_citations(
        self, ontology_result: dict[str, Any]
    ) -> list[Citation]:
        """从 Ontology 结果中构建 Citation 列表。"""
        citations: list[Citation] = []
        for area in ontology_result.get("areas", []):
            citations.append(
                Citation(
                    citation_id=f"cit_ontology_{area}",
                    source_type=CitationSourceType.AUDIT_STANDARD,
                    source_id="ISA_315",
                    source_name="ISA 315 Identifying and Assessing the Risks of Material Misstatement",
                    section="R21 — Understanding the Entity and Its Environment",
                    text_snippet=f"Reasoning chain for {area} derived from ISA 315 risk assessment framework",
                    relevance_score=0.95,
                    confidence=0.9,
                    metadata={
                        "ontology_area": area,
                        "standard_paragraph": "R21",
                    },
                )
            )
        return citations
```

### 10.1 Planner 的典型调用链

```
Client (API)
  │
  ▼
WorkflowEngine.create(graph_def)
  │
  ▼
WorkflowEngine.start(workflow_id)
  │
  ├─► AgentRegistry.get("planner")
  │     │
  │     ▼
  │   PlannerAgent.run(AgentRequest(
  │       workflow_id="wf_001",
  │       task_id="planning",
  │       firm_id="firm_abc",
  │       client_id="client_xyz",
  │       engagement_id="fy2024",
  │       inputs={"area": "revenue_recognition"},
  │   ))
  │     │
  │     ▼
  │   AgentResponse(
  │       status=SUCCESS,
  │       result={"artifact_type": "audit_plan", ...},
  │       citations=[Citation(...)],
  │       confidence=0.85,
  │       next_action="start_risk_assessment",
  │   )
  │     │
  │     ▼
  │   触发 Event: AgentCompleted → {agent_name: "planner", duration_ms: 1240, ...}
  │   触发 Event: ArtifactCreated → {artifact_id: "plan_wf_001", artifact_type: "audit_plan"}
  │     │
  │     ▼
  │   WorkflowEngine 根据 next_action 调度下一个 Agent...
  │
  ├─► AgentRegistry.get("knowledge")
  │     ...
  │
  ├─► AgentRegistry.get("risk")
  │     ...
  │
  └─► AgentRegistry.get("reviewer")
        ...
        ▼
      AgentResponse(status=NEEDS_HUMAN, ...)
        │
        ▼
      触发 Event: ApprovalRequired
        │
        ▼
      WAITING_APPROVAL → 审计师审查 Dashboard → 提交 ApprovalDecision
        │
        ▼
      触发 Event: ApprovalSubmitted → WorkflowCompleted
```

---

## 11. 附录：契约版本兼容性规则

### 11.1 版本号语义

```
v<MAJOR>.<MINOR>.<PATCH>

MAJOR: 不兼容的契约变更（字段移除、类型改变、状态枚举值删除）
MINOR: 向后兼容的新增（新增可选字段、新增状态枚举值）
PATCH: 文档修正、描述变更、不影响代码的调整
```

### 11.2 冻结后的变更流程

| 阶段 | 规则 |
|------|------|
| E0.5 完成后 | Agent Contract v1.0.0 冻结。任何人不得修改已冻结的字段定义。 |
| 如需新增字段 | 升级至 v1.1.0（MINOR bump），新增字段必须是 Optional。 |
| 如需 breaking change | 升级至 v2.0.0（MAJOR bump），前端与所有 Agent 同步更新。 |
| 任何变更 | 必须通过 Architecture Gate Review，更新本文档并附带 Migration Guide。 |

### 11.3 前向兼容性保证

- **新增字段**：接收方（Agent）必须容忍未知字段（Pydantic `extra='ignore'` 或 `extra='allow'`）。
- **新增枚举值**：接收方必须将未知枚举值视为等价于对应的 fallback（如未知 status → 视为 FAILED）。
- **弃用字段**：必须先标记 `deprecated` 并保持一个版本周期，再在下一 MAJOR 版本移除。

---

> **文档维护者：** AuditFlow Architecture Team  
> **最后更新：** E0.5 MileStone 0.5.4 完成时  
> **关联文档：** `auditflow/docs/architecture/artifact-contract.md`、`auditflow/docs/architecture/event-contract.md`
