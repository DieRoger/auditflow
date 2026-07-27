# 1B.1.2 — Reasoning Chains 定义

- **Epic:** E1B — Audit Intelligence Model
- **Labels:** `knowledge`, `ontology`, `core`
- **Depends on:** 1B.1.1
- **Estimate:** —

## Description

以 YAML 格式定义 ≥5 条完整的审计推理链（Reasoning Chain），每条链覆盖完整的 Risk → Assertion → ProcedureType → EvidenceType → Standard 路径。推理链是 Ontology Schema 的语义内容——节点和边提供数据结构，推理链提供具体的审计领域知识。

推理链通过 `import_ontology` 脚本写入 `ontology_node` 和 `ontology_edge` 表，使 Agent 能够通过 `get_reasoning_chains()` 函数按 AuditArea 查询结构化推理路径。

## Acceptance Criteria

- [ ] ≥5 条 Reasoning Chain，每条含完整 Risk → Assertion → Procedure → Evidence → Standard 链路
- [ ] YAML 格式符合 `import_ontology` 脚本的输入规范（nodes + edges 双段结构）
- [ ] 覆盖以下 5 个 AuditArea（MVP 最低要求）：

| # | AuditArea | 核心 Risk → Assertion | 关键 ProcedureType |
|---|-----------|----------------------|-------------------|
| 1 | Revenue Recognition | Aggressive Recognition → Existence/Accuracy/Cutoff | Confirmation、Inspection、Cutoff Testing |
| 2 | Accounts Receivable | Overstatement → Existence/Valuation | Confirmation、Aging Analysis |
| 3 | Inventory | Obsolescence → Valuation；Theft → Existence | Physical Count、NRV Testing |
| 4 | Fixed Assets | Impairment not recognized → Valuation | Recoverability Test、Appraisal |
| 5 | Accounts Payable | Unrecorded Liabilities → Completeness | Search for Unrecorded Liabilities、Confirmation |

- [ ] 每条链的边附带 `weight`（0.0–10.0）和 `properties.rationale`（推理依据）
- [ ] 所有 Standard 节点正确引用 ISA 240 / ISA 315 / ASC 606 / IFRS 15 等准则
- [ ] YAML 文件存放于 `ontology/chains/` 目录，一个 AuditArea 一个文件

## I/O Interface

```yaml
# knowledge/ontology/reasoning_chains.yaml（概念示例）
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

```bash
# 导入命令
python -m auditflow.tools.import_ontology \
    --dir ontology/chains/ \
    --db-url postgresql://user:pass@localhost:5432/auditflow
```

## Related ADR

- [ADR-002 — 审计本体模型：Graph-Ready PostgreSQL Schema](../architecture/ADR-002-Ontology-Model.md)（§4 完整 YAML 示例、§5 MVP 推理链清单）
