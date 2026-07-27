# AuditFlow Benchmark Dataset 规范

> **版本:** v1.0
> **对应 Epic:** E7 — Benchmark Expansion
> **维护者:** AuditFlow 核心团队
> **最后更新:** 2026-01

---

## 目录

1. [概述](#1-概述)
2. [Benchmark YAML Schema](#2-benchmark-yaml-schema)
3. [七大审计领域](#3-七大审计领域)
4. [案例结构详解](#4-案例结构详解)
5. [Baseline 对比与优化门禁](#5-baseline-对比与优化门禁)
6. [CI 集成](#6-ci-集成)
7. [扩展计划](#7-扩展计划)

---

## 1. 概述

AuditFlow Benchmark Dataset 是系统的**核心评估资产**，用于量化衡量审计 Agent 链条（Planner → Knowledge → Risk → Evidence → Reviewer）在真实审计场景下的表现。数据集由 **20 个精心设计的审计案例** 组成，覆盖 **7 大审计高风险领域**，每个案例均包含模拟客户文档、结构化财务数据输入、标注化的期望输出以及多维度评估指标。

### 1.1 设计原则

| 原则 | 说明 |
|------|------|
| **标准化** | 所有案例遵循统一的 YAML Schema，确保 Evaluation Runner 可自动化执行 |
| **可复现** | 每个案例包含确定的 `input` 和可验证的 `expected`，支持 CI 中批量回归 |
| **覆盖度** | 20 个案例覆盖 7 个领域、≥5 个 Ontology Reasoning Chain（来自 E1B） |
| **可扩展** | 通过追加 `benchmark/{scenario}/benchmark.yaml` 即可添加新场景 |
| **版本化** | Benchmark 数据本身受 Git 版本控制，与 Prompt 版本对应 |

### 1.2 存储结构

```
benchmark/
├── revenue_recognition/
│   ├── benchmark.yaml              # 5 cases
│   └── documents/
│       ├── rev_001_annual_report.pdf
│       ├── rev_001_sales_contract.pdf
│       ├── rev_002_shipping_log.xlsx
│       └── ...
├── ar_impairment/
│   ├── benchmark.yaml              # 3 cases
│   └── documents/
├── inventory_valuation/
│   ├── benchmark.yaml              # 3 cases
│   └── documents/
├── expense_cutoff/
│   ├── benchmark.yaml              # 3 cases
│   └── documents/
├── fixed_asset/
│   ├── benchmark.yaml              # 2 cases
│   └── documents/
├── control_testing/
│   ├── benchmark.yaml              # 2 cases
│   └── documents/
├── fraud_risk/
│   ├── benchmark.yaml              # 2 cases
│   └── documents/
└── README.md
```

每个 `benchmark.yaml` 是一个自包含的评估单元，可以被 `EvaluationRunner` 独立加载和执行。模拟文档（PDF、Excel 等）放置在对应的 `documents/` 子目录中。

---

## 2. Benchmark YAML Schema

### 2.1 顶层结构

```yaml
# benchmark/{scenario}/benchmark.yaml
name: string                    # 数据集名称，例如 "revenue_audit_v1"
scenario: string                # 场景描述，例如 "Revenue Recognition Audit"
version: string                 # Schema 版本，当前为 "1.0"
created_at: datetime            # ISO 8601 创建时间
domain: string                  # 所属审计领域
cases: list[BenchmarkCase]      # 案例列表
```

### 2.2 BenchmarkCase 完整定义

```yaml
cases:
  - id: rev_001                           # 全局唯一 ID，格式: {domain_short}_{NNN}
    description: >                        # 用例描述（中文），说明审计场景与风险本质
      激进收入确认 — 被审计单位年度收入增长 45%，远高于行业均值 10%，
      同时应收账款周转天数从 90 天上升至 120 天。
    severity: HIGH                        # 预期严重程度: CRITICAL | HIGH | MEDIUM | LOW

    # ─── 模拟文档清单 ───
    documents:
      - file: annual_report_sample.pdf
        description: "2025 年度财务报告（含附注）"
        pages: [24, 35, 42]              # 关键页码（可选，用于定向检索验证）
      - file: sales_contract_sample.pdf
        description: "Q4 大额销售合同样本"
      - file: ar_aging_report.xlsx
        description: "应收账款账龄分析表"

    # ─── 结构化输入数据 ───
    input:
      financial_data:
        revenue_growth: "45%"             # 年度收入增长率
        industry_avg_growth: "10%"        # 行业平均增长率
        receivable_days: 120              # 应收账款周转天数
        receivable_days_prior: 90         # 上期应收账款周转天数
        revenue_q4_ratio: "42%"           # Q4 收入占全年比例
        gross_margin_change: "-3.2pp"     # 毛利率变动（百分点）
      non_financial:
        management_comp_tied_to_revenue: true  # 管理层薪酬是否与收入挂钩
        auditor_change: false

    # ─── 标注期望输出 ───
    expected:
      risks:
        - area: Revenue Recognition
          severity: HIGH
          probability: 0.75              # 0.0 ~ 1.0
          indicators:
            - "revenue_growth_3x_industry_avg"
            - "receivable_days_increased_gt_30pct"
            - "q4_revenue_concentration"
            - "gross_margin_decline_with_revenue_surge"
          description: >
            收入增长率远超行业均值，伴随应收账款周转天数显著延长及
            Q4 收入高度集中，存在提前确认收入的重大风险。

      assertions:
        - Existence       # 交易是否真实发生
        - Accuracy        # 金额是否准确
        - Cutoff          # 是否记录在正确期间

      procedures:
        - type: Inspection
          target: sales_contracts
          description: "抽查年末前 15 天大额销售合同，核对发货单日期与收入确认日期"
          sample_size: 10
        - type: Confirmation
          target: top5_customers
          description: "对前 5 大客户执行积极函证，确认交易金额与条款"
        - type: AnalyticalProcedure
          target: revenue_trend
          description: "按月分析收入趋势，识别异常波动月份"

      evidence_min_count: 3              # 最少证据数量要求

      related_standards:
        - standard: IFRS 15
          paragraphs: ["¶27", "¶31", "¶B42"]
          topic: "Revenue recognition — performance obligations"
        - standard: ISA 240
          paragraphs: ["¶32", "¶A1-A7"]
          topic: "Fraud risk — revenue recognition"
        - standard: ISA 500
          paragraphs: ["¶6"]
          topic: "Audit evidence — sufficiency"

    # ─── 评估指标配置 ───
    evaluation:
      primary_metric: risk_classification_accuracy
      secondary_metrics:
        - citation_completeness
        - procedure_coverage
        - reasoning_quality
        - severity_accuracy
      thresholds:
        risk_classification_accuracy: 0.80
        citation_completeness: 0.70
        procedure_coverage: 0.60
        reasoning_quality: 0.60
      weight: 1.0                        # 案例在聚合评分中的权重（默认 1.0）
```

### 2.3 Schema 字段说明

| 字段路径 | 类型 | 必填 | 说明 |
|----------|------|------|------|
| `cases[].id` | string | ✅ | 全局唯一标识，格式 `{domain}_{NNN}` |
| `cases[].description` | string | ✅ | 审计场景中文描述 |
| `cases[].severity` | enum | ✅ | `CRITICAL` / `HIGH` / `MEDIUM` / `LOW` |
| `cases[].documents` | list | ✅ | 模拟文档清单，至少 1 个 |
| `cases[].documents[].file` | string | ✅ | 相对 `documents/` 的文件名 |
| `cases[].documents[].description` | string | 否 | 文档内容说明 |
| `cases[].documents[].pages` | list[int] | 否 | 关键页码，用于检索精准度验证 |
| `cases[].input.financial_data` | dict | ✅ | 结构化财务指标，EvaluationRunner 注入 |
| `cases[].input.non_financial` | dict | 否 | 非财务背景信息 |
| `cases[].expected.risks` | list | ✅ | 标注的风险发现，至少 1 个 |
| `cases[].expected.risks[].area` | string | ✅ | 风险领域 |
| `cases[].expected.risks[].severity` | enum | ✅ | 标注严重程度 |
| `cases[].expected.risks[].probability` | float | ✅ | 风险概率 (0.0–1.0) |
| `cases[].expected.risks[].indicators` | list[str] | ✅ | 风险指标标识符 |
| `cases[].expected.assertions` | list[enum] | ✅ | 受影响的管理层认定: `Existence` / `Completeness` / `Accuracy` / `Cutoff` / `Valuation` / `RightsAndObligations` / `Presentation` |
| `cases[].expected.procedures` | list | ✅ | 建议的审计程序 |
| `cases[].expected.evidence_min_count` | int | ✅ | 最少证据数量 |
| `cases[].expected.related_standards` | list | ✅ | 关联会计准则/审计准则 |
| `cases[].evaluation.primary_metric` | string | ✅ | 首要评估指标 |
| `cases[].evaluation.secondary_metrics` | list[string] | ✅ | 辅助评估指标 |
| `cases[].evaluation.thresholds` | dict | ✅ | 各指标最低通过阈值 |
| `cases[].evaluation.weight` | float | 否 | 案例权重，默认 1.0 |

---

## 3. 七大审计领域

### 3.1 领域总览

| # | 领域 (Domain) | 案例数 | 核心风险主题 |
|---|--------------|--------|-------------|
| 1 | Revenue Recognition | 5 | 激进确认、截止性、虚构收入、捆绑合同、可变对价 |
| 2 | AR Impairment | 3 | 坏账准备不足、账龄分类错误、虚构应收 |
| 3 | Inventory Valuation | 3 | 存货跌价、数量差异、成本核算错误 |
| 4 | Expense Cutoff | 3 | 费用资本化、跨期费用、关联方交易 |
| 5 | Fixed Asset | 2 | 折旧政策变更、减值测试缺失 |
| 6 | Control Testing | 2 | 职责分离缺失、审批绕过 |
| 7 | Fraud Risk | 2 | 管理层凌驾、收入舞弊 |

### 3.2 Revenue Recognition (收入确认) — 5 Cases

收入确认是审计中最高风险领域（ISA 240 将其列为假定舞弊风险）。

| Case ID | 风险场景 | 严重程度 | 关键 Indicators | 核心认定 | 关联准则 |
|---------|---------|---------|----------------|----------|---------|
| `rev_001` | 激进收入确认 — 收入增长 3x 行业均值，应收周转延长 | HIGH | revenue_growth_3x_industry_avg, receivable_days_increased | Existence, Accuracy, Cutoff | IFRS 15 ¶27, ISA 240 ¶32 |
| `rev_002` | 截止性错误 — Q4 收入占比 55%，次年 1 月大量退货 | HIGH | q4_revenue_concentration, post_period_returns | Cutoff, Existence | IFRS 15 ¶31, ISA 500 ¶6 |
| `rev_003` | 虚构收入 — 新增客户占比超 40% 且多为现金交易 | CRITICAL | new_customer_concentration, cash_transaction_ratio | Existence | ISA 240 ¶A1-A7, IFRS 15 ¶9 |
| `rev_004` | 捆绑合同 — 多要素合同未正确拆分履约义务 | MEDIUM | bundled_contracts, deferred_revenue_imbalance | Accuracy, Presentation | IFRS 15 ¶22-30 (Step 2) |
| `rev_005` | 可变对价 — 销售返利/折扣估计不充分 | MEDIUM | variable_consideration_estimate, rebate_liability_understated | Accuracy, Completeness | IFRS 15 ¶50-59 |

### 3.3 AR Impairment (应收账款减值) — 3 Cases

| Case ID | 风险场景 | 严重程度 | 关键 Indicators | 核心认定 | 关联准则 |
|---------|---------|---------|----------------|----------|---------|
| `ar_001` | 坏账准备不足 — ECL 模型输入参数过于乐观 | HIGH | ecl_parameters_optimistic, provision_ratio_declining | Valuation, Accuracy | IFRS 9 ¶5.5.1-20, ISA 540 |
| `ar_002` | 账龄分类错误 — 长账龄应收被错误归类为短期 | HIGH | aging_misclassification, overdue_gt_90d_mislabelled | Valuation, Classification | IFRS 9 ¶B5.5.35, ISA 500 ¶6 |
| `ar_003` | 虚构应收账款 — 无真实交易的虚假应收余额 | CRITICAL | fictitious_receivables, confirmation_exceptions | Existence | ISA 240 ¶32, ISA 505 |

### 3.4 Inventory Valuation (存货估值) — 3 Cases

| Case ID | 风险场景 | 严重程度 | 关键 Indicators | 核心认定 | 关联准则 |
|---------|---------|---------|----------------|----------|---------|
| `inv_001` | 存货跌价 — 陈旧库存未计提减值，库龄 > 18 个月 | HIGH | inventory_obsolescence, aging_gt_18mo_no_provision | Valuation | IAS 2 ¶28, ISA 540 |
| `inv_002` | 数量差异 — 盘点差异巨大，存货明细账与实盘不一致 | HIGH | quantity_discrepancy, physical_count_variance | Existence, Completeness | ISA 501 ¶4-7 |
| `inv_003` | 成本核算错误 — 制造费用分配率异常导致库存成本偏离 | MEDIUM | overhead_allocation_error, standard_cost_variance | Accuracy, Valuation | IAS 2 ¶10-14 |

### 3.5 Expense Cutoff (费用截止性) — 3 Cases

| Case ID | 风险场景 | 严重程度 | 关键 Indicators | 核心认定 | 关联准则 |
|---------|---------|---------|----------------|----------|---------|
| `exp_001` | 费用不当资本化 — R&D 支出资本化率从 0% 骤升至 40% | HIGH | r_and_d_capitalization_spike, intangible_asset_surge | Accuracy, Classification, Cutoff | IAS 38 ¶57, ISA 500 ¶6 |
| `exp_002` | 跨期费用 — 次年大额发票计入当期，跨期调节利润 | MEDIUM | cross_period_expenses, post_balance_sheet_invoices | Cutoff, Completeness | ISA 500 ¶6, IAS 10 ¶3-4 |
| `exp_003` | 关联方交易 — 与管理层控制的壳公司进行非公允交易 | HIGH | related_party_transactions, off_market_pricing, shell_company_indicators | Existence, Accuracy, Presentation | IAS 24 ¶18-19, ISA 550 ¶A1-A7 |

### 3.6 Fixed Asset (固定资产) — 2 Cases

| Case ID | 风险场景 | 严重程度 | 关键 Indicators | 核心认定 | 关联准则 |
|---------|---------|---------|----------------|----------|---------|
| `fa_001` | 折旧政策变更 — 折旧年限突然延长 50%，无合理商业理由 | HIGH | depreciation_policy_change, useful_life_extended, earnings_impact | Valuation, Accuracy | IAS 16 ¶51-62, IAS 8 ¶32-38 |
| `fa_002` | 减值测试缺失 — 持续亏损的 CGU 未执行减值测试 | HIGH | impairment_indicator_ignored, loss_making_cgu, no_impairment_test | Valuation | IAS 36 ¶9-17, ISA 540 |

### 3.7 Control Testing (控制测试) — 2 Cases

| Case ID | 风险场景 | 严重程度 | 关键 Indicators | 核心认定 | 关联准则 |
|---------|---------|---------|----------------|----------|---------|
| `ctrl_001` | 职责分离缺失 — 同一员工兼任制单、审核、付款 | CRITICAL | segregation_of_duties_failure, single_user_full_cycle | 全部认定 | ISA 315 ¶A114-A118, ISA 330 ¶7-10 |
| `ctrl_002` | 审批绕过 — 大额采购未经适当层级审批即执行 | HIGH | approval_bypass, po_below_threshold_splitting | 全部认定 | ISA 330 ¶7-10, ISA 240 ¶32 |

### 3.8 Fraud Risk (舞弊风险) — 2 Cases

| Case ID | 风险场景 | 严重程度 | 关键 Indicators | 核心认定 | 关联准则 |
|---------|---------|---------|----------------|----------|---------|
| `fraud_001` | 管理层凌驾 — CEO 直接指令绕过所有审批流程修改财务数据 | CRITICAL | management_override, journal_entry_atypical_timing, ceo_direct_order | 全部认定 | ISA 240 ¶31-33, ISA 240 ¶A41-A45 |
| `fraud_002` | 收入舞弊 — 虚构"三角销售"循环虚增收入 | CRITICAL | round_tripping_revenue, related_party_chain, no_economic_substance | Existence, Accuracy | ISA 240 ¶32, IFRS 15 ¶9, IAS 24 |

---

## 4. 案例结构详解

每个 Benchmark Case 由以下四个核心模块构成：

### 4.1 Documents（模拟文档）

模拟文档是案例的**数据基础**。EvaluationRunner 执行时将文档注入 Document Intelligence Pipeline（E1A），模拟真实审计中的客户资料。

**文档类型包括：**

| 类型 | 格式 | 示例内容 |
|------|------|---------|
| 财务报表 | PDF | 年度财务报告（资产负债表、利润表、附注） |
| 业务合同 | PDF | 销售合同、采购合同、关联交易协议 |
| 分析底稿 | XLSX | 应收账款账龄表、存货库龄分析、固定资产卡片 |
| 内部记录 | PDF/TXT | 董事会会议纪要、审批记录、邮件往来 |
| 外部凭证 | PDF | 银行对账单、客户函证回函、发票 |

**文档生成要求：**
- 每个案例至少包含 **1 个** 文档，复杂案例建议 **2-4 个**
- 文档内容应模拟真实商业场景，包含足够的细节供 Agent 检索
- 明确标注关键页码（`pages` 字段），便于定向检索验证

### 4.2 Input（结构化输入）

`input` 是注入给 Agent 的**结构化财务数据**，模拟从 ERP/财务系统中提取的指标。

```yaml
input:
  financial_data:     # 财务指标（必填）
    revenue_growth: "45%"
    industry_avg_growth: "10%"
    receivable_days: 120
    # ... 任意自定义字段
  non_financial:      # 非财务背景（选填）
    management_comp_tied_to_revenue: true
    auditor_change: false
```

**设计原则：**
- `financial_data` 字段名使用 snake_case，值为字符串或数值
- 指标选择应聚焦与该案例风险直接相关的数据
- `non_financial` 提供审计背景信息（如管理层动机、行业环境）

### 4.3 Expected（标注期望输出）

`expected` 是人工标注的**标准答案**，用于评估 Agent 输出的质量。

#### 4.3.1 Risks（风险识别）

```yaml
risks:
  - area: Revenue Recognition           # 风险领域
    severity: HIGH                      # 严重程度
    probability: 0.75                   # 风险概率
    indicators:                         # 风险指标标识符
      - "revenue_growth_3x_industry_avg"
      - "receivable_days_increased_gt_30pct"
    description: >                      # 风险描述（中文）
      收入增长率远超行业均值，伴随应收账款周转天数显著延长...
```

**评估方式：** Risk Agent 的输出与 `expected.risks` 进行匹配，计算 Risk Classification Accuracy 和 Severity Accuracy。

#### 4.3.2 Assertions（管理层认定）

```yaml
assertions:
  - Existence
  - Accuracy
  - Cutoff
```

支持的认定类型：`Existence`、`Completeness`、`Accuracy`、`Cutoff`、`Valuation`、`RightsAndObligations`、`Presentation`。

#### 4.3.3 Procedures（审计程序）

```yaml
procedures:
  - type: Inspection                    # 程序类型
    target: sales_contracts             # 目标对象
    description: "抽查年末前 15 天大额销售合同..."
    sample_size: 10
```

支持的 `type` 值：`Inspection`、`Observation`、`Confirmation`、`Recalculation`、`Reperformance`、`AnalyticalProcedure`、`Inquiry`。

#### 4.3.4 Evidence & Standards

- `evidence_min_count`: Risk/Evidence Agent 应发现的最少证据数量
- `related_standards`: 关联的会计准则 (IFRS/IAS) 和审计准则 (ISA)，含具体段落号

### 4.4 Evaluation（评估指标）

```yaml
evaluation:
  primary_metric: risk_classification_accuracy
  secondary_metrics:
    - citation_completeness
    - procedure_coverage
    - reasoning_quality
    - severity_accuracy
  thresholds:
    risk_classification_accuracy: 0.80
    citation_completeness: 0.70
    procedure_coverage: 0.60
    reasoning_quality: 0.60
  weight: 1.0
```

#### 可用评估指标一览

| 指标 ID | 所属 Layer | 计算方式 | 说明 |
|---------|-----------|---------|------|
| `risk_classification_accuracy` | L2 | Exact Match / F1 | Agent 识别的风险是否与标注一致 |
| `severity_accuracy` | L2 | Weighted F1 | 严重程度判定是否准确（容忍 1 级偏差） |
| `reasoning_quality` | L2 | LLM-as-Judge (1-5 scale) | 推理链是否逻辑自洽、充分 |
| `citation_completeness` | L3 | 标注标准引用 / 检出标准引用 | Agent 引用准则的覆盖度 |
| `citation_precision` | L3 | 正确引用 / 总引用 | 引用的准则是否真正相关 |
| `citation_recall` | L3 | 检出正确引用 / 应检出引用 | 是否存在遗漏关键准则 |
| `unsupported_claim_rate` | L3 | 无引用 Claim / 总 Claim | 声称有无证据支持的比率 |
| `procedure_coverage` | L2 | 建议程序 / 标注程序 | Agent 推荐的审计程序覆盖度 |
| `evidence_coverage` | L2 | 发现证据 / 标注最少证据 | 证据收集充分性 |
| `completion_rate` | L4 | 成功完成 / 总执行 | 工作流整体完成率 |
| `human_intervention_count` | L4 | 计数 | HITL 触发次数 |
| `retrieval_recall_at_k` | L1 | Recall@5 | 检索召回率 |

---

## 5. Baseline 对比与优化门禁

### 5.1 Baseline 概念

在 AuditFlow E3（Agent Core Runtime）完成后，对全部 20 个 Case 执行三种模式下的评估，建立 **Baseline Score 矩阵**：

| 模式 | 说明 | 架构 |
|------|------|------|
| **GPT-4 Direct** | 将文档全文 + 财务数据一次性发送给 GPT-4，要求输出风险分析 | 单次 LLM 调用，无 RAG，无 Agent |
| **Naive RAG** | 文档切块 → Embedding → 向量检索 → LLM 生成 | 基础 RAG，无 Ontology，无 Agent 迭代 |
| **AuditFlow E3** | Planner → Knowledge → Risk → Evidence → Reviewer 完整 Agent 链 | 5 Agent + Ontology + HITL |

### 5.2 Baseline 报告模板

```
┌─ AuditFlow Baseline Report ─────────────────────────────────────┐
│  Date: 2026-XX-XX                                               │
│  Prompt Version: v1.0.0                                         │
│  Model: gpt-4-turbo / deepseek-v3                               │
│                                                                  │
│  ┌──────────────────┬──────────┬──────────┬──────────┬───────┐ │
│  │ Metric           │ GPT-4 Dir│ Naive RAG│ AuditFlow│ Δ E3  │ │
│  ├──────────────────┼──────────┼──────────┼──────────┼───────┤ │
│  │ risk_cls_acc     │   0.52   │   0.58   │   0.82   │ +0.30 │ │
│  │ severity_acc     │   0.48   │   0.55   │   0.78   │ +0.23 │ │
│  │ reasoning_quality│   2.8    │   3.1    │   4.2    │ +1.1  │ │
│  │ citation_prec.   │   0.35   │   0.42   │   0.85   │ +0.43 │ │
│  │ citation_recall  │   0.28   │   0.38   │   0.80   │ +0.42 │ │
│  │ procedure_cov.   │   0.40   │   0.45   │   0.72   │ +0.27 │ │
│  │ evidence_cov.    │   0.33   │   0.48   │   0.76   │ +0.28 │ │
│  │ avg_cost_per_case│  $0.12   │  $0.18   │  $0.45   │   —   │ │
│  │ avg_latency      │   3.2s   │   4.8s   │  18.5s   │   —   │ │
│  └──────────────────┴──────────┴──────────┴──────────┴───────┘ │
│                                                                  │
│  Conclusion: AuditFlow E3 在所有质量指标上显著优于 Baselines     │
│  Cost/Latency 在可接受范围内（单次审计 $0.45 / 18.5s）           │
└──────────────────────────────────────────────────────────────────┘
```

### 5.3 优化门禁规则

| 规则 | 条件 | 动作 |
|------|------|------|
| **质量退化门禁** | 新 Prompt 版本任一 Primary Metric < Baseline × 0.95 | 🚫 PR Blocked |
| **单一指标保护** | 某领域 mean score 下降 > 5% | ⚠️ Warning + 需团队 Review |
| **回归检测** | 任意单个 case score < Baseline - 10pp | 🚫 PR Blocked |
| **成本超限** | avg_cost_per_case > Baseline × 1.5 | ⚠️ Warning |
| **延迟超限** | p95_latency > Baseline × 2.0 | ⚠️ Warning |

---

## 6. CI 集成

### 6.1 CI Pipeline 流程

```
┌──────────────────────────────────────────────────────────────────┐
│  PR 提交                                                         │
│    │                                                             │
│    ▼                                                             │
│  ┌────────────────────┐                                          │
│  │ lint + type-check  │ ← 快速失败（< 2 min）                    │
│  └─────────┬──────────┘                                          │
│            │ ✅                                                   │
│            ▼                                                     │
│  ┌────────────────────┐                                          │
│  │ unit tests         │ ← 单元测试（< 5 min）                    │
│  └─────────┬──────────┘                                          │
│            │ ✅                                                   │
│            ▼                                                     │
│  ┌─────────────────────────────────────────────────────┐         │
│  │ Benchmark Evaluation                                │         │
│  │  ├─ L1 Retrieval Eval (Recall@5, MRR, NDCG)         │         │
│  │  ├─ L2 Agent Eval (Risk Accuracy, Severity, etc.)   │         │
│  │  └─ L3 Grounding Eval (Citation Precision/Recall)   │         │
│  │                                                     │         │
│  │  ⏱  ~15-30 min（需调用 LLM）                        │         │
│  └──────────────────────┬──────────────────────────────┘         │
│                         │                                        │
│              ┌──────────▼──────────┐                              │
│              │ Score >= Baseline?  │                              │
│              └──────────┬──────────┘                              │
│                    Yes  │  No                                     │
│                    ✅   │  🚫                                     │
│                 Merge   │  Block + Report                         │
└──────────────────────────────────────────────────────────────────┘
```

### 6.2 CI 配置文件示例

```yaml
# .github/workflows/benchmark.yml (GitHub Actions)
name: Benchmark Gate

on:
  pull_request:
    paths:
      - "src/agents/**"         # Agent 逻辑变更
      - "src/prompts/**"        # Prompt 模板变更
      - "src/evaluation/**"     # 评估逻辑变更
      - "benchmark/**"          # Benchmark 数据变更

jobs:
  benchmark:
    runs-on: ubuntu-latest
    timeout-minutes: 45

    steps:
      - uses: actions/checkout@v4

      - name: Setup Python & Dependencies
        run: make install && make setup-benchmark

      - name: Run Full Benchmark Suite
        id: benchmark
        run: |
          python -m evaluation.runner \
            --suite benchmark/ \
            --output results/current.json \
            --baseline results/baseline.json

      - name: Gate Check — Quality Regression
        if: always()
        run: |
          python -m evaluation.gate \
            --current results/current.json \
            --baseline results/baseline.json \
            --tolerance 0.05

      - name: Upload Benchmark Report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: benchmark-report
          path: results/
```

### 6.3 Baseline 存储

```yaml
# results/baseline.json — 存放于 Git 仓库
{
  "version": "1.0",
  "prompt_version": "v1.0.0",
  "model": "gpt-4-turbo",
  "date": "2026-03-15",
  "scores": {
    "overall": {
      "risk_classification_accuracy": 0.82,
      "severity_accuracy": 0.78,
      "reasoning_quality": 4.2,
      "citation_precision": 0.85,
      "citation_recall": 0.80,
      "procedure_coverage": 0.72,
      "evidence_coverage": 0.76,
      "mean_cost_per_case": 0.45,
      "p95_latency_seconds": 22.3
    },
    "per_domain": {
      "revenue_recognition": { "risk_classification_accuracy": 0.85, "severity_accuracy": 0.80 },
      "ar_impairment": { "risk_classification_accuracy": 0.80, "severity_accuracy": 0.75 },
      "inventory_valuation": { "risk_classification_accuracy": 0.78, "severity_accuracy": 0.73 },
      "expense_cutoff": { "risk_classification_accuracy": 0.83, "severity_accuracy": 0.80 },
      "fixed_asset": { "risk_classification_accuracy": 0.81, "severity_accuracy": 0.77 },
      "control_testing": { "risk_classification_accuracy": 0.84, "severity_accuracy": 0.82 },
      "fraud_risk": { "risk_classification_accuracy": 0.80, "severity_accuracy": 0.76 }
    },
    "per_case": {
      "rev_001": { "risk_classification_accuracy": 0.85, "severity_accuracy": 0.80 },
      "rev_002": { "risk_classification_accuracy": 0.88, "severity_accuracy": 0.85 }
    }
  }
}
```

---

## 7. 扩展计划

### 7.1 添加新案例

在现有领域中添加新案例，需遵循以下流程：

1. **设计案例**: 基于真实审计风险场景设计案例，填写 Case Design Template
2. **创建模拟文档**: 在 `benchmark/{domain}/documents/` 下添加模拟文件
3. **编辑 benchmark.yaml**: 在原文件的 `cases` 列表末尾追加新案例
4. **本地验证**: 运行 `python -m evaluation.runner --case {new_case_id}` 确保格式正确
5. **标注审核**: 由至少 1 名具有审计专业背景的 Reviewer 审核 `expected` 标注
6. **提交 PR**: 附带案例设计文档和本地验证结果截图
7. **更新 Baseline**: 新案例批注后重新运行完整 Benchmark Suite，更新 `results/baseline.json`

#### Case Design Template

```yaml
# 新案例设计模板（提交前填写）
case_id:                    # {domain}_{NNN} 格式
domain:                     # 所属领域
designer:                   # 设计者
reviewer:                   # 审核者
scenario_description:       # 审计场景描述
real_world_reference:       # 真实案例参考（可选，脱敏后）
reasoning_chain:            # 关联的 Ontology Reasoning Chain ID
documents_needed:           # 需要创建的模拟文档列表
risk_indicators:            # 预期的风险指标
standards_referenced:       # 引用的准则段落
design_date:                # 设计日期
```

### 7.2 添加新领域 (New Domain)

当现有 7 个领域不足以覆盖新的审计场景时：

1. **领域提案**: 在 Issue 中提交 New Domain Proposal，包含：
   - 领域名称与核心风险描述
   - 计划案例数量（建议 ≥ 2 个）
   - 涉及的会计准则/审计准则
   - 与现有 Ontology 的覆盖关系
2. **创建目录结构**: `benchmark/{new_domain}/benchmark.yaml` + `documents/`
3. **创建 Reasoning Chain**: 在 E1B Ontology 中追加对应推理链
4. **案例开发**: 按 7.1 流程开发至少 2 个案例
5. **更新文档**: 更新本文档 §3 的领域总览表

#### 候选扩展领域

| 优先级 | 候选领域 | 潜在风险 | 案例建议数 |
|--------|---------|---------|-----------|
| P0 | Related Party Transactions | 未披露关联方交易完整性/定价公允 | 3 |
| P1 | Going Concern Assessment | 持续经营假设不合理 | 2 |
| P1 | Financial Instruments Valuation | 复杂金融工具估值模型偏差 | 3 |
| P2 | Leases (IFRS 16) | 租赁负债与使用权资产确认 | 2 |
| P2 | Provisions & Contingencies | 预计负债低估 | 2 |
| P3 | Business Combinations | 合并对价分摊/商誉减值 | 3 |

### 7.3 版本策略

```
Benchmark v1.0 (MVP Beta)
    └── 20 Cases × 7 Domains
    └── Coverage: ISA 315/330/500/240 + IFRS 15/9 + IAS 2/16/36/38

Benchmark v1.1 (Post-MVP)
    └── +3 Related Party Cases
    └── +2 Going Concern Cases
    └── Coverage: +IAS 24, +ISA 570

Benchmark v2.0 (Commercial Launch)
    └── 30+ Cases × 10+ Domains
    └── Multi-language documents (EN + CN)
    └── Industry-specific scenarios (制造业、金融、零售)
```

---

## 附录 A. 评估指标与 Layer 映射

| Layer | 名称 | 指标 | 数据来源 | 执行频率 |
|-------|------|------|----------|----------|
| L1 | Retrieval | Recall@5, MRR, NDCG | Benchmark 标准段落标注 | 每次 PR |
| L2 | Agent | Risk Classification Accuracy, Severity Accuracy, Reasoning Quality, Procedure Coverage | Benchmark expected 标注 | 每次 PR |
| L3 | Grounding | Citation Precision, Citation Recall, Unsupported Claim Rate | Grounding Checker + Benchmark 标准引用 | 每次 PR |
| L4 | Workflow | Completion Rate, Human Intervention Count, Time Reduction | 端到端真实案例（非 Benchmark） | 每周 Cron |

## 附录 B. 术语对照

| 中文 | English | 说明 |
|------|---------|------|
| 审计领域 | Audit Domain | 如 Revenue Recognition, AR Impairment |
| 案例 | Case / Benchmark Case | 单个测试用例 |
| 风险场景 | Risk Scenario | 具体审计风险描述 |
| 管理层认定 | Management Assertion | Existence, Accuracy, Cutoff 等 |
| 审计程序 | Audit Procedure | Inspection, Confirmation, AnalyticalProcedure 等 |
| 推理链 | Reasoning Chain | Ontology 中的 Risk → Assertion → Procedure → Evidence → Standard 链路 |
| 基线 | Baseline | 当前最优分数，用于 CI 门禁比较 |
| 标注 | Annotation / Expected Output | 人工标注的标准答案 |

---

> **下一步：** 本文档描述的数据集由 Epic 7 (Benchmark Expansion) 实现。具体 Issue 参见 `ISSUES.md` — Epic 7 → Issue 7.1.1 (Benchmark Schema) / Issue 7.1.2 (20 Cases) / Issue 7.1.3 (Baseline Report)。
