# AuditFlow Event Schema（冻结版本 E0.5 / v3.2）

> **状态：** Frozen — 全项目唯一 Event Contract 事实来源  
> **冻结时间：** Epic 0.5 完成  
> **原则：** Agent Runtime、Workflow Engine 与 Frontend 之间的所有通信均通过结构化事件完成。所有状态变更均触发事件，事件不可变、可追溯、可实时推送。

---

## 目录

1. [概述](#1-概述)
2. [WorkflowEvent 基类](#2-workflowevent-基类)
3. [Agent 级事件（10 种）](#3-agent-级事件10-种)
   - [3.1 AgentStarted](#31-agentstarted)
   - [3.2 AgentThinking](#32-agentthinking)
   - [3.3 ToolCalled](#33-toolcalled)
   - [3.4 ToolCompleted](#34-toolcompleted)
   - [3.5 RetrievalCompleted](#35-retrievalcompleted)
   - [3.6 EvidenceFound](#36-evidencefound)
   - [3.7 ArtifactCreated](#37-artifactcreated)
   - [3.8 RiskDetected](#38-riskdetected)
   - [3.9 AgentCompleted](#39-agentcompleted)
   - [3.10 AgentFailed](#310-agentfailed)
4. [Workflow 生命周期事件（6 种）](#4-workflow-生命周期事件6-种)
   - [4.1 ApprovalRequired](#41-approvalrequired)
   - [4.2 ApprovalSubmitted](#42-approvalsubmitted)
   - [4.3 WorkflowPaused](#43-workflowpaused)
   - [4.4 WorkflowResumed](#44-workflowresumed)
   - [4.5 WorkflowCompleted](#45-workflowcompleted)
   - [4.6 WorkflowFailed](#46-workflowfailed)
5. [WebSocket 集成](#5-websocket-集成)
6. [持久化：agent_execution_log](#6-持久化agent_execution_log)
7. [附录：完整事件类型枚举与常量](#7-附录完整事件类型枚举与常量)

---

## 1. 概述

### 1.1 设计动机

在 AuditFlow 系统中，Agent Runtime 负责调度 Agent 执行审计任务，Workflow Engine 负责编排多 Agent 协作流程，Frontend 负责向审计师展示实时进度与中间结果。这三者之间的通信如果采用轮询或自由格式消息，会导致：

| 问题 | 后果 |
|------|------|
| **状态不可观测** | Frontend 无法实时展示 Agent 正在"思考什么"、"调用了什么工具" |
| **审批链路断裂** | 高风险判断需要人工审批时，Frontend 不知道何时弹出审批卡片 |
| **溯源不可靠** | 事后复盘时，无法精确还原每一步的决策时间线 |
| **耦合脆弱** | 各组件直接调用彼此的内部方法，任何一个重构都会级联破坏 |

因此，AuditFlow 在 E0.5 冻结了 Event Schema：**Agent Runtime、Workflow Engine、Frontend 之间仅通过 `WorkflowEvent` 通信**，所有事件不可变、持久化、可 WebSocket 推送。

### 1.2 设计原则

1. **状态变更 = 事件：** 任何有意义的系统状态变更，都必须产生且仅产生一条 `WorkflowEvent`。
2. **不可变：** 事件一旦写入 `agent_execution_log`（Append-Only 表），不允许 UPDATE 或 DELETE。
3. **实时 + 持久化双通道：** 关键事件通过 WebSocket 实时推送到 Frontend；所有事件持久化到数据库，支持事后审计与 Hash Chain 防篡改校验。
4. **Payload 类型安全：** 每种 `event_type` 对应一个严格的 payload schema，由 Pydantic 校验，杜绝弱类型 `dict[str, Any]`。
5. **单一事实来源：** 本文档是 Event 结构的唯一权威定义，所有组件必须与此一致。

### 1.3 事件分类

```
┌──────────────────────────────────────────────────────────────┐
│                    WorkflowEvent（基类）                       │
├──────────────────────────────┬───────────────────────────────┤
│   Agent 级事件（10 种）       │   Workflow 生命周期事件（6 种）  │
│                              │                               │
│  AgentStarted                │  ApprovalRequired             │
│  AgentThinking               │  ApprovalSubmitted            │
│  ToolCalled                  │  WorkflowPaused               │
│  ToolCompleted               │  WorkflowResumed              │
│  RetrievalCompleted          │  WorkflowCompleted            │
│  EvidenceFound               │  WorkflowFailed               │
│  ArtifactCreated             │                               │
│  RiskDetected                │                               │
│  AgentCompleted              │                               │
│  AgentFailed                 │                               │
└──────────────────────────────┴───────────────────────────────┘
```

### 1.4 事件流转全景

```
Agent Runtime                    Workflow Engine                   Frontend (WebSocket)
     │                                │                                │
     │── AgentStarted ───────────────▶│── AgentStarted ───────────────▶│  显示 Agent 启动
     │── AgentThinking ──────────────▶│── AgentThinking ──────────────▶│  更新思考步骤
     │── ToolCalled ─────────────────▶│── ToolCalled ─────────────────▶│  展示工具调用
     │── ToolCompleted ──────────────▶│── ToolCompleted ──────────────▶│  展示工具结果
     │── RetrievalCompleted ─────────▶│── RetrievalCompleted ─────────▶│  更新检索统计
     │── EvidenceFound ──────────────▶│── EvidenceFound ──────────────▶│  追加证据卡片
     │── ArtifactCreated ────────────▶│── ArtifactCreated ────────────▶│  展示产出物
     │── RiskDetected ───────────────▶│── RiskDetected ───────────────▶│  展示风险标记
     │                                │                                │
     │                                │── ApprovalRequired ───────────▶│  弹出审批卡片
     │                                │◀── ApprovalSubmitted ──────────│  提交审批决策
     │                                │                                │
     │── AgentCompleted ─────────────▶│── AgentCompleted ─────────────▶│  标记 Agent 完成
     │  or AgentFailed ──────────────▶│  or AgentFailed ──────────────▶│  标记 Agent 失败
     │                                │                                │
     │                                │── WorkflowCompleted ──────────▶│  工作流完成
     │                                │  or WorkflowFailed ───────────▶│  工作流失败
     ▼                                ▼                                ▼
agent_execution_log (Append-Only + Hash Chain)
```

---

## 2. WorkflowEvent 基类

所有事件的公共祖先。**禁止直接实例化** — 只能通过 `event_type` 对应的子 schema 创建。

```python
from pydantic import BaseModel, Field
from typing import Any
from datetime import datetime
from uuid import uuid4


class WorkflowEvent(BaseModel):
    """AuditFlow 中所有事件的统一基类。

    字段职责：
    - event_id: 全局唯一事件标识，由生产者生成。
    - workflow_id: 归属的工作流 ID，贯穿该次审计全生命周期。
    - event_type: 事件类型枚举值，决定 payload 的 schema。
    - timestamp: 事件产生时刻（UTC），精确到毫秒。
    - payload: 类型化的事件载荷，每个 event_type 对应一个严格的 Pydantic Model。
    """

    event_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="全局唯一事件 ID（UUID v4）"
    )

    workflow_id: str = Field(
        ...,
        description="归属的 Workflow ID"
    )

    event_type: str = Field(
        ...,
        description="事件类型枚举值，例如 AGENT_STARTED、TOOL_CALLED 等"
    )

    timestamp: datetime = Field(
        default_factory=lambda: datetime.utcnow(),
        description="事件产生时刻（UTC），精确到毫秒"
    )

    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="类型化的事件载荷，结构由 event_type 决定"
    )
```

### 2.1 字段约束

| 字段 | 类型 | 必填 | 生成者 | 说明 |
|------|------|------|--------|------|
| `event_id` | `str` (UUID v4) | ✅ | 事件生产者 | 全局唯一，用于去重与 Hash Chain |
| `workflow_id` | `str` | ✅ | Workflow Engine | 一次审计工作流的唯一标识 |
| `event_type` | `str` | ✅ | 事件生产者 | 必须是 `EventType` 枚举中的合法值 |
| `timestamp` | `datetime` (UTC) | ✅ | 事件生产者 | 毫秒精度，用于排序与时间线重建 |
| `payload` | `dict` | ✅ | 事件生产者 | 结构随 `event_type` 不同而不同，见各节定义 |

### 2.2 使用示例

```python
from auditflow.events import WorkflowEvent, EventType

# Agent Runtime 产生一个 AgentStarted 事件
event = WorkflowEvent(
    workflow_id="wf_20250115_001",
    event_type=EventType.AGENT_STARTED,
    payload={
        "agent_name": "RiskAgent",
        "task_summary": "评估应收账款坏账风险"
    }
)

# Workflow Engine 接收后：
# 1. 写入 agent_execution_log（持久化）
# 2. 通过 WebSocket 推送到 Frontend（实时）
```

---

## 3. Agent 级事件（10 种）

Agent 级事件由 **Agent Runtime** 在 Agent 执行生命周期中产生。每个事件对应 Agent 状态机的一个状态转换。

### 3.1 AgentStarted

Agent 开始执行时触发。Frontend 据此显示 Agent 工作卡片并初始化进度指示。

| 字段 | 类型 | 说明 |
|------|------|------|
| `agent_name` | `str` | Agent 名称，例如 `"PlannerAgent"`、`"RiskAgent"` |
| `task_summary` | `str` | 本次任务的简短摘要（≤200 字符） |

```python
# Payload Schema
class AgentStartedPayload(BaseModel):
    agent_name: str
    task_summary: str
```

**event_type:** `"AGENT_STARTED"`

---

### 3.2 AgentThinking

Agent 进入推理阶段时触发。用于 Frontend 展示 Agent 当前的思考步骤描述，提升透明度和信任感。

| 字段 | 类型 | 说明 |
|------|------|------|
| `agent_name` | `str` | Agent 名称 |
| `step_description` | `str` | 当前推理步骤的自然语言描述 |

```python
# Payload Schema
class AgentThinkingPayload(BaseModel):
    agent_name: str
    step_description: str
```

**event_type:** `"AGENT_THINKING"`

> **频率注意：** 一个 Agent 在其生命周期内可能触发多次 `AgentThinking`，每次代表一个推理步骤。Frontend 应以追加模式展示，而非替换。

---

### 3.3 ToolCalled

Agent 调用外部工具时触发。Frontend 据此展示工具调用卡片。

| 字段 | 类型 | 说明 |
|------|------|------|
| `agent_name` | `str` | 发起调用的 Agent 名称 |
| `tool_name` | `str` | 被调用的工具名称，例如 `"vector_search"` |
| `params_summary` | `str` | 工具参数的简短摘要（出于安全考虑，不暴露完整参数） |

```python
# Payload Schema
class ToolCalledPayload(BaseModel):
    agent_name: str
    tool_name: str
    params_summary: str
```

**event_type:** `"TOOL_CALLED"`

> **安全围栏：** `params_summary` 仅包含参数的类型与数量摘要，不暴露可能包含敏感数据的完整参数值。完整参数仅在 `agent_execution_log` 的 `payload` 中加密存储。

---

### 3.4 ToolCompleted

工具调用返回结果时触发。携带工具执行耗时，Frontend 更新工具卡片状态。

| 字段 | 类型 | 说明 |
|------|------|------|
| `agent_name` | `str` | 发起调用的 Agent 名称 |
| `tool_name` | `str` | 工具名称 |
| `result_summary` | `str` | 工具返回结果的简短摘要 |
| `duration_ms` | `int` | 工具执行耗时（毫秒） |

```python
# Payload Schema
class ToolCompletedPayload(BaseModel):
    agent_name: str
    tool_name: str
    result_summary: str
    duration_ms: int
```

**event_type:** `"TOOL_COMPLETED"`

> **配对规则：** 每个 `ToolCompleted` 必须与一个先前的 `ToolCalled` 配对（同一 `agent_name` + `tool_name`）。Frontend 据此将工具卡片从"执行中"切换为"已完成"。

---

### 3.5 RetrievalCompleted

知识检索操作完成时触发。由 Knowledge Agent 产生，Frontend 展示检索统计信息。

| 字段 | 类型 | 说明 |
|------|------|------|
| `query` | `str` | 检索查询文本 |
| `hit_count` | `int` | 检索命中数 |
| `top_score` | `float` | 最高相似度得分（0.0–1.0） |

```python
# Payload Schema
class RetrievalCompletedPayload(BaseModel):
    query: str
    hit_count: int
    top_score: float
```

**event_type:** `"RETRIEVAL_COMPLETED"`

---

### 3.6 EvidenceFound

Evidence Agent 发现并确认一条有效证据时触发。Frontend 追加证据卡片到证据面板。

| 字段 | 类型 | 说明 |
|------|------|------|
| `evidence_id` | `str` | 证据唯一 ID |
| `claim` | `str` | 证据所支撑的断言/主张 |
| `source_summary` | `str` | 证据来源摘要（文档名 + Chunk 位置） |

```python
# Payload Schema
class EvidenceFoundPayload(BaseModel):
    evidence_id: str
    claim: str
    source_summary: str
```

**event_type:** `"EVIDENCE_FOUND"`

---

### 3.7 ArtifactCreated

Agent 产出结构化 Artifact 时触发。Frontend 据此在产出物面板中追加新条目。

| 字段 | 类型 | 说明 |
|------|------|------|
| `artifact_id` | `str` | Artifact 唯一 ID |
| `artifact_type` | `str` | Artifact 类型枚举，如 `"RiskFinding"`、`"EvidencePackage"` |
| `created_by` | `str` | 产出该 Artifact 的 Agent 名称 |

```python
# Payload Schema
class ArtifactCreatedPayload(BaseModel):
    artifact_id: str
    artifact_type: str
    created_by: str
```

**event_type:** `"ARTIFACT_CREATED"`

> **关联文档：** Artifact 完整类型定义见 `auditflow/docs/api/artifact-schema.md`。

---

### 3.8 RiskDetected

Risk Agent 识别到风险时触发。Frontend 在风险面板中追加风险标记。

| 字段 | 类型 | 说明 |
|------|------|------|
| `risk_id` | `str` | 风险唯一 ID |
| `area` | `str` | 风险所属审计领域，如 `"AR"`（应收账款）、`"INV"`（存货） |
| `severity` | `str` | 风险严重等级：`"LOW"` / `"MEDIUM"` / `"HIGH"` / `"CRITICAL"` |

```python
# Payload Schema
class RiskDetectedPayload(BaseModel):
    risk_id: str
    area: str
    severity: str  # LOW | MEDIUM | HIGH | CRITICAL
```

**event_type:** `"RISK_DETECTED"`

> **HITL 触发规则：** 当 `severity == "HIGH"` 或 `"CRITICAL"` 时，Workflow Engine 应自动将工作流状态转为 `WAITING_APPROVAL`，并触发 `ApprovalRequired` 事件（见 §4.1）。

---

### 3.9 AgentCompleted

Agent 成功完成全部任务时触发。携带资源消耗统计。

| 字段 | 类型 | 说明 |
|------|------|------|
| `agent_name` | `str` | Agent 名称 |
| `duration_ms` | `int` | Agent 总执行耗时（毫秒） |
| `tokens` | `int` | LLM Token 消耗总数（prompt + completion） |
| `confidence` | `float` | Agent 对输出结果的置信度（0.0–1.0） |

```python
# Payload Schema
class AgentCompletedPayload(BaseModel):
    agent_name: str
    duration_ms: int
    tokens: int
    confidence: float
```

**event_type:** `"AGENT_COMPLETED"`

---

### 3.10 AgentFailed

Agent 执行失败时触发。携带错误详情与重试信息，Frontend 据此展示错误状态与重试按钮。

| 字段 | 类型 | 说明 |
|------|------|------|
| `agent_name` | `str` | Agent 名称 |
| `error_type` | `str` | 错误类型，例如 `"ToolTimeout"`、`"LLMAPIError"`、`"ValidationError"` |
| `retry_count` | `int` | 当前已重试次数（含本次） |
| `recoverable` | `bool` | 是否可恢复（`True` 表示可自动/手动重试，`False` 表示致命错误） |

```python
# Payload Schema
class AgentFailedPayload(BaseModel):
    agent_name: str
    error_type: str
    retry_count: int
    recoverable: bool
```

**event_type:** `"AGENT_FAILED"`

> **重试策略：** 若 `recoverable == True` 且 `retry_count < max_retries`，Agent Runtime 自动重新调度该 Agent。若 `recoverable == False`，Workflow Engine 将工作流转为 `WORKFLOW_FAILED`。

---

## 4. Workflow 生命周期事件（6 种）

Workflow 生命周期事件由 **Workflow Engine** 产生，反映工作流级别的状态转换与人工交互节点。

### 4.1 ApprovalRequired

当 Agent 产出的风险等级达到阈值或 Reviewer Agent 判定需人工介入时，Workflow Engine 触发此事件。Frontend 据此弹出审批卡片。

| 字段 | 类型 | 说明 |
|------|------|------|
| `approval_id` | `str` | 审批请求唯一 ID |
| `agent_name` | `str` | 触发审批的 Agent 名称 |
| `severity` | `str` | 触发审批的风险等级：`"HIGH"` / `"CRITICAL"` |
| `summary` | `str` | 审批事项摘要（供审计师快速决策） |

```python
# Payload Schema
class ApprovalRequiredPayload(BaseModel):
    approval_id: str
    agent_name: str
    severity: str  # HIGH | CRITICAL
    summary: str
```

**event_type:** `"APPROVAL_REQUIRED"`

> **Frontend 行为：** 收到此事件后，前端应弹出审批对话框，展示 `summary`，提供"批准"/"驳回"/"要求修改"三个选项。

---

### 4.2 ApprovalSubmitted

审计师提交审批决策后，Frontend 通过 WebSocket 向 Workflow Engine 发送此事件。Engine 据此决定继续执行、回退或终止。

| 字段 | 类型 | 说明 |
|------|------|------|
| `approval_id` | `str` | 对应的审批请求 ID |
| `decision` | `str` | 审批决策：`"APPROVED"` / `"REJECTED"` / `"NEEDS_REVISION"` |
| `comment` | `str` | 审计师备注（可选，为空时传 `""`） |

```python
# Payload Schema
class ApprovalSubmittedPayload(BaseModel):
    approval_id: str
    decision: str  # APPROVED | REJECTED | NEEDS_REVISION
    comment: str
```

**event_type:** `"APPROVAL_SUBMITTED"`

> **注意：** 此事件由 Frontend **发起**（而非 Workflow Engine），方向与其他事件相反。Engine 收到后根据 `decision` 执行相应分支逻辑，并将此事件持久化到 `approval_log` 表。

---

### 4.3 WorkflowPaused

工作流因外部原因（如等待人工输入、系统维护）暂停时触发。

| 字段 | 类型 | 说明 |
|------|------|------|
| `reason` | `str` | 暂停原因描述 |

```python
# Payload Schema
class WorkflowPausedPayload(BaseModel):
    reason: str
```

**event_type:** `"WORKFLOW_PAUSED"`

---

### 4.4 WorkflowResumed

工作流从暂停状态恢复时触发。Payload 为空（`{}`）。

```python
# Payload Schema
class WorkflowResumedPayload(BaseModel):
    pass  # 无额外字段
```

**event_type:** `"WORKFLOW_RESUMED"`

---

### 4.5 WorkflowCompleted

整个工作流成功完成时触发。携带总资源消耗统计。

| 字段 | 类型 | 说明 |
|------|------|------|
| `total_duration_ms` | `int` | 工作流总耗时（毫秒） |
| `total_tokens` | `int` | 所有 Agent 的 LLM Token 消耗总和 |
| `total_cost` | `float` | 估算总成本（USD） |

```python
# Payload Schema
class WorkflowCompletedPayload(BaseModel):
    total_duration_ms: int
    total_tokens: int
    total_cost: float
```

**event_type:** `"WORKFLOW_COMPLETED"`

---

### 4.6 WorkflowFailed

工作流因不可恢复的错误而终止时触发。

| 字段 | 类型 | 说明 |
|------|------|------|
| `error` | `str` | 导致失败的最终错误描述 |
| `recoverable` | `bool` | 是否可恢复（始终为 `False`，保留字段用于未来扩展） |

```python
# Payload Schema
class WorkflowFailedPayload(BaseModel):
    error: str
    recoverable: bool
```

**event_type:** `"WORKFLOW_FAILED"`

---

## 5. WebSocket 集成

### 5.1 双通道架构

AuditFlow 的事件分发采用"实时推送 + 持久化"双通道：

```
┌──────────────────┐         WebSocket (实时)        ┌──────────────────┐
│  Agent Runtime   │ ──────────────────────────────▶ │    Frontend      │
│  Workflow Engine │                                  │  (React SPA)     │
└────────┬─────────┘                                  └──────────────────┘
         │
         │  INSERT (持久化)
         ▼
┌──────────────────┐
│ agent_execution  │
│ _log (Append-    │
│ Only + Hash      │
│ Chain)           │
└──────────────────┘
```

### 5.2 实时推送事件（WebSocket）

以下事件通过 WebSocket **实时推送**到 Frontend，供 UI 即时更新：

| 事件 | 推送时机 | Frontend 行为 |
|------|----------|---------------|
| `AgentStarted` | Agent 开始执行 | 初始化 Agent 工作卡片，显示加载动画 |
| `AgentThinking` | Agent 进入推理步骤 | 追加思考步骤文本到卡片 |
| `ToolCalled` | 工具调用发起 | 新增工具调用条目，状态："执行中" |
| `ToolCompleted` | 工具调用返回 | 更新工具条目为"已完成"，显示耗时 |
| `RetrievalCompleted` | 知识检索完成 | 更新检索统计面板 |
| `EvidenceFound` | 证据确认 | 追加证据卡片到证据面板 |
| `ArtifactCreated` | Artifact 产出 | 追加条目到产出物面板 |
| `RiskDetected` | 风险识别 | 追加风险标记到风险面板 |
| `AgentCompleted` | Agent 完成 | 标记 Agent 卡片为"已完成"，显示统计 |
| `AgentFailed` | Agent 失败 | 标记 Agent 卡片为"失败"，显示错误信息 |
| `ApprovalRequired` | 需要人工审批 | **弹出审批对话框**（模态框） |
| `WorkflowPaused` | 工作流暂停 | 全局状态栏显示"已暂停" |
| `WorkflowResumed` | 工作流恢复 | 全局状态栏恢复"运行中" |
| `WorkflowCompleted` | 工作流完成 | 显示完成摘要 & 跳转至报告页 |
| `WorkflowFailed` | 工作流失败 | 显示失败摘要 & 错误详情 |

### 5.3 持久化-Only 事件

以下事件**仅写入数据库**，不通过 WebSocket 推送（因为方向相反或无实时展示需求）：

| 事件 | 原因 |
|------|------|
| `ApprovalSubmitted` | 由 Frontend **发起**，经 HTTP POST 提交，Engine 处理后再写入日志 |

### 5.4 WebSocket 连接协议

```
连接端点：  ws://<host>/ws/workflow/{workflow_id}
认证方式：  JWT Token（通过连接时的 query param 传递）
消息格式：  JSON，与 WorkflowEvent 序列化格式一致

示例消息：
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "workflow_id": "wf_20250115_001",
  "event_type": "AGENT_STARTED",
  "timestamp": "2025-01-15T10:30:00.123Z",
  "payload": {
    "agent_name": "RiskAgent",
    "task_summary": "评估应收账款坏账风险"
  }
}
```

### 5.5 断线重连与事件回放

- **断线重连：** Frontend 使用指数退避重连策略（1s → 2s → 4s → 8s，最大 30s）。
- **事件回放：** 重连成功后，Frontend 通过 `GET /api/v1/workflows/{workflow_id}/events?since={last_event_id}` 拉取断线期间遗漏的事件，合并到本地状态。

---

## 6. 持久化：agent_execution_log

### 6.1 表结构

所有 WorkflowEvent 写入 `agent_execution_log` 表。该表为 **Append-Only + Hash Chain** 设计，防止篡改。

```sql
CREATE TABLE agent_execution_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL,
    agent_name VARCHAR NOT NULL,
    prompt_version VARCHAR NOT NULL,
    event_type VARCHAR NOT NULL,
    payload JSONB NOT NULL,
    payload_hash VARCHAR NOT NULL,     -- SHA256(payload::text)
    previous_hash VARCHAR,             -- 上一条日志的 payload_hash（Hash Chain）
    created_at TIMESTAMPTZ DEFAULT now()

    -- 安全约束
    -- REVOKE UPDATE, DELETE ON agent_execution_log FROM application_role;
    -- GRANT INSERT, SELECT ON agent_execution_log TO application_role;
);
```

### 6.2 Hash Chain 机制

每条日志的 `payload_hash` = `SHA256(payload::text)`，`previous_hash` 指向上一条日志的 `payload_hash`：

```
event1: payload_hash = SHA256(e1.payload), previous_hash = NULL
event2: payload_hash = SHA256(e2.payload), previous_hash = SHA256(e1.payload)
event3: payload_hash = SHA256(e3.payload), previous_hash = SHA256(e2.payload)
```

**验证函数：**

```sql
CREATE OR REPLACE FUNCTION verify_hash_chain(p_workflow_id UUID)
RETURNS TABLE(seq_no BIGINT, valid BOOLEAN, expected_hash VARCHAR, actual_hash VARCHAR)
AS $$
-- 逐条重新计算 payload_hash，与存储值比对
-- 同时验证 previous_hash 链的连续性
-- 任一条断裂即标记 valid = FALSE
$$ LANGUAGE plpgsql;
```

### 6.3 写入规则

| 规则 | 说明 |
|------|------|
| **仅追加** | `INSERT` 权限开放，`UPDATE` / `DELETE` 权限已回收 |
| **原子写入** | 每条事件作为一行写入，`payload_hash` 与 `previous_hash` 在同一事务中计算 |
| **不可变性** | 一旦写入，任何组件（包括管理员）都无法通过应用层修改已持久化的事件 |
| **审批日志分离** | 审批决策写入独立的 `approval_log` 表（同样 Append-Only + Hash Chain） |

---

## 7. 附录：完整事件类型枚举与常量

### 7.1 EventType 枚举

```python
from enum import Enum


class EventType(str, Enum):
    """AuditFlow v3.2 冻结事件类型枚举 — 共 16 种。"""

    # ── Agent 级事件（10 种） ──────────────────────────
    AGENT_STARTED         = "AGENT_STARTED"
    AGENT_THINKING        = "AGENT_THINKING"
    TOOL_CALLED           = "TOOL_CALLED"
    TOOL_COMPLETED        = "TOOL_COMPLETED"
    RETRIEVAL_COMPLETED   = "RETRIEVAL_COMPLETED"
    EVIDENCE_FOUND        = "EVIDENCE_FOUND"
    ARTIFACT_CREATED      = "ARTIFACT_CREATED"
    RISK_DETECTED         = "RISK_DETECTED"
    AGENT_COMPLETED       = "AGENT_COMPLETED"
    AGENT_FAILED          = "AGENT_FAILED"

    # ── Workflow 生命周期事件（6 种） ──────────────────
    APPROVAL_REQUIRED     = "APPROVAL_REQUIRED"
    APPROVAL_SUBMITTED    = "APPROVAL_SUBMITTED"
    WORKFLOW_PAUSED       = "WORKFLOW_PAUSED"
    WORKFLOW_RESUMED      = "WORKFLOW_RESUMED"
    WORKFLOW_COMPLETED    = "WORKFLOW_COMPLETED"
    WORKFLOW_FAILED       = "WORKFLOW_FAILED"
```

### 7.2 事件严重等级常量

```python
class SeverityLevel(str, Enum):
    """RiskDetected / ApprovalRequired 使用的严重等级。"""
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"
```

### 7.3 审批决策常量

```python
class ApprovalDecision(str, Enum):
    """ApprovalSubmitted 使用的决策枚举。"""
    APPROVED       = "APPROVED"
    REJECTED       = "REJECTED"
    NEEDS_REVISION = "NEEDS_REVISION"
```

### 7.4 版本兼容性

| 变更类型 | 策略 |
|----------|------|
| 新增 `event_type` | MINOR bump（v3.3），旧版消费者忽略未知事件类型 |
| 已有 `payload` 新增字段 | MINOR bump，消费者使用 `extra='ignore'` 容忍 |
| 已有 `payload` 删除字段 | MAJOR bump（v4.0），需 Migration Guide |
| 已有 `payload` 修改字段类型 | MAJOR bump（v4.0），视为 Breaking Change |

---

> **文档维护者：** AuditFlow Architecture Team  
> **最后更新：** E0.5 MileStone 0.5.4 完成时（冻结）  
> **关联文档：** `auditflow/docs/api/agent-contract.md`、`auditflow/docs/api/artifact-schema.md`  
> **原始定义来源：** `auditflow/ISSUES.md` § Event Contract（v3.1） → v3.2 冻结
