# Import Framework v1.0

**Status:** Architecture Freeze — 代码实现前不得修改  
**Bounded Context:** Import  
**Domain:** Import（非 Finance Domain）  
**Last Updated:** 2026-07-28

---

## Overview

Import Framework 负责将外部数据（Excel/CSV/ERP Export）导入 AuditFlow。

它属于 **Import Context**，不是 Finance Domain。ImportRecord 中 `raw_data` 永久保存原始数据，支持在不重新上传的情况下修改 Mapping 并重新生成 Canonical 实体。

---

## Architecture

```
Upload File
      │
      ▼
ImportSession（一次上传）
      │
      ├──────────────┐
      ▼              ▼
ImportRecord     MappingProfile
（每一行原始数据）  （本次使用的字段映射）
      │
      ▼
Validation
      │
      ▼
Canonical Entity (Transaction / Document / Party)
      │
      ▼
Audit Engine
```

---

## Entities

### ImportSession（聚合根）

表示一次完整的数据导入操作。

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `session_id` | `UUID` | ✅ | 唯一标识 |
| `filename` | `String` | ✅ | 原始文件名 |
| `uploaded_at` | `DateTime` | ✅ | 上传时间 |
| `uploaded_by` | `String` | ✅ | 上传人 |
| `source_type` | `Enum(EXCEL, CSV, ERP_EXPORT)` | ✅ | 数据源类型 |
| `status` | `Enum(PENDING, MAPPING, VALIDATING, COMPLETE, PARTIAL, FAILED)` | ✅ | 导入状态 |
| `mapping_profile_id` | `UUID` | ⚠️ | 使用的 MappingProfile |
| `row_count` | `Int` | ✅ | 总行数 |
| `valid_count` | `Int` | ✅ | 通过验证的行数 |

**状态机**:

```
PENDING → MAPPING → VALIDATING → COMPLETE（全部行通过）
                              → PARTIAL（部分行通过）
                              → FAILED（全部行失败）
```

---

### ImportRecord（每一行原始数据）

保存 Excel 的每一行原始数据。**raw_data 永不修改**。

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `record_id` | `UUID` | ✅ | 唯一标识 |
| `session_id` | `UUID` | ✅ | 所属 ImportSession |
| `row_number` | `Int` | ✅ | 原始行号（1-based） |
| `raw_data` | `JSON` | ✅ | 原始完整数据（永不修改） |
| `status` | `Enum(PENDING, VALID, FAILED, DUPLICATE)` | ✅ | 验证状态 |
| `validation_errors` | `List[String]` | ⚠️ | 验证失败原因列表 |
| `canonical_refs` | `JSON { type: "transaction", id: UUID }` | ⚠️ | 生成的 Canonical 实体引用 |

**raw_data 示例**:

```json
{
  "销售日期": "2025-12-31",
  "客户名称": "ABC Manufacturing",
  "销售金额": "10,000.00",
  "发票号": "INV-2025-001",
  "发货日期": "2026-01-02"
}
```

**关键设计决策**: `raw_data` 与 ImportRecord 同生命周期。Mapping 修改后，直接从 `raw_data` 重新生成 Canonical Transaction，无需重新上传文件。

---

### MappingProfile

定义 Excel 列到 Canonical Schema 的映射关系。

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `profile_id` | `UUID` | ✅ | 唯一标识 |
| `name` | `String` | ✅ | "Firm A Revenue Template" |
| `mappings` | `JSON` | ✅ | 字段映射定义 |
| `created_at` | `DateTime` | ✅ | — |

**mappings 结构**:

```json
{
  "transaction_date": {
    "aliases": ["销售日期", "Date", "Sales Date", "transaction_date"],
    "required": true,
    "format": "YYYY-MM-DD"
  },
  "amount": {
    "aliases": ["金额", "Amount", "Sales Amount", "amount"],
    "required": true,
    "format": "Decimal"
  },
  "party_name": {
    "aliases": ["客户名称", "Customer", "Party", "customer"],
    "required": true
  },
  "invoice_no": {
    "aliases": ["发票号", "Invoice No", "Invoice_No"],
    "required": false
  },
  "shipping_date": {
    "aliases": ["发货日期", "Ship Date", "Shipping_Date"],
    "required": false,
    "format": "YYYY-MM-DD"
  }
}
```

---

### ValidationResult

汇总一次 ImportSession 的验证结果。

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | `UUID` | 所属 Session |
| `total_rows` | `Int` | 总行数 |
| `valid_rows` | `Int` | 通过数 |
| `failed_rows` | `Int` | 失败数 |
| `errors` | `List[{row, field, message}]` | 逐行错误详情 |

---

## 关键关系

```
ImportSession (1)
    ├── (N) ImportRecord
    └── (1) MappingProfile

ImportRecord
    └── (0..1) Canonical Entity (Transaction / Document / Party)
```

**为什么不是 1:1**: Validation 可能失败（日期为空、金额非数字），此时 ImportRecord 存在但无对应 Canonical Entity。

**为什么不是 0..N (MVP)**: Phase A 只支持 1 ImportRecord → 0..1 Transaction。将来 ERP 一行凭证拆为借贷双方时扩展为 0..N。

---

## Lifecycle

### 1. Upload
```
User → Upload Excel → Create ImportSession(status=PENDING)
```

### 2. Preview
```
ImportSession → Parse Excel → Create ImportRecord（每行，status=PENDING）
User → Preview first 5 rows
```

### 3. Mapping
```
User → Select column mapping（或选择已有 MappingProfile）
ImportSession → status=MAPPING
```

### 4. Validation
```
For each ImportRecord:
    validate date format, amount is numeric, required fields present
    → status=VALID | FAILED
ImportSession → status=COMPLETE | PARTIAL | FAILED
```

### 5. Import
```
For each VALID ImportRecord:
    create Canonical Transaction + Document + Party
    → ImportRecord.canonical_refs = {type: "transaction", id: ...}
```

### 6. Re-Map（无需重新上传）
```
User → Modify MappingProfile
→ For each ImportRecord with canonical_refs:
    delete old Canonical Transaction
    re-run Validation + Import
```

---

## 与 Finance Domain 的边界

| Import Context | Finance Domain |
|----------------|---------------|
| ImportSession | — |
| ImportRecord | Transaction（0..1 引用） |
| MappingProfile | — |
| ValidationResult | — |
| — | Document |
| — | Party |

ImportRecord 通过 `canonical_refs` 引用 Finance Domain 实体，**不持有 Canonical 实体本身**。

---

## Excel Adapter（Phase A MVP）

### 支持的格式

- `.xlsx`（openpyxl）
- `.xls`（xlrd）
- `.csv`（pandas）

### 解析策略

1. 读取第一行作为列名
2. 跳过空行
3. 每行生成一个 `ImportRecord`（raw_data=该行全部列的 JSON）
4. 表格/数值列转为字符串存储

### 示例

输入 Excel：

| 销售日期 | 客户 | 金额 | 发票号 | 发货日期 |
|---------|------|------|--------|---------|
| 2025-12-31 | ABC | 10000 | INV-001 | 2026-01-02 |

生成的 ImportRecord：

```json
{
  "record_id": "rec_abc123",
  "session_id": "sess_xyz",
  "row_number": 1,
  "raw_data": {
    "销售日期": "2025-12-31",
    "客户": "ABC",
    "金额": "10000",
    "发票号": "INV-001",
    "发货日期": "2026-01-02"
  },
  "status": "PENDING"
}
```

---

## 扩展点

- `source_type` 扩展：`SAP_EXPORT`, `KINGDEE_EXPORT`, `YONYOU_EXPORT`
- `MappingProfile` 增加 LLM Suggestion（Phase B）
- `ImportRecord → 0..N` Canonical Objects（Phase 3，ERP 凭证拆分）
