# ADR-002：审计本体模型 — Graph-Ready PostgreSQL Schema

- **状态：** 已接受（Architecture Baseline v1.0）
- **日期：** 2026-07-26
- **决策者：** Architecture Gate Review #3
- **影响范围：** E3 Knowledge & Ontology — 审计领域语义推理基础设施

---

## 1. 背景（Context）

AuditFlow 的核心价值主张是**理解审计领域的语义关系**，而非仅仅做通用 RAG（Retrieval-Augmented Generation）。审计工作底稿背后有一套成体系的概念结构：

```
Risk（风险）  ──▶  Assertion（认定）  ──▶  Procedure（程序）  ──▶  Evidence（证据）
```

如果系统不知道"收入确认"（Revenue Recognition）这个审计领域包含哪些固有风险，不知道这些风险违反了哪些管理当局认定（Existence、Accuracy、Cutoff），不知道针对这些认定应采用什么审计程序，不知道每种程序产生什么类型的审计证据——那么 AuditFlow 就退化成了一个**通用文档检索 + LLM 生成**的管道，丧失了审计专业性。

### 1.1 问题诊断

| 缺乏本体模型的后果 | 具体表现 |
|-------------------|---------|
| **检索盲目** | 向量相似度检索返回的是语义相近的文本片段，而非审计逻辑相关的概念。例如查询"收入确认风险"，可能返回与"收入"相关的会计准则条款，而不是与该风险关联的**认定、程序和证据类型**。 |
| **推理断裂** | Agent 无法沿着 Risk → Assertion → Procedure → Evidence 的链条进行多跳推理，每一步都需要重新构造 Prompt 并依赖 LLM 的零样本知识。 |
| **不可解释** | 当系统做出"建议执行函证程序"的决策时，无法追溯到"该程序针对的是应收账款的存在性认定，而该认定又源于虚增收入的风险"。 |
| **扩展困难** | 每次新增审计领域（如新增"长期资产减值"领域），都需要手工编写大量 Prompt 模板，无法通过声明式配置完成。 |

### 1.2 目标

构建一个**轻量级、PostgreSQL 原生、可扩展的审计本体模型**，使 Agent 能够：

1. **结构化查询**审计领域知识：给定一个 AuditArea，查出其所有 Risk → Assertion → ProcedureType → EvidenceType 推理链。
2. **解释推理路径**：每一步推理都能追溯到本体中的节点和边。
3. **声明式扩展**：新增审计领域只需编写 YAML 配置文件，通过导入脚本写入数据库。

---

## 2. 决策（Decision）

采用 **PostgreSQL 关系模型作为本体存储，以节点-边（Node-Edge）图结构组织审计语义**。预留未来迁移至 Neo4j 等专用图数据库的路径（Graph-Ready）。

### 2.1 两张核心表：ontology_node 与 ontology_edge

本体的所有概念存储在 `ontology_node` 表中，所有关系存储在 `ontology_edge` 表中。这是一个经典的**属性图（Property Graph）模型在关系数据库上的投影**。

```
┌──────────────────┐          ┌──────────────────┐
│  ontology_node   │          │  ontology_edge   │
├──────────────────┤          ├──────────────────┤
│ id (PK)          │◀─────────│ source_node_id   │
│ node_type        │          │ target_node_id   │
│ label            │          │ edge_type        │
│ properties       │          │ properties       │
│ description      │          │ weight           │
│ is_active        │          │ is_active        │
│ created_at       │          │ created_at       │
└──────────────────┘          └──────────────────┘
```

### 2.2 节点类型（node_type）

| 节点类型 | 含义 | 示例 |
|---------|------|------|
| `AuditArea` | 审计领域（最高层级概念） | Revenue Recognition、长期资产减值、存货 |
| `Risk` | 该审计领域下的固有风险或舞弊风险 | Aggressive Recognition（激进确认）、Channel Stuffing（渠道压货） |
| `Assertion` | 审计认定（管理层声明） | Existence、Accuracy、Cutoff、Completeness、Valuation |
| `ProcedureType` | 审计程序类型 | Inspection、Confirmation、Recalculation、Inquiry |
| `EvidenceType` | 审计证据类型 | Documentary、External、Physical、Analytical |
| `Standard` | 适用的审计准则或会计准则 | ISA 240、ISA 315、ASC 606、IFRS 15 |

### 2.3 边关系类型（edge_type）

| 边类型 | 方向 | 语义 |
|--------|------|------|
| `HAS_RISK` | AuditArea → Risk | 该审计领域包含哪些风险 |
| `VIOLATES` | Risk → Assertion | 该风险违反（威胁）哪些认定 |
| `ADDRESSED_BY` | Assertion → ProcedureType | 该认定由哪些审计程序应对 |
| `PRODUCES` | ProcedureType → EvidenceType | 该程序产生哪些类型的证据 |
| `SUPPORTS` | EvidenceType → Assertion | 证据反过来支持（证实/证伪）认定（反向弧，增强推理） |
| `REFERENCES` | 任意节点 → Standard | 引用审计准则或会计准则 |

### 2.4 推理链（Reasoning Chain）

推理链是上述节点和边的**有向路径**，定义了从审计领域到证据的完整推理过程。推理链以 YAML 格式定义，通过导入脚本写入数据库。

**一条完整的推理链：**

```
AuditArea              Risk                   Assertion              ProcedureType          EvidenceType
┌──────────────┐ HAS_RISK ┌──────────────┐ VIOLATES ┌──────────────┐ ADDRESSED_BY ┌──────────────┐ PRODUCES ┌──────────────┐
│ Revenue       │─────────▶│ Aggressive   │─────────▶│ Existence    │─────────────▶│ Confirmation │─────────▶│ External     │
│ Recognition   │          │ Recognition  │          │ Accuracy     │              │ Inspection   │          │ Documentary  │
│               │          │              │          │ Cutoff       │              │              │          │              │
└──────────────┘          └──────────────┘          └──────────────┘              └──────────────┘          └──────────────┘
```

### 2.5 MVP 范围：≥5 个 AuditArea

MVP 阶段至少包含以下审计领域，每个领域配备完整的推理链：

1. **Revenue Recognition（收入确认）** — 最高风险领域，几乎每项审计都涉及
2. **Accounts Receivable（应收账款）** — 与收入确认紧密关联
3. **Inventory（存货）** — 涉及存在性、计价、截止等多重认定
4. **Fixed Assets / Long-lived Assets（固定资产/长期资产）** — 涉及减值评估
5. **Accounts Payable / Expenses（应付账款/费用）** — 完整性认定为主

---

## 3. SQL DDL

### 3.1 ontology_node

```sql
-- ============================================================================
-- 审计本体节点表（Graph-Ready）
-- 存储审计领域的所有概念节点：AuditArea、Risk、Assertion、
-- ProcedureType、EvidenceType、Standard
-- ============================================================================

CREATE TABLE ontology_node (
    -- 主键
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 节点分类
    node_type       VARCHAR(32) NOT NULL,
    -- 取值：AuditArea | Risk | Assertion | ProcedureType | EvidenceType | Standard

    -- 节点标签（人类可读，用于 UI 展示和 Prompt 构造）
    label           VARCHAR(255) NOT NULL,

    -- 节点描述（详细说明，供 Agent 在推理时参考）
    description     TEXT,

    -- 扩展属性（JSONB，用于存储该节点特有的元数据）
    -- 例如：Standard 节点的 clause、Assertion 节点的 category 等
    properties      JSONB DEFAULT '{}'::JSONB,

    -- 状态控制
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    -- TRUE  = 当前推理中可用
    -- FALSE = 已弃用但保留历史引用

    -- 来源追溯
    source          VARCHAR(128),
    -- 取值：manual | yaml_import | agent_generated
    source_ref       VARCHAR(255),
    -- 来源引用路径，例如 "ontology/revenue_recognition.yaml"

    -- 时间戳
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- 约束
    CONSTRAINT chk_ontology_node_type CHECK (
        node_type IN (
            'AuditArea', 'Risk', 'Assertion',
            'ProcedureType', 'EvidenceType', 'Standard'
        )
    ),

    -- 同一 node_type 下 label 唯一（避免重复概念）
    CONSTRAINT uq_ontology_node_label_type UNIQUE (label, node_type)
);

-- 索引：按类型查询所有节点
CREATE INDEX idx_ontology_node_type
    ON ontology_node (node_type) WHERE is_active = TRUE;

-- 索引：按标签模糊搜索（Agent 查询时使用）
CREATE INDEX idx_ontology_node_label_trgm
    ON ontology_node USING gin (label gin_trgm_ops);
```

### 3.2 ontology_edge

```sql
-- ============================================================================
-- 审计本体边表（Graph-Ready）
-- 存储节点之间的语义关系，构成推理链
-- ============================================================================

CREATE TABLE ontology_edge (
    -- 主键
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 边的两端
    source_node_id  UUID NOT NULL REFERENCES ontology_node(id),
    target_node_id  UUID NOT NULL REFERENCES ontology_node(id),

    -- 边类型
    edge_type       VARCHAR(32) NOT NULL,
    -- 取值：HAS_RISK | VIOLATES | ADDRESSED_BY | PRODUCES | SUPPORTS | REFERENCES

    -- 边的权重（0.0–10.0，表示关系的强弱）
    -- 用于 Agent 在多个推理路径之间做选择时排序
    weight          NUMERIC(3,1) DEFAULT 5.0 NOT NULL,

    -- 扩展属性（JSONB）
    -- 例如：存储 VIOLATES 边的 "risk_level"、"is_significant_risk" 等
    properties      JSONB DEFAULT '{}'::JSONB,

    -- 状态控制
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,

    -- 来源追溯
    source          VARCHAR(128),
    source_ref       VARCHAR(255),

    -- 时间戳
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- 约束
    CONSTRAINT chk_ontology_edge_type CHECK (
        edge_type IN (
            'HAS_RISK', 'VIOLATES', 'ADDRESSED_BY',
            'PRODUCES', 'SUPPORTS', 'REFERENCES'
        )
    ),

    -- 同一对节点之间，同类型边只能有一条
    CONSTRAINT uq_ontology_edge_unique UNIQUE (source_node_id, target_node_id, edge_type)
);

-- 索引：按源节点查询出边（Agent 前向推理）
CREATE INDEX idx_ontology_edge_source
    ON ontology_edge (source_node_id, edge_type) WHERE is_active = TRUE;

-- 索引：按目标节点查询入边（Agent 反向推理 / 解释）
CREATE INDEX idx_ontology_edge_target
    ON ontology_edge (target_node_id, edge_type) WHERE is_active = TRUE;
```

### 3.3 递归 CTE 推理查询

```sql
-- ============================================================================
-- 从 AuditArea 出发，展开完整的推理链（多跳路径）
-- 返回从 AuditArea 到 EvidenceType 的所有可能路径
-- ============================================================================

CREATE OR REPLACE FUNCTION get_reasoning_chains(
    p_audit_area_label VARCHAR(255)
)
RETURNS TABLE (
    chain_id        TEXT,          -- 推理链唯一标识
    path_depth      INT,           -- 路径深度（跳数）
    node_id         UUID,          -- 节点 ID
    node_type       VARCHAR(32),   -- 节点类型
    node_label      VARCHAR(255),  -- 节点标签
    edge_type       VARCHAR(32),   -- 连接该节点的边类型
    edge_weight     NUMERIC(3,1)   -- 边权重
)
LANGUAGE sql
STABLE
AS $$
    WITH RECURSIVE chain AS (
        -- 基础情况：从 AuditArea 节点开始
        SELECT
            n.id AS node_id,
            n.node_type,
            n.label AS node_label,
            n.id::TEXT AS chain_id,
            0 AS path_depth,
            NULL::VARCHAR(32) AS edge_type,
            NULL::NUMERIC(3,1) AS edge_weight
        FROM ontology_node n
        WHERE n.node_type = 'AuditArea'
          AND n.label = p_audit_area_label
          AND n.is_active = TRUE

        UNION ALL

        -- 递归步骤：沿边展开下一层
        SELECT
            next_n.id AS node_id,
            next_n.node_type,
            next_n.label AS node_label,
            c.chain_id || '→' || next_n.id::TEXT AS chain_id,
            c.path_depth + 1 AS path_depth,
            e.edge_type,
            e.weight AS edge_weight
        FROM chain c
        JOIN ontology_edge e
            ON e.source_node_id = c.node_id
           AND e.is_active = TRUE
        JOIN ontology_node next_n
            ON next_n.id = e.target_node_id
           AND next_n.is_active = TRUE
        WHERE c.path_depth < 6   -- 安全上限：最多 6 跳（AuditArea → Risk → Assertion → ProcedureType → EvidenceType → Standard）
    )
    SELECT
        chain.chain_id,
        chain.path_depth,
        chain.node_id,
        chain.node_type,
        chain.node_label,
        chain.edge_type,
        chain.edge_weight
    FROM chain
    ORDER BY chain_id, path_depth;
$$;
```

---

## 4. 推理链 YAML 定义示例

以下展示一条完整的推理链定义（YAML 格式），导入脚本读取后写入 `ontology_node` 和 `ontology_edge` 表。

### 4.1 示例：Revenue Recognition（收入确认）

```yaml
# ============================================================================
# 推理链定义：Revenue Recognition（收入确认）
# 文件位置：ontology/chains/revenue_recognition.yaml
# 导入方式：python -m auditflow.tools.import_ontology --file <this_file>
# ============================================================================

chain_name: "Revenue Recognition — 完整审计推理链"
chain_id: "REV_REC_001"
audit_area: "Revenue Recognition"
version: "1.0"
author: "Architecture Gate Review #3"

# ─── 节点定义 ───────────────────────────────────────────────────────────────

nodes:
  # --- AuditArea ---
  - id: "rev-rec-area"
    node_type: "AuditArea"
    label: "Revenue Recognition"
    description: >
      收入确认审计领域。涵盖与客户合同相关的收入确认时点、
      金额和分类。适用 ASC 606 / IFRS 15。

  # --- Risks ---
  - id: "risk-aggressive-recognition"
    node_type: "Risk"
    label: "Aggressive Recognition"
    description: >
      管理层可能在收入满足确认条件之前提前确认收入，
      以美化财务报表。常见手法包括：在发货前确认、
      在服务未完成时确认、渠道压货（Channel Stuffing）。
    properties:
      risk_category: "fraud_risk"
      is_significant_risk: true
      risk_level: "high"

  - id: "risk-side-agreements"
    node_type: "Risk"
    label: "Side Agreements"
    description: >
      管理层可能通过未披露的附属协议修改销售条款，
      如授予退货权、价格保护或延长付款期限，
      导致表面上的销售实质上不满足收入确认条件。
    properties:
      risk_category: "fraud_risk"
      is_significant_risk: true
      risk_level: "high"

  - id: "risk-cutoff-errors"
    node_type: "Risk"
    label: "Cutoff Errors"
    description: >
      收入可能被记录在错误的会计期间，
      尤其是临近资产负债表日的交易。
    properties:
      risk_category: "error_risk"
      is_significant_risk: false
      risk_level: "medium"

  # --- Assertions ---
  - id: "assertion-existence"
    node_type: "Assertion"
    label: "Existence"
    description: >
      已记录的收入交易确实发生（不是虚构销售）。
    properties:
      assertion_category: "transaction_level"

  - id: "assertion-accuracy"
    node_type: "Assertion"
    label: "Accuracy"
    description: >
      收入交易按正确的金额记录（无多记或少记）。
    properties:
      assertion_category: "transaction_level"

  - id: "assertion-cutoff"
    node_type: "Assertion"
    label: "Cutoff"
    description: >
      收入交易记录在正确的会计期间。
    properties:
      assertion_category: "transaction_level"

  - id: "assertion-completeness"
    node_type: "Assertion"
    label: "Completeness"
    description: >
      所有应记录的收入交易均已记录（无遗漏）。
    properties:
      assertion_category: "transaction_level"

  # --- ProcedureTypes ---
  - id: "procedure-confirmation"
    node_type: "ProcedureType"
    label: "Confirmation"
    description: >
      向客户的客户（外部第三方）直接函证应收账款余额和交易条款。
      是验证 Existence 和 Accuracy 最有力的程序之一。
    properties:
      procedure_family: "substantive"
      reliability: "high"

  - id: "procedure-inspection"
    node_type: "ProcedureType"
    label: "Inspection"
    description: >
      检查支持销售交易的原始凭证，包括：
      销售合同、发货单、客户签收单、验收报告等。
    properties:
      procedure_family: "substantive"
      reliability: "high"

  - id: "procedure-cutoff-testing"
    node_type: "ProcedureType"
    label: "Cutoff Testing"
    description: >
      选取资产负债表日前后各 N 天的交易样本，
      检查其是否记录在正确的会计期间。
    properties:
      procedure_family: "substantive"
      reliability: "high"

  - id: "procedure-analytical-review"
    node_type: "ProcedureType"
    label: "Analytical Review"
    description: >
      分析收入趋势、毛利率波动、与行业基准的对比，
      识别异常波动和潜在错报迹象。
    properties:
      procedure_family: "substantive_analytical"
      reliability: "medium"

  # --- EvidenceTypes ---
  - id: "evidence-external"
    node_type: "EvidenceType"
    label: "External Evidence"
    description: >
      来源于独立第三方的证据，可靠性最高。
      包括：银行函证回函、客户确认函回函、
      律师询证函回函、监管机构文件等。
    properties:
      reliability: "high"
      source: "external_third_party"

  - id: "evidence-documentary"
    node_type: "EvidenceType"
    label: "Documentary Evidence"
    description: >
      被审计单位内部生成的书面证据。可靠性取决于
      被审计单位内部控制的有效性。
      包括：销售合同、发票、发货单、验收单、
      董事会会议纪要等。
    properties:
      reliability: "medium"
      source: "internal"

  - id: "evidence-analytical"
    node_type: "EvidenceType"
    label: "Analytical Evidence"
    description: >
      通过分析程序得出的证据（比率分析、趋势分析、
      回归分析等）。通常作为辅助证据使用。
    properties:
      reliability: "medium"
      source: "auditor_generated"

  # --- Standards ---
  - id: "standard-isa240"
    node_type: "Standard"
    label: "ISA 240"
    description: >
      审计准则第 240 号——审计师在财务报表审计中
      对舞弊的责任。
    properties:
      standard_body: "IAASB"
      topic: "fraud_responsibility"

  - id: "standard-isa315"
    node_type: "Standard"
    label: "ISA 315 (Revised 2019)"
    description: >
      审计准则第 315 号（2019 修订版）——识别和评估
      重大错报风险。
    properties:
      standard_body: "IAASB"
      topic: "risk_assessment"

  - id: "standard-asc606"
    node_type: "Standard"
    label: "ASC 606"
    description: >
      会计准则汇编第 606 号——与客户合同产生的收入。
      五步法收入确认模型。
    properties:
      standard_body: "FASB"
      topic: "revenue_recognition"

# ─── 边定义 ─────────────────────────────────────────────────────────────────

edges:
  # AuditArea → Risk（HAS_RISK）
  - source: "rev-rec-area"
    target: "risk-aggressive-recognition"
    edge_type: "HAS_RISK"
    weight: 10.0
    properties:
      is_primary: true
      rationale: "收入确认是舞弊高风险领域；激进确认是最常见的收入舞弊手段"

  - source: "rev-rec-area"
    target: "risk-side-agreements"
    edge_type: "HAS_RISK"
    weight: 8.5
    properties:
      is_primary: true
      rationale: "附属协议使表面销售实质上不成立，需要额外审计程序发现"

  - source: "rev-rec-area"
    target: "risk-cutoff-errors"
    edge_type: "HAS_RISK"
    weight: 7.0
    properties:
      is_primary: false
      rationale: "截止错误是常见错报，但通常非舞弊性质"

  # Risk → Assertion（VIOLATES）
  - source: "risk-aggressive-recognition"
    target: "assertion-existence"
    edge_type: "VIOLATES"
    weight: 10.0
    properties:
      rationale: "提前确认的收入可能根本不存在"

  - source: "risk-aggressive-recognition"
    target: "assertion-accuracy"
    edge_type: "VIOLATES"
    weight: 8.0
    properties:
      rationale: "提前确认可能导致金额计量不准确"

  - source: "risk-aggressive-recognition"
    target: "assertion-cutoff"
    edge_type: "VIOLATES"
    weight: 9.0
    properties:
      rationale: "提前确认本质上是截止问题"

  - source: "risk-side-agreements"
    target: "assertion-existence"
    edge_type: "VIOLATES"
    weight: 9.0
    properties:
      rationale: "附属协议可能表明交易实质上不成立"

  - source: "risk-side-agreements"
    target: "assertion-accuracy"
    edge_type: "VIOLATES"
    weight: 7.0
    properties:
      rationale: "退货权或价格保护影响最终交易金额"

  - source: "risk-cutoff-errors"
    target: "assertion-cutoff"
    edge_type: "VIOLATES"
    weight: 10.0
    properties:
      rationale: "截止错误的直接后果是跨期错报"

  - source: "risk-cutoff-errors"
    target: "assertion-completeness"
    edge_type: "VIOLATES"
    weight: 6.0
    properties:
      rationale: "截止错误可能导致部分交易遗漏"

  # Assertion → ProcedureType（ADDRESSED_BY）
  - source: "assertion-existence"
    target: "procedure-confirmation"
    edge_type: "ADDRESSED_BY"
    weight: 10.0
    properties:
      rationale: "外部函证是验证存在性的黄金标准程序"

  - source: "assertion-existence"
    target: "procedure-inspection"
    edge_type: "ADDRESSED_BY"
    weight: 8.0
    properties:
      rationale: "检查原始凭证可验证交易真实性"

  - source: "assertion-accuracy"
    target: "procedure-inspection"
    edge_type: "ADDRESSED_BY"
    weight: 9.0
    properties:
      rationale: "核对合同金额与入账金额验证准确性"

  - source: "assertion-accuracy"
    target: "procedure-confirmation"
    edge_type: "ADDRESSED_BY"
    weight: 8.0
    properties:
      rationale: "函证可同时验证金额和交易条款"

  - source: "assertion-cutoff"
    target: "procedure-cutoff-testing"
    edge_type: "ADDRESSED_BY"
    weight: 10.0
    properties:
      rationale: "截止测试直接针对跨期错报"

  - source: "assertion-cutoff"
    target: "procedure-inspection"
    edge_type: "ADDRESSED_BY"
    weight: 7.0
    properties:
      rationale: "检查发货单日期可验证收入确认时点"

  - source: "assertion-completeness"
    target: "procedure-analytical-review"
    edge_type: "ADDRESSED_BY"
    weight: 7.0
    properties:
      rationale: "分析程序可识别异常的收入缺口，提示遗漏"

  # ProcedureType → EvidenceType（PRODUCES）
  - source: "procedure-confirmation"
    target: "evidence-external"
    edge_type: "PRODUCES"
    weight: 10.0
    properties:
      rationale: "函证回函是来自独立第三方的外部证据"

  - source: "procedure-inspection"
    target: "evidence-documentary"
    edge_type: "PRODUCES"
    weight: 10.0
    properties:
      rationale: "凭证检查产生被审计单位内部书面证据"

  - source: "procedure-cutoff-testing"
    target: "evidence-documentary"
    edge_type: "PRODUCES"
    weight: 9.0
    properties:
      rationale: "截止测试依赖发货单等内部凭证"

  - source: "procedure-analytical-review"
    target: "evidence-analytical"
    edge_type: "PRODUCES"
    weight: 10.0
    properties:
      rationale: "分析程序产生分析性证据"

  # EvidenceType → Assertion（SUPPORTS — 反向弧）
  - source: "evidence-external"
    target: "assertion-existence"
    edge_type: "SUPPORTS"
    weight: 10.0
    properties:
      rationale: "外部函证回函直接证实交易存在"

  - source: "evidence-documentary"
    target: "assertion-accuracy"
    edge_type: "SUPPORTS"
    weight: 8.0
    properties:
      rationale: "合同和发票支撑金额准确性"

  # 任意节点 → Standard（REFERENCES）
  - source: "risk-aggressive-recognition"
    target: "standard-isa240"
    edge_type: "REFERENCES"
    weight: 5.0
    properties:
      rationale: "ISA 240 要求审计师识别和应对舞弊风险"

  - source: "risk-aggressive-recognition"
    target: "standard-isa315"
    edge_type: "REFERENCES"
    weight: 5.0
    properties:
      rationale: "ISA 315 要求识别重大错报风险，包括收入确认"

  - source: "rev-rec-area"
    target: "standard-asc606"
    edge_type: "REFERENCES"
    weight: 5.0
    properties:
      rationale: "ASC 606 定义了收入确认的五步法模型"
```

### 4.2 导入脚本调用方式

```bash
# 导入单个推理链 YAML 文件
python -m auditflow.tools.import_ontology \
    --file ontology/chains/revenue_recognition.yaml \
    --db-url postgresql://user:pass@localhost:5432/auditflow

# 批量导入所有推理链
python -m auditflow.tools.import_ontology \
    --dir ontology/chains/ \
    --db-url postgresql://user:pass@localhost:5432/auditflow
```

---

## 5. MVP 推理链清单

MVP 阶段必须实现的 5 个 AuditArea 及其核心推理路径（完整 YAML 定义按 4.1 格式编写）：

| # | AuditArea | 核心 Risk → Assertion 路径 | 关键 ProcedureType |
|---|-----------|---------------------------|-------------------|
| 1 | **Revenue Recognition** | Aggressive Recognition → Existence/Accuracy/Cutoff | Confirmation、Inspection、Cutoff Testing |
| 2 | **Accounts Receivable** | Overstatement → Existence/Valuation | Confirmation、Aging Analysis |
| 3 | **Inventory** | Obsolescence → Valuation；Theft → Existence | Physical Count、NRV Testing |
| 4 | **Fixed Assets** | Impairment not recognized → Valuation | Recoverability Test、Appraisal |
| 5 | **Accounts Payable** | Unrecorded Liabilities → Completeness | Search for Unrecorded Liabilities、Confirmation |

---

## 6. 后果（Consequences）

### 6.1 积极后果

- **语义推理能力：** Agent 可以通过查询本体（`get_reasoning_chains`）获取结构化的审计领域知识，而非仅依赖向量相似度检索。例如，Agent 被告知审计领域为"Revenue Recognition"后，可以：
  1. 查出所有关联 Risks
  2. 对每个 Risk，查出被违反的 Assertions
  3. 对每个 Assertion，查出推荐的 ProcedureTypes
  4. 对每个 ProcedureType，查出其产生的 EvidenceTypes
  5. 形成完整的审计程序矩阵（Risk × Assertion × Procedure × Evidence）
- **可解释性：** 每一项审计决策都可以沿着本体中的边追溯到最上游的风险和准则依据。例如："建议执行函证程序，因为收入确认领域存在激进确认风险，该风险威胁存在性认定，而函证是应对存在性认定的标准程序（参考 ISA 240）"。
- **声明式扩展：** 新增审计领域只需编写 YAML 文件 → 运行导入脚本。无需修改任何 Agent 代码或 Prompt 模板。
- **Graph-Ready：** `ontology_node` 和 `ontology_edge` 两张表的结构与属性图模型（Property Graph Model）完全对应。未来如需迁移至 Neo4j，迁移脚本复杂度极低（每个节点映射为一个 Vertex，每条边映射为一个 Relationship）。
- **后向兼容：** 现有向量检索路径完全保留。本体查询作为**增强层**叠加在向量检索之上——Agent 可以同时从本体获取结构化知识和从向量数据库获取语义相似文档。

### 6.2 权衡与代价

- **初期建设成本：** 每个 AuditArea 需要领域专家（SME）编写完整的推理链 YAML。5 个 MVP AuditArea 预计需要 3–5 个工作日。
- **维护成本：** 审计准则修订时（如 ISA 315 Revised 2019 替代旧版），需要更新 YAML 并重新导入。通过 `is_active = FALSE` 标记旧节点，可保留历史推理路径的追溯能力。
- **覆盖范围有限：** MVP 的 5 个 AuditArea 仅覆盖最常见的高风险领域。对于非标准行业（如保险、矿业），Agent 仍然回退到纯向量检索模式。解决方式：本体模型的 `weight` 字段允许 Agent 区分"强推荐"（weight ≥ 8）和"弱参考"（weight < 5），未覆盖领域自动走弱参考路径。
- **图查询性能：** 递归 CTE 在 PostgreSQL 上对于深度 ≤ 6 的路径查询性能可接受（预计 < 50ms）。如果本体规模增长到数百个 AuditArea，建议迁移至 Neo4j 并利用其原生图遍历引擎。

### 6.3 与 Issue E3 的关系

本 ADR 是对 `ISSUES.md` 中 Epic 3（Knowledge & Ontology）的正式架构决策记录，具体覆盖：

- **E3.1 本体模型设计** — 节点类型、边类型、推理链结构
- **E3.2 YAML 导入工具** — `import_ontology` 脚本的接口定义
- **E3.3 Agent 本体查询接口** — `get_reasoning_chains` 函数的契约

---

## 7. 参考

- [ISA 240 — The Auditor's Responsibilities Relating to Fraud in an Audit of Financial Statements](https://www.iaasb.org/publications/isa-240-revised-auditors-responsibilities-relating-fraud-audit-financial-statements)
- [ISA 315 (Revised 2019) — Identifying and Assessing the Risks of Material Misstatement](https://www.iaasb.org/publications/isa-315-revised-2019-identifying-and-assessing-risks-material-misstatement)
- [ASC 606 — Revenue from Contracts with Customers](https://fasb.org/Page/PageContent?PageId=/standards/codification/asc606.html)
- [IFRS 15 — Revenue from Contracts with Customers](https://www.ifrs.org/issued-standards/list-of-standards/ifrs-15-revenue-from-contracts-with-customers/)
- [AuditFlow ISSUES.md §Epic 3](../ISSUES.md)
- [ADR-001: Architecture Baseline v1.0](./ADR-001-Architecture-Baseline.md)
- [Property Graph Model — ISO GQL Standard](https://www.iso.org/standard/76120.html)

---

> **文档版本：** v1.0 — Architecture Baseline v1.0 冻结  
> **下次修订：** E3 完成后（根据实际 YAML 导入工具反馈调整节点属性 schema）
