# 1B.1.1 — Ontology Schema (Graph Ready PG)

- **Epic:** E1B — Audit Intelligence Model
- **Labels:** `knowledge`, `ontology`, `core`
- **Depends on:** 无（与 E1A 并行）
- **Estimate:** —

## Description

构建审计本体模型的 PostgreSQL Schema，采用 **Node-Edge 属性图结构**（Graph-Ready：未来可迁 Neo4j，MVP 用 PG）。两张核心表 `ontology_node` 和 `ontology_edge` 共同承载审计领域的全部语义概念及其关系，支撑 Agent 进行结构化多跳推理查询（AuditArea → Risk → Assertion → ProcedureType → EvidenceType → Standard）。

**这是 AuditFlow 与普通 RAG 的分水岭——系统必须具备理解审计语义关系的能力，而非仅做向量相似度检索。**

## Acceptance Criteria

- [ ] `ontology_node` 表创建，含 `node_type` CHECK 约束（AuditArea | Risk | Assertion | ProcedureType | EvidenceType | Standard）
- [ ] `ontology_edge` 表创建，含 `edge_type` CHECK 约束（HAS_RISK | VIOLATES | ADDRESSED_BY | PRODUCES | SUPPORTS | REFERENCES）
- [ ] 节点覆盖 ≥5 AuditArea + 6 Assertion + 5 ProcedureType + 5 EvidenceType
- [ ] 边覆盖全部 6 种 relation 类型
- [ ] 递归 CTE 函数 `get_reasoning_chains(audit_area_label)` ——给定 AuditArea → 返回完整推理链（Risk → Assertion → ProcedureType → EvidenceType → Standard）
- [ ] 数据初始化脚本：YAML → SQL INSERT（`python -m auditflow.tools.import_ontology --dir ontology/chains/`）
- [ ] 索引：`idx_ontology_node_type`、`idx_ontology_node_label_trgm`、`idx_ontology_edge_source`、`idx_ontology_edge_target`
- [ ] `(label, node_type)` 唯一约束防止重复概念
- [ ] `(source_node_id, target_node_id, edge_type)` 唯一约束防止重复边

## I/O Interface

```sql
-- 核心表：ontology_node
CREATE TABLE ontology_node (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_type       VARCHAR(32) NOT NULL,   -- AuditArea | Risk | Assertion | ProcedureType | EvidenceType | Standard
    label           VARCHAR(255) NOT NULL,
    description     TEXT,
    properties      JSONB DEFAULT '{}'::JSONB,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    source          VARCHAR(128),           -- manual | yaml_import | agent_generated
    source_ref      VARCHAR(255),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_ontology_node_type CHECK (
        node_type IN ('AuditArea','Risk','Assertion','ProcedureType','EvidenceType','Standard')
    ),
    CONSTRAINT uq_ontology_node_label_type UNIQUE (label, node_type)
);

-- 核心表：ontology_edge
CREATE TABLE ontology_edge (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_node_id  UUID NOT NULL REFERENCES ontology_node(id),
    target_node_id  UUID NOT NULL REFERENCES ontology_node(id),
    edge_type       VARCHAR(32) NOT NULL,   -- HAS_RISK | VIOLATES | ADDRESSED_BY | PRODUCES | SUPPORTS | REFERENCES
    weight          NUMERIC(3,1) DEFAULT 5.0 NOT NULL,
    properties      JSONB DEFAULT '{}'::JSONB,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    source          VARCHAR(128),
    source_ref      VARCHAR(255),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_ontology_edge_type CHECK (
        edge_type IN ('HAS_RISK','VIOLATES','ADDRESSED_BY','PRODUCES','SUPPORTS','REFERENCES')
    ),
    CONSTRAINT uq_ontology_edge_unique UNIQUE (source_node_id, target_node_id, edge_type)
);

-- 推理链查询函数
CREATE OR REPLACE FUNCTION get_reasoning_chains(
    p_audit_area_label VARCHAR(255)
)
RETURNS TABLE (
    chain_id        TEXT,
    path_depth      INT,
    node_id         UUID,
    node_type       VARCHAR(32),
    node_label      VARCHAR(255),
    edge_type       VARCHAR(32),
    edge_weight     NUMERIC(3,1)
)
LANGUAGE sql STABLE;
```

## Related ADR

- [ADR-002 — 审计本体模型：Graph-Ready PostgreSQL Schema](../architecture/ADR-002-Ontology-Model.md)
