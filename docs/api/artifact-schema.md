# AuditFlow Artifact Schema（冻结版本 E0.5 / v3.2）

> **状态：** Frozen — 全项目唯一 Artifact 事实来源  
> **冻结时间：** Epic 0.5 完成  
> **原则：** 所有 Agent/Service 的输出必须是结构化 Artifact，不是自然语言文本块。Report Generator 及其他下游 Service 直接消费 Artifact，无需解析自然语言。

---

## 目录

1. [概述](#1-概述)
2. [AuditArtifact 基类](#2-auditartifact-基类)
3. [ArtifactRegistry — 注册与发现](#3-artifactregistry--注册与发现)
4. [7 种冻结 Artifact 类型](#4-7-种冻结-artifact-类型)
   - [4.1 RiskFindingArtifact](#41-riskfindingartifact)
   - [4.2 EvidencePackageArtifact](#42-evidencepackageartifact)
   - [4.3 KnowledgePackageArtifact](#43-knowledgepackageartifact)
   - [4.4 AuditPlanArtifact](#44-auditplanartifact)
   - [4.5 ReviewReportArtifact](#45-reviewreportartifact)
   - [4.6 WorkpaperArtifact](#46-workpaperartifact)
   - [4.7 ReportArtifact](#47-reportartifact)
5. [Artifact 溯源链](#5-artifact-溯源链)
6. [附录：完整类型枚举与常量](#6-附录完整类型枚举与常量)

---

## 1. 概述

### 1.1 设计动机

传统 AI 审计系统的 Agent 输出自由文本，下游组件需要靠正则或 LLM 二次解析才能提取结构化信息。这种方式存在三个致命问题：

| 问题 | 后果 |
|------|------|
| **解析脆弱性** | Prompt 微调即可导致下游解析失败 |
| **信息丢失** | 自然语言无法精确表达 structured claims / scores / citations |
| **溯源断裂** | 自由文本无法可靠建立 `parent_artifact_id` 链 |

AuditFlow 在设计之初即冻结 Artifact Schema：**每个 Agent/Service 产出一个明确的 Artifact 子类型**，字段类型严格受控，下游无需任何自然语言解析。

### 1.2 设计原则

1. **结构化优先：** `content` 字段始终是严格的 Pydantic Model，不是 `dict[str, Any]` 的弱类型兜底。
2. **不可变溯源：** 每个 Artifact 携带 `parent_artifact_id`，构成从 Planner → 最终 Report 的完整证据链。
3. **Citation 必须：** 每个 Artifact 的 `citations` 字段不可为空（至少声明来源 Agent）。
4. **Schema 版本化：** `schema_version` 字段保证向前兼容，未来升级时旧版本仍可反序列化。
5. **单一事实来源：** 本文档是 Artifact 结构的唯一权威定义，所有代码必须与此一致。

### 1.3 Artifact 生命周期

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Planner  │───▶│Knowledge │───▶│  Risk    │───▶│Evidence  │───▶│ Reviewer │
│          │    │  Agent   │    │  Agent   │    │  Agent   │    │  Agent   │
│AuditPlan │    │Knowledge │    │RiskFind. │    │Evidence  │    │ Review   │
│Artifact  │    │Package   │    │Artifact  │    │Package   │    │ Report   │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
      │               │               │               │               │
      └───────────────┴───────────────┴───────────────┴───────────────┘
                                      │
                                      ▼
                            ┌──────────────────┐
                            │ Report Generator  │
                            │  (Service)        │
                            │                   │
                            │  ReportArtifact   │
                            └──────────────────┘
                                      │
                                      ▼
                            ┌──────────────────┐
                            │  Human Reviewer   │
                            │  (Final Sign-off) │
                            └──────────────────┘
```

---

## 2. AuditArtifact 基类

所有 Artifact 类型的公共祖先。**禁止直接实例化** — 只能通过子类型创建。

### 2.1 Pydantic 定义

```python
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Generic, Literal, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


# ═══════════════════════════════════════════════════════════════════
# Citation
# ═══════════════════════════════════════════════════════════════════

class Citation(BaseModel):
    """一条可追溯的引用 — AuditArtifact 的基础构成单元"""
    citation_id: str = Field(
        default_factory=lambda: f"cit-{uuid4().hex[:12]}",
        description="全局唯一引用 ID"
    )
    source_type: Literal[
        "AUDIT_STANDARD",
        "CLIENT_DOCUMENT",
        "ONTOLOGY_CHAIN",
        "AGENT_INFERENCE",
        "HUMAN_INPUT",
        "EXTERNAL_API",
    ]
    source_id: str = Field(
        description="来源标识：标准段落号 / 文档 ID / 推理链名称"
    )
    source_label: str = Field(
        description="人类可读的来源标签，如 'ISA 315 ¶27'"
    )
    excerpt: str | None = Field(
        default=None,
        description="引用原文摘录（如有）"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Agent 对此引用的置信度"
    )


# ═══════════════════════════════════════════════════════════════════
# AuditArtifact 基类
# ═══════════════════════════════════════════════════════════════════

class AuditArtifact(BaseModel):
    """所有 Agent/Service 的结构化产出的抽象基类。

    禁止直接实例化 — 必须使用子类型。
    """

    artifact_type: str = Field(
        description="Artifact 类型标识符，如 'risk_finding'。由子类 Literal 约束。"
    )
    artifact_id: str = Field(
        default_factory=lambda: f"art-{uuid4().hex[:16]}",
        description="全局唯一 Artifact ID"
    )
    created_by: str = Field(
        description="产出此 Artifact 的 Agent 名称或 Service 名称"
    )
    schema_version: str = Field(
        default="v1",
        description="Schema 版本号，用于向前兼容反序列化"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="创建时间戳 (UTC)"
    )
    workflow_id: str = Field(
        description="所属 Workflow ID"
    )
    project_id: str = Field(
        description="所属审计项目 ID"
    )
    content: dict[str, Any] = Field(
        description="结构化 JSON 内容。子类通过范型约束为具体 Content Model。"
    )
    citations: list[Citation] = Field(
        default_factory=list,
        description="与此 Artifact 关联的所有 Citation"
    )
    parent_artifact_id: str | None = Field(
        default=None,
        description="上游 Artifact ID — 构成溯源链的核心字段"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="扩展元数据（Agent 执行耗时、token 用量、模型版本等）"
    )

    @field_validator("citations")
    @classmethod
    def citations_must_not_be_empty(cls, v: list[Citation]) -> list[Citation]:
        """每个 Artifact 必须至少携带一条 Citation。"""
        if len(v) == 0:
            raise ValueError("Artifact.citations 不能为空 — 至少需一条来源声明")
        return v

    class Config:
        extra = "forbid"  # 禁止未声明字段，保证 Schema 纪律
```

### 2.2 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `artifact_type` | `str` | ✅ | 类型标识符，子类通过 `Literal` 固定值 |
| `artifact_id` | `str` | ✅ | 全局唯一 ID，格式 `art-{16 hex}` |
| `created_by` | `str` | ✅ | 产出者名称：`planner` / `knowledge_agent` / `risk_agent` / `evidence_agent` / `reviewer_agent` / `workpaper_generator` / `report_generator` |
| `schema_version` | `str` | ✅ | 当前固定 `"v1"` |
| `created_at` | `datetime` | ✅ | UTC 创建时间 |
| `workflow_id` | `str` | ✅ | 所属 Workflow |
| `project_id` | `str` | ✅ | 所属审计项目 |
| `content` | `dict` | ✅ | 结构化内容，子类约束为具体 Content Model |
| `citations` | `list[Citation]` | ✅ | 至少一条引用 |
| `parent_artifact_id` | `str \| None` | ❌ | 上游 Artifact ID（Planner 为 `None`） |
| `metadata` | `dict` | ❌ | 执行元数据（耗时、token、模型等） |

---

## 3. ArtifactRegistry — 注册与发现

### 3.1 概述

`ArtifactRegistry` 是 Artifact 类型的全局注册表，提供：

- **类型注册：** 所有 Artifact 子类型在启动时自注册
- **类型发现：** 下游 Service 按 `artifact_type` 查找对应的 Pydantic Model
- **反序列化路由：** 从 JSON/dict 还原为正确的 Artifact 子类型实例
- **Schema 校验：** 统一入口校验 Artifact 是否符合其声明的类型

### 3.2 接口定义

```python
from typing import Type

class ArtifactRegistry:
    """全局 Artifact 类型注册表（单例）。"""

    _instance: ArtifactRegistry | None = None
    _registry: dict[str, Type[AuditArtifact]]

    def __new__(cls) -> ArtifactRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._registry = {}
        return cls._instance

    # ── 注册 ──────────────────────────────────────────────

    def register(self, artifact_cls: Type[AuditArtifact]) -> None:
        """注册一个 Artifact 子类型。

        使用子类 artifact_type 字段的 Literal 值作为 key。

        Raises:
            ValueError: 如果该 artifact_type 已被注册
            TypeError: 如果 artifact_cls 不是 AuditArtifact 的子类
        """
        ...

    # ── 发现 ──────────────────────────────────────────────

    def get(self, artifact_type: str) -> Type[AuditArtifact]:
        """按 artifact_type 查找 Artifact 子类。

        Raises:
            KeyError: 如果类型未注册
        """
        ...

    def list_types(self) -> list[str]:
        """返回所有已注册的 artifact_type 标识符。"""
        ...

    # ── 反序列化 ──────────────────────────────────────────

    def deserialize(self, data: dict) -> AuditArtifact:
        """从 dict 还原为正确的 Artifact 子类型实例。

        根据 data['artifact_type'] 路由到注册的 Model 进行校验。
        """
        ...

    # ── 批量校验 ──────────────────────────────────────────

    def validate_batch(self, artifacts: list[dict]) -> list[AuditArtifact]:
        """批量反序列化并校验。任何一条失败则整体回滚。"""
        ...


# 全局单例入口
artifact_registry = ArtifactRegistry()
```

### 3.3 使用示例

```python
# ── 注册（各 Artifact 模块加载时自动执行） ──
from auditflow.artifacts.registry import artifact_registry

artifact_registry.register(RiskFindingArtifact)
artifact_registry.register(EvidencePackageArtifact)
artifact_registry.register(KnowledgePackageArtifact)
artifact_registry.register(AuditPlanArtifact)
artifact_registry.register(ReviewReportArtifact)
artifact_registry.register(WorkpaperArtifact)
artifact_registry.register(ReportArtifact)

# ── 反序列化（下游 Service 使用） ──
raw = {
    "artifact_type": "risk_finding",
    "artifact_id": "art-a1b2c3d4e5f6g7h8",
    "content": {"area": "Revenue", "title": "...", ...},
    ...
}
artifact = artifact_registry.deserialize(raw)
# → RiskFindingArtifact 实例，content 已校验为 RiskFindingContent
```

---

## 4. 7 种冻结 Artifact 类型

### 4.1 RiskFindingArtifact

**产出者：** `risk_agent`  
**触发条件：** Risk Agent 完成 Evidence 补充后的最终风险评估  
**下游消费者：** Reviewer Agent, Workpaper Generator, Report Generator

#### 4.1.1 Content Schema

```python
class ProcedureSuggestion(BaseModel):
    """建议的审计程序"""
    procedure_type: Literal[
        "Inspection",
        "Observation",
        "Inquiry",
        "Confirmation",
        "Recalculation",
        "Reperformance",
        "AnalyticalProcedure",
    ]
    description: str = Field(
        description="程序描述，如 '抽查年末前 15 天大额销售合同'"
    )
    evidence_required: list[str] = Field(
        description="所需证据类型，如 ['sales_contracts', 'shipping_docs']"
    )
    priority: Literal["REQUIRED", "RECOMMENDED", "OPTIONAL"] = Field(
        default="REQUIRED"
    )


class RiskIndicator(BaseModel):
    """风险信号（带量化信息）"""
    indicator: str = Field(
        description="风险信号描述，如 'revenue_growth > 3x industry_avg'"
    )
    actual_value: str | None = Field(
        default=None,
        description="实际观测值，如 '45%'"
    )
    benchmark: str | None = Field(
        default=None,
        description="基准/阈值，如 'industry_avg: 10%'"
    )
    direction: Literal["ABOVE", "BELOW", "EQUAL", "DEVIATION"] | None = None


class RiskFindingContent(BaseModel):
    """RiskFindingArtifact 的 content 结构"""
    area: str = Field(
        description="审计领域，如 'Revenue Recognition'"
    )
    title: str = Field(
        description="风险标题，如 '激进收入确认 — 收入增长远超行业均值'"
    )
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = Field(
        description="风险严重等级"
    )
    probability: float = Field(
        ge=0.0,
        le=1.0,
        description="风险发生概率 (0.0–1.0)"
    )
    indicators: list[RiskIndicator] = Field(
        description="支持此风险判断的具体信号列表"
    )
    related_standards: list[str] = Field(
        description="相关审计准则/会计准则，如 ['IFRS 15 ¶27', 'ISA 240 ¶32']"
    )
    suggested_procedures: list[ProcedureSuggestion] = Field(
        description="建议执行的审计程序"
    )
    reasoning: list[str] = Field(
        description="Agent 推理链 — 从 Indicator 到 Risk 判断的逻辑步骤"
    )


class RiskFindingArtifact(AuditArtifact):
    """Risk Agent 产出的风险发现"""
    artifact_type: Literal["risk_finding"]
    content: RiskFindingContent
```

#### 4.1.2 严重等级判定规则

| Severity | 触发条件 | 下游行为 |
|----------|----------|----------|
| `CRITICAL` | 管理层凌驾 / 舞弊迹象 / 持续经营疑虑 | 强制暂停 → `NEEDS_HUMAN` |
| `HIGH` | 高风险指标 + 证据不足 / 高风险指标 ≥ 3 个 | 强制 → `NEEDS_HUMAN` |
| `MEDIUM` | 中等风险指标 1–2 个 / 证据基本充分 | 进入 Reviewer 审查 |
| `LOW` | 无显著异常 / 证据充分 | 进入 Reviewer 审查（低优先级） |

#### 4.1.3 示例

```json
{
  "artifact_type": "risk_finding",
  "artifact_id": "art-a1b2c3d4e5f6g7h8",
  "created_by": "risk_agent",
  "schema_version": "v1",
  "created_at": "2025-06-15T10:30:00Z",
  "workflow_id": "wf-x1y2z3",
  "project_id": "proj-2025-001",
  "content": {
    "area": "Revenue Recognition",
    "title": "激进收入确认 — 收入增长 3 倍行业均值",
    "severity": "HIGH",
    "probability": 0.85,
    "indicators": [
      {
        "indicator": "revenue_growth > 3x industry_avg",
        "actual_value": "45%",
        "benchmark": "industry_avg: 10%",
        "direction": "ABOVE"
      },
      {
        "indicator": "receivable_days increased > 30% YoY",
        "actual_value": "120 days",
        "benchmark": "prior_year: 85 days",
        "direction": "ABOVE"
      }
    ],
    "related_standards": [
      "IFRS 15 ¶27",
      "ISA 240 ¶32",
      "ISA 500 ¶6"
    ],
    "suggested_procedures": [
      {
        "procedure_type": "Inspection",
        "description": "抽查年末前 15 天大额销售合同，核对发货单日期",
        "evidence_required": ["sales_contracts", "shipping_docs"],
        "priority": "REQUIRED"
      },
      {
        "procedure_type": "Confirmation",
        "description": "函证前 5 大客户年度交易额",
        "evidence_required": ["customer_confirmations"],
        "priority": "REQUIRED"
      }
    ],
    "reasoning": [
      "识别到 revenue_growth=45% 远超行业均值 10% → 触发 Ontology 推理链 'revenue_recognition'",
      "应收账款周转天数从 85 天恶化至 120 天 → 截止性问题风险上升",
      "结合两个 HIGH 风险指标 → 综合判定为 HIGH 严重等级",
      "ISA 240 ¶32 要求对异常收入增长保持职业怀疑 → 建议实质性程序"
    ]
  },
  "citations": [
    {
      "citation_id": "cit-abc123def456",
      "source_type": "ONTOLOGY_CHAIN",
      "source_id": "revenue_recognition",
      "source_label": "Ontology 推理链: revenue_recognition",
      "confidence": 0.95
    }
  ],
  "parent_artifact_id": "art-prev-evidence-pkg",
  "metadata": {
    "agent_duration_ms": 3420,
    "total_tokens": 1850,
    "model": "gpt-4",
    "iteration_count": 2
  }
}
```

---

### 4.2 EvidencePackageArtifact

**产出者：** `evidence_agent`  
**触发条件：** Evidence Agent 完成对 claims_to_verify 的 Hybrid Search → 证据封装  
**下游消费者：** Risk Agent, Reviewer Agent, Workpaper Generator

#### 4.2.1 Content Schema

```python
class EvidenceSource(BaseModel):
    """证据来源描述"""
    source_type: Literal["CLIENT_DOCUMENT", "EXTERNAL_DATABASE", "API_RESPONSE", "AGENT_INFERENCE"]
    source_id: str = Field(description="文档 ID / API endpoint / Agent session ID")
    source_label: str = Field(description="人类可读标签，如 '2024 年度审计报告 p.42'")
    retrieval_method: Literal["VECTOR_SEARCH", "KEYWORD_SEARCH", "HYBRID", "MANUAL"] = Field(
        default="HYBRID"
    )
    relevance_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="检索相关度分数"
    )


class EvidencedClaim(BaseModel):
    """一条已完成证据匹配的声明"""
    claim_id: str = Field(
        description="声明唯一 ID"
    )
    claim_text: str = Field(
        description="声明原文，如 '收入确认时点符合 IFRS 15 要求'"
    )
    assertion: Literal[
        "Existence", "Completeness", "Accuracy",
        "Valuation", "RightsAndObligations", "PresentationAndDisclosure",
        "Cutoff", "Occurrence", "Classification",
    ] = Field(
        description="对应的审计断言"
    )
    sources: list[EvidenceSource] = Field(
        description="支持此 claim 的证据来源列表"
    )
    is_supported: bool = Field(
        description="证据是否充分支持该 claim"
    )
    support_level: Literal["STRONG", "MODERATE", "WEAK", "NONE"] = Field(
        description="证据支持强度"
    )
    notes: str | None = Field(
        default=None,
        description="Agent 备注"
    )


class EvidencePackageContent(BaseModel):
    """EvidencePackageArtifact 的 content 结构"""
    claims: list[EvidencedClaim] = Field(
        description="所有已评估的声明"
    )
    sources: list[EvidenceSource] = Field(
        description="汇总的所有证据来源"
    )
    coverage: float = Field(
        ge=0.0,
        le=1.0,
        description="有证据支持的 claim 占比 = supported_claims / total_claims"
    )
    unmatched: list[str] = Field(
        description="未找到任何证据的 claim 文本"
    )
    total_claims: int = Field(description="声明总数")
    supported_claims: int = Field(description="获得证据支持的声明数")


class EvidencePackageArtifact(AuditArtifact):
    """Evidence Agent 产出的证据包"""
    artifact_type: Literal["evidence_package"]
    content: EvidencePackageContent
```

#### 4.2.2 coverage 计算

```
coverage = supported_claims / total_claims

其中:
  supported_claims = |{ claim ∈ claims | claim.is_supported == True }|
  total_claims     = |claims|
```

当 `coverage < 0.5` 时，Risk Agent 可能触发迭代循环（请求补充证据）。

#### 4.2.3 示例

```json
{
  "artifact_type": "evidence_package",
  "artifact_id": "art-e4f5g6h7i8j9k0l1",
  "created_by": "evidence_agent",
  "schema_version": "v1",
  "content": {
    "claims": [
      {
        "claim_id": "clm-001",
        "claim_text": "2024 年收入增长 45%，前 5 大客户贡献 60%",
        "assertion": "Accuracy",
        "sources": [
          {
            "source_type": "CLIENT_DOCUMENT",
            "source_id": "doc-fin-2024-p42",
            "source_label": "2024 年度审计报告 p.42 — 收入明细表",
            "retrieval_method": "HYBRID",
            "relevance_score": 0.92
          }
        ],
        "is_supported": true,
        "support_level": "STRONG"
      }
    ],
    "sources": [],
    "coverage": 0.75,
    "unmatched": ["关联方交易定价的公允性"],
    "total_claims": 4,
    "supported_claims": 3
  },
  "citations": [
    {
      "citation_id": "cit-evid001",
      "source_type": "CLIENT_DOCUMENT",
      "source_id": "doc-fin-2024-p42",
      "source_label": "2024 年度审计报告 p.42",
      "confidence": 0.92
    }
  ],
  "parent_artifact_id": "art-prev-risk-finding"
}
```

---

### 4.3 KnowledgePackageArtifact

**产出者：** `knowledge_agent`  
**触发条件：** Knowledge Agent 检索审计准则 → 返回原文 + LLM 解读  
**下游消费者：** Risk Agent, Reviewer Agent, Report Generator

#### 4.3.1 Content Schema

```python
class StandardReference(BaseModel):
    """一条审计准则/会计准则引用"""
    standard_id: str = Field(
        description="准则编号，如 'ISA 315'"
    )
    paragraph: str = Field(
        description="段落号，如 '¶27'"
    )
    full_ref: str = Field(
        description="完整引用，如 'ISA 315 ¶27'"
    )
    title: str = Field(
        description="段落标题/主题"
    )
    full_text: str = Field(
        description="原始条文全文"
    )
    retrieval_score: float | None = Field(
        default=None,
        ge=0.0, le=1.0,
        description="检索相关度分数"
    )


class StandardInterpretation(BaseModel):
    """LLM 对准则的解读"""
    standard_ref: str = Field(
        description="被解读的准则引用，如 'IFRS 15 ¶27'"
    )
    interpretation: str = Field(
        description="LLM 解读：将准则语言翻译为审计实操指引"
    )
    applicability: Literal["DIRECTLY_APPLICABLE", "INDIRECTLY_RELEVANT", "BACKGROUND"] = Field(
        description="适用性级别"
    )
    caveats: list[str] = Field(
        default_factory=list,
        description="解读的注意事项 / 适用前提"
    )


class KnowledgePackageContent(BaseModel):
    """KnowledgePackageArtifact 的 content 结构"""
    standards: list[StandardReference] = Field(
        description="检索到的原始准则列表"
    )
    interpretations: list[StandardInterpretation] = Field(
        description="LLM 准则解读列表"
    )
    citations: list[Citation] = Field(
        default_factory=list,
        description="Knowledge 层面的额外 Citation（会合并到 Artifact 顶层 citations）"
    )
    query_summary: str = Field(
        description="触发此次检索的查询摘要"
    )


class KnowledgePackageArtifact(AuditArtifact):
    """Knowledge Agent 产出的知识包"""
    artifact_type: Literal["knowledge_package"]
    content: KnowledgePackageContent
```

---

### 4.4 AuditPlanArtifact

**产出者：** `planner`（Planner Agent）+ `planning_engine`（Service 协作）  
**触发条件：** 审计目标输入 → Ontology 查询 → 任务拆解  
**下游消费者：** 所有下游 Agent, Workpaper Generator

#### 4.4.1 Content Schema

```python
class MaterialityCalc(BaseModel):
    """重要性水平计算"""
    base: Literal["REVENUE", "TOTAL_ASSETS", "NET_PROFIT", "EQUITY"] = Field(
        description="计算基准"
    )
    base_value: float = Field(description="基准数值")
    percentage: float = Field(description="百分比阈值，如 0.05 表示 5%")
    overall_materiality: float = Field(description="整体重要性水平 = base_value × percentage")
    performance_materiality: float = Field(
        description="实际执行重要性水平 = overall_materiality × 0.75"
    )
    de_minimis: float = Field(
        description="微小错报阈值 = overall_materiality × 0.05"
    )


class SamplingStrategy(BaseModel):
    """抽样策略"""
    method: Literal["STATISTICAL", "JUDGMENTAL", "MONETARY_UNIT", "BLOCK"] = Field(
        description="抽样方法"
    )
    population_size: int = Field(description="总体规模")
    sample_size: int = Field(description="样本量")
    stratification: list[str] | None = Field(
        default=None,
        description="分层依据，如 ['金额 > 100 万单独测试']"
    )
    rationale: str = Field(description="抽样方法选择的理由")


class ProcedureDef(BaseModel):
    """一条审计程序定义"""
    step_id: str = Field(description="步骤 ID")
    step_order: int = Field(description="执行顺序 (1-based)")
    procedure_type: Literal[
        "Inspection", "Observation", "Inquiry",
        "Confirmation", "Recalculation", "Reperformance",
        "AnalyticalProcedure",
    ]
    description: str = Field(description="程序描述")
    assertion: str = Field(description="针对的审计断言")
    evidence_required: list[str] = Field(description="所需证据类型")
    assigned_agent: Literal["risk_agent", "evidence_agent", "knowledge_agent"] = Field(
        description="负责执行的 Agent"
    )
    risk_reference: str | None = Field(
        default=None,
        description="关联的风险发现 ID（如有）"
    )


class AgentSequence(BaseModel):
    """Agent 执行序列"""
    order: int = Field(description="执行顺序")
    agent_name: str = Field(description="Agent 名称")
    task_summary: str = Field(description="任务摘要")
    depends_on: list[str] = Field(
        default_factory=list,
        description="依赖的前置 Agent 名称列表"
    )
    expected_artifact_type: str = Field(
        description="期望产出的 Artifact 类型"
    )


class AuditPlanContent(BaseModel):
    """AuditPlanArtifact 的 content 结构"""
    steps: list[ProcedureDef] = Field(
        description="审计程序步骤列表"
    )
    agent_sequence: list[AgentSequence] = Field(
        description="Agent 执行序列"
    )
    evidence_required: list[str] = Field(
        description="全局所需证据类型汇总"
    )
    materiality: MaterialityCalc | None = Field(
        default=None,
        description="重要性水平（Planning Engine 计算）"
    )
    sampling_strategy: SamplingStrategy | None = Field(
        default=None,
        description="抽样策略（Planning Engine 计算）"
    )
    timeline: dict[str, str] = Field(
        default_factory=dict,
        description="计划时间线，如 {'planning': 'Day 1-2', 'fieldwork': 'Day 3-10'}"
    )


class AuditPlanArtifact(AuditArtifact):
    """Planner Agent + Planning Engine 产出的审计计划"""
    artifact_type: Literal["audit_plan"]
    content: AuditPlanContent
```

#### 4.4.2 溯源链起点

`AuditPlanArtifact` 是 Artifact 溯源链的**根节点** — 其 `parent_artifact_id` 始终为 `None`。

---

### 4.5 ReviewReportArtifact

**产出者：** `reviewer_agent`  
**触发条件：** Reviewer Agent 审查上游所有 Artifact → 检测遗漏/幻觉/弱逻辑  
**下游消费者：** HITL 审批 Dashboard, Workpaper Generator（终版）

#### 4.5.1 Content Schema

```python
class ReviewIssue(BaseModel):
    """审查发现的一个问题"""
    issue_id: str = Field(description="问题唯一 ID")
    severity: Literal["BLOCKER", "MAJOR", "MINOR", "SUGGESTION"] = Field(
        description="问题严重等级"
    )
    category: Literal[
        "MISSING_CITATION",     # 声明无引用
        "WEAK_LOGIC",           # 推理链薄弱
        "HALLUCINATION",        # 疑似幻觉（无法验证的声明）
        "INSUFFICIENT_EVIDENCE",# 证据不足以支持结论
        "STANDARD_MISMATCH",    # 准则适用错误
        "PROCEDURE_GAP",        # 程序遗漏
        "INCONSISTENCY",        # 与其他 Artifact 不一致
    ] = Field(description="问题类别")
    description: str = Field(description="问题描述")
    artifact_ref: str = Field(
        description="出问题的 Artifact ID"
    )
    suggestion: str = Field(description="修复建议")
    affected_claims: list[str] = Field(
        default_factory=list,
        description="受影响的 Claim ID 列表"
    )


class HallucinationCheck(BaseModel):
    """幻觉检测结果"""
    total_claims_checked: int = Field(description="检查的声明总数")
    unsupported_claims: int = Field(description="无法验证的声明数")
    unsupported_claim_rate: float = Field(
        description="无法验证率 = unsupported / total"
    )
    hallucination_risk: Literal["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        description="幻觉风险等级"
    )
    suspect_claims: list[str] = Field(
        default_factory=list,
        description="疑似幻觉的声明 IDs"
    )


class ReviewReportContent(BaseModel):
    """ReviewReportArtifact 的 content 结构"""
    review_result: Literal["APPROVED", "NEEDS_REVISION", "REJECTED"] = Field(
        description="审查结论"
    )
    issues: list[ReviewIssue] = Field(
        description="发现的问题列表"
    )
    quality_score: float = Field(
        ge=0.0,
        le=1.0,
        description="综合质量评分"
    )
    hallucination_risk: HallucinationCheck = Field(
        description="幻觉检测结果"
    )
    reviewed_artifacts: list[str] = Field(
        description="被审查的 Artifact ID 列表"
    )
    summary: str = Field(
        description="审查总结"
    )


class ReviewReportArtifact(AuditArtifact):
    """Reviewer Agent 产出的审查报告"""
    artifact_type: Literal["review_report"]
    content: ReviewReportContent
```

#### 4.5.2 quality_score 阈值规则

| quality_score | review_result | 下游行为 |
|---------------|---------------|----------|
| ≥ 0.85 | `APPROVED` | 流入 Workpaper Generator |
| 0.60–0.84 | `NEEDS_REVISION` | 自动退回上游 Agent（含 issue 列表） |
| < 0.60 | `REJECTED` | 强制 `NEEDS_HUMAN`，不可自动修复 |
| hallucination_risk ≥ `HIGH` | `REJECTED` | 无论 quality_score 多少，强制人工审查 |

---

### 4.6 WorkpaperArtifact

**产出者：** `workpaper_generator`（Service — 模板渲染 + Citation 嵌入）  
**触发条件：** Reviewer Agent `APPROVED` → Workpaper Generator 消费所有上游 Artifact  
**下游消费者：** HITL Dashboard, 最终审计档案

#### 4.6.1 Content Schema

```python
class WorkpaperSection(BaseModel):
    """工作底稿的一个标准章节"""
    section_id: str = Field(description="章节 ID")
    heading: str = Field(description="章节标题")
    content: str = Field(description="Markdown 格式的章节正文")
    citations: list[Citation] = Field(
        default_factory=list,
        description="本章节引用的 Citation"
    )
    source_artifact_ids: list[str] = Field(
        default_factory=list,
        description="本章节数据来源的 Artifact IDs"
    )


class WorkpaperContent(BaseModel):
    """WorkpaperArtifact 的 content 结构

    遵循标准审计工作底稿结构：
    Objective → Risk → Procedures → Findings → Conclusion
    """
    objective: WorkpaperSection = Field(
        description="审计目标 — 说明本次审计的范围和目的"
    )
    risk: WorkpaperSection = Field(
        description="风险评估 — 汇总 RiskFindingArtifact 内容"
    )
    procedures: WorkpaperSection = Field(
        description="审计程序 — 汇总 AuditPlanArtifact 的程序定义"
    )
    findings: WorkpaperSection = Field(
        description="审计发现 — 汇总 EvidencePackageArtifact 的证据结果"
    )
    conclusion: WorkpaperSection = Field(
        description="审计结论 — 综合判断"
    )
    appendix: list[WorkpaperSection] = Field(
        default_factory=list,
        description="附录（如 Materiality 计算明细、Sampling 明细）"
    )


class WorkpaperArtifact(AuditArtifact):
    """Workpaper Generator 产出的工作底稿草稿"""
    artifact_type: Literal["workpaper"]
    content: WorkpaperContent
```

#### 4.6.2 章节与上游 Artifact 映射

| 章节 | 主要来源 Artifact | 渲染方式 |
|------|-------------------|----------|
| `objective` | `AuditPlanArtifact.content.steps` | 提取审计范围与目标 |
| `risk` | `RiskFindingArtifact.content` | 汇总所有 Risk Finding |
| `procedures` | `AuditPlanArtifact.content.steps` | 程序列表渲染为表格 |
| `findings` | `EvidencePackageArtifact.content.claims` | 证据匹配结果渲染 |
| `conclusion` | `ReviewReportArtifact.content.summary` | 审查总结 + 质量评分 |
| `appendix` | `MaterialityCalc` + `SamplingStrategy` | 计算明细表 |

#### 4.6.3 MVP Beta 边界

> ⚠️ **Workpaper Draft Only:** MVP Beta 阶段仅生成工作底稿**草稿**。最终底稿需 Human Reviewer 确认后锁定。

---

### 4.7 ReportArtifact

**产出者：** `report_generator`（Service — ISA 700 模板渲染）  
**触发条件：** Workpaper 完成后 → Report Generator 消费所有上游 Artifact  
**下游消费者：** **Human Reviewer Only**（强制 HITL — 不可自动出具最终审计意见）

#### 4.7.1 Content Schema

```python
class ReportSection(BaseModel):
    """审计报告的一个 ISA 700 标准章节"""
    section_id: str = Field(description="章节 ID")
    heading: str = Field(description="章节标题（中英文双语）")
    content: str = Field(description="章节正文")
    is_required: bool = Field(
        default=True,
        description="是否为 ISA 700 强制章节"
    )


class ReportContent(BaseModel):
    """ReportArtifact 的 content 结构

    严格遵循 ISA 700 标准审计报告结构。
    """
    title: ReportSection = Field(
        description="标题 — '独立审计报告'"
    )
    addressee: ReportSection = Field(
        description="收件人 — 被审计单位股东/董事会"
    )
    opinion: ReportSection = Field(
        description="审计意见 — 无保留意见/保留意见/否定意见/无法表示意见"
    )
    basis_for_opinion: ReportSection = Field(
        description="形成审计意见的基础"
    )
    key_audit_matters: ReportSection = Field(
        description="关键审计事项 (KAM)"
    )
    management_responsibility: ReportSection = Field(
        description="管理层对财务报表的责任"
    )
    auditor_responsibility: ReportSection = Field(
        description="注册会计师的责任"
    )
    other_reporting_responsibilities: ReportSection | None = Field(
        default=None,
        description="其他报告责任（如适用）"
    )
    signature: ReportSection = Field(
        description="签字 — 注册会计师姓名、日期、事务所信息（草稿阶段留空）"
    )
    opinion_type: Literal[
        "UNMODIFIED",        # 无保留意见
        "QUALIFIED",         # 保留意见
        "ADVERSE",           # 否定意见
        "DISCLAIMER",        # 无法表示意见
        "PENDING",           # 待 Human 确认
    ] = Field(
        default="PENDING",
        description="审计意见类型 — 草稿阶段固定为 PENDING"
    )
    draft_warnings: list[str] = Field(
        default_factory=list,
        description="草稿警告信息（如 '本报告为 AI 生成草稿，尚未经人工审核'）"
    )


class ReportArtifact(AuditArtifact):
    """Report Generator 产出的审计报告草稿"""
    artifact_type: Literal["report"]
    content: ReportContent
```

#### 4.7.2 ISA 700 章节映射

| ISA 700 要求 | ReportSection | 内容来源 |
|-------------|---------------|----------|
| Title | `title` | 固定模板 |
| Addressee | `addressee` | `project_id` → 客户信息 |
| Opinion | `opinion` | 汇总 `RiskFindingArtifact` + `ReviewReportArtifact` |
| Basis for Opinion | `basis_for_opinion` | `KnowledgePackageArtifact.standards` |
| Key Audit Matters | `key_audit_matters` | `RiskFindingArtifact`（CRITICAL + HIGH） |
| Responsibilities | `management_responsibility` / `auditor_responsibility` | ISA 700 固定措辞 |
| Signature | `signature` | **草稿阶段留空** |

#### 4.7.3 强制 HITL

`ReportArtifact` 是唯一**不可自动出具**的 Artifact：

- `opinion_type` 在草稿阶段固定为 `"PENDING"`
- Generator 创建 Artifact 后 `next_action` 强制为 `"HUMAN_REVIEW"`
- 仅 Human Reviewer 在 Approval Dashboard 确认后，系统创建最终版本（`schema_version` 仍为 `v1`，`metadata.finalized_at` 记录确认时间）

---

## 5. Artifact 溯源链

### 5.1 链式结构

每个 Artifact 通过 `parent_artifact_id` 指向上游，形成一条完整的不可变证据链：

```
AuditPlanArtifact          (parent_artifact_id = null)
    │
    ▼
KnowledgePackageArtifact   (parent_artifact_id = AuditPlanArtifact.artifact_id)
    │
    ▼
RiskFindingArtifact        (parent_artifact_id = KnowledgePackageArtifact.artifact_id)
    │
    ▼
EvidencePackageArtifact    (parent_artifact_id = RiskFindingArtifact.artifact_id)
    │
    ▼
ReviewReportArtifact       (parent_artifact_id = EvidencePackageArtifact.artifact_id)
    │
    ▼
WorkpaperArtifact          (parent_artifact_id = ReviewReportArtifact.artifact_id)
    │
    ▼
ReportArtifact             (parent_artifact_id = WorkpaperArtifact.artifact_id)
```

### 5.2 溯源查询

```python
def trace_artifact_chain(
    leaf_artifact_id: str,
    store: ArtifactStore,
) -> list[AuditArtifact]:
    """从叶子 Artifact 追溯到根 Artifact (Planner)。

    Returns:
        按时间顺序排列的 Artifact 列表 [AuditPlanArtifact, ..., leaf]
    """
    chain: list[AuditArtifact] = []
    current_id: str | None = leaf_artifact_id
    visited: set[str] = set()

    while current_id is not None:
        if current_id in visited:
            raise ValueError(f"检测到循环引用: {current_id}")
        visited.add(current_id)

        artifact = store.get(current_id)
        chain.append(artifact)
        current_id = artifact.parent_artifact_id

    chain.reverse()
    return chain
```

### 5.3 完整性校验

```python
def verify_artifact_chain(
    workflow_id: str,
    store: ArtifactStore,
) -> ChainVerification:
    """校验一个 Workflow 的 Artifact 链完整性。

    检查项:
    1. 是否存在 AuditPlanArtifact（根节点，parent_artifact_id = None）
    2. 所有 Artifact 的 parent_artifact_id 能否在链中找到
    3. 链是否覆盖全部预期的 7 种 Artifact 类型
    4. 是否存在循环引用
    """
    ...
```

---

## 6. 附录：完整类型枚举与常量

### 6.1 artifact_type 枚举

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

### 6.2 产出者映射

| artifact_type | created_by | 组件类型 |
|---------------|------------|----------|
| `audit_plan` | `planner` | Agent |
| `knowledge_package` | `knowledge_agent` | Agent |
| `risk_finding` | `risk_agent` | Agent |
| `evidence_package` | `evidence_agent` | Agent |
| `review_report` | `reviewer_agent` | Agent |
| `workpaper` | `workpaper_generator` | Service |
| `report` | `report_generator` | Service |

### 6.3 下游消费矩阵

| 上游 Artifact ↓ / 下游消费者 → | Knowledge Agent | Risk Agent | Evidence Agent | Reviewer Agent | Workpaper Generator | Report Generator |
|-------------------------------|:---:|:---:|:---:|:---:|:---:|:---:|
| `AuditPlanArtifact` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `KnowledgePackageArtifact` | — | ✅ | — | ✅ | ✅ | ✅ |
| `RiskFindingArtifact` | — | — | ✅ | ✅ | ✅ | ✅ |
| `EvidencePackageArtifact` | — | ✅ | — | ✅ | ✅ | ✅ |
| `ReviewReportArtifact` | — | — | — | — | ✅ | ✅ |
| `WorkpaperArtifact` | — | — | — | — | — | ✅ |
| `ReportArtifact` | — | — | — | — | — | — |

> `ReportArtifact` 仅被 Human Reviewer 消费（HITL），不被任何自动化组件消费。

---

> **文档版本：** v3.2 — E0.5 Frozen  
> **最后更新：** 2025-06-15  
> **下次修订：** E3 Agent Core 完成后（如 Agent 职责变更导致 Content Schema 调整，需升级 `schema_version` → `v2`）
