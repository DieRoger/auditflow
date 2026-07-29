# Canonical Audit Schema v1.0

**Status:** Architecture Freeze — 代码实现前不得修改  
**Domain:** Finance  
**Bounded Context:** Finance Data  
**Last Updated:** 2026-07-28

---

## Overview

Canonical Audit Schema 定义 AuditFlow 中所有结构化审计数据的统一表示。

所有 Importer（Excel/CSV/ERP）必须将原始数据映射为下列 Canonical 实体后，才能被 Audit Workflow 消费。

---

## Entities

### Transaction

表示一笔可审计的业务交易。是所有审计程序（截止测试、发生测试、完整性测试）的基本单元。

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `transaction_id` | `UUID` | ✅ | 唯一标识 |
| `transaction_type` | `Enum(SALES, PURCHASE, PAYMENT, RECEIPT, JOURNAL)` | ✅ | 交易类型 |
| `transaction_date` | `Date` | ✅ | 交易日期 |
| `period` | `String(YYYY-MM)` | ✅ | 会计期间 |
| `amount` | `Decimal(18,2)` | ✅ | 交易金额 |
| `currency` | `String(3)` | ⚠️ | 币种（默认 CNY） |
| `party_id` | `UUID` | ⚠️ | 关联 Party |
| `document_refs` | `List[UUID]` | ⚠️ | 引用 Document（发票/合同/发货单） |
| `description` | `Text` | ⚠️ | 交易摘要 |
| `source` | `String` | ✅ | 数据来源标识（ImportSession ID） |

**Invariant**: `transaction_date` 必须是有效日历日期。`period` 必须与 `transaction_date` 所属月份一致。

---

### Document

表示支持审计证据的业务文档。每个 Document 可被多条 Transaction 引用。

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `document_id` | `UUID` | ✅ | 唯一标识 |
| `document_type` | `Enum(INVOICE, DELIVERY, CONTRACT, RECEIPT, PURCHASE_ORDER, SHIPPING)` | ✅ | 文档类型 |
| `document_no` | `String` | ✅ | 文档编号 |
| `document_date` | `Date` | ✅ | 文档日期 |
| `party_id` | `UUID` | ⚠️ | 关联 Party |
| `amount` | `Decimal(18,2)` | ⚠️ | 文档金额 |
| `reference_no` | `String` | ⚠️ | 外部引用号 |

**Invariant**: `document_no` 在同一 `document_type` 内应唯一（软约束）。

---

### Party

表示交易对手方（客户/供应商/员工等）。

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `party_id` | `UUID` | ✅ | 唯一标识 |
| `party_type` | `Enum(CUSTOMER, VENDOR, EMPLOYEE)` | ✅ | 类型 |
| `name` | `String` | ✅ | 名称 |

---

### AccountEntry（预留 v2.0）

Phase 1 只定义接口，不实现。用于后续对接 GL/TB。

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `entry_id` | `UUID` | ✅ | 唯一标识 |
| `account_code` | `String` | ✅ | 科目编码 |
| `debit` | `Decimal(18,2)` | ⚠️ | 借方金额 |
| `credit` | `Decimal(18,2)` | ⚠️ | 贷方金额 |
| `period` | `String(YYYY-MM)` | ✅ | 会计期间 |

---

## Entity Relationships

```
Party (1) ────────────── (N) Transaction
   │                            │
   │                            │ (0..N)
   │                            ▼
   └─────────────────────── Document

AccountEntry (v2.0)
   └── independent of Transaction
```

- **Party → Transaction**: 一个 Party 可以参与多笔交易
- **Transaction → Document**: 一笔交易可以关联多个文档（合同+发票+发货单）
- **Party → Document**: 一个 Party 可以拥有多个文档
- **AccountEntry**: 独立实体，不与 Transaction 直接关联（v2.0）

---

## Schema 使用约束

1. **Transaction 不可变**: 创建后不可修改。如需更正，创建新 Transaction 并标记原记录为 `reversed`（v2.0）。
2. **Document 可关联**: Document 可被多条 Transaction 引用，引用关系存于 `document_refs`。
3. **Party 可合并**: 同一实体以不同名称出现时，合并为一条 Party 记录（v2.0 Deduplication）。
4. **所有金额为 Decimal**: 禁止使用 float。

---

## 扩展点

- `transaction_type` 枚举可扩展：`INVENTORY_ADJUSTMENT`, `PAYROLL`, `TAX`
- `document_type` 枚举可扩展：`BANK_STATEMENT`, `LAWYER_LETTER`, `MINUTES`
- `AccountEntry` 实现后支持 TB/GL 全量导入和比率分析
