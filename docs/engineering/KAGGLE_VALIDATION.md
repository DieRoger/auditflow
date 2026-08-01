# Kaggle Vertical Slice Validation

**Generated:** 2026-08-01 14:28
**Dataset:** Kaggle #1 — Financial Audit Transactions (7000 rows, 955 anomalies)

> 边界声明: Kaggle 无 PDF 审计证据/财务报表/TB/Materiality/底稿。
> 因此 Procedure 层只验证 Mapping 覆盖率（不验证正确性），Evidence 层只验证引用完整性（不验证真实性）。

## Benchmark Dashboard

| Capability | Result |
|------------|--------|
| Review Reduction | **89.0%** |
| Assessment Accuracy (Balanced) | **79.1% (60.6%)** |
| Evidence Reference Completeness | **100.0%** |
| Procedure Mapping Coverage | **100.0%** |
| Detection F1 | **60.1%** |
| Workflow Success Rate | **100.0%** |
| Pipeline Runtime (synthetic, 29 txns) | **0.01s** |
| Full Kaggle 4-layer Scan (7,000 rows) | **0.40s** |

## Pipeline Funnel (Review Reduction 可视化)

```
7000 Transactions
    |
    v
769 Review Queue (89.0% reduction)
    |
    v
11535 Findings
    |
    v
3138 High-Risk Items
    |
    v
11535 Procedures Planned
    |
    v
Reviewer → Final Report
```

## Layer Details

### Layer 1 — Detection (GT: Abnormal_Label)
- Precision 67.4%, Recall 54.2%, F1 60.1%
- Threshold 15, TP=518 FP=251 FN=437 TN=5794
- Review Reduction: 769/7000 flagged (89.0% saved)

### Layer 2 — Assessment (GT: Risk_Class 0/1/2 → LOW/MEDIUM/HIGH)
- Accuracy: 79.1% | Balanced Accuracy: 60.6% | Adjacent-level: 96.2%

#### Confusion Matrix (GT rows × Pred columns)

| GT \ Pred | LOW | MEDIUM | HIGH |
|-----------|-----|--------|------|
| LOW | 5300 | 494 | 251 |
| MEDIUM | 239 | 177 | 459 |
| HIGH | 15 | 6 | 59 |

| Ground Truth | Accuracy | N |
|--------------|----------|---|
| LOW | 87.7% | 6045 |
| MEDIUM | 20.2% | 875 |
| HIGH | 73.8% | 80 |

### Layer 3 — Procedure Mapping Coverage (Rule Mapping, 不验证正确性)
- Coverage: 100.0% (2544/2544 findings have procedure_template)
- Abnormal types found: {'Unusual_Amount_Spike': 175, 'Split_Transaction': 142, 'High_Risk_Vendor': 141, 'Cross_Province_Mismatch': 115, 'Duplicate_Invoice': 109, 'Round_Trip_Transfer': 107, 'Temporal_Burst': 92, 'Tax_ID_Mismatch': 74}

### Layer 4 — Evidence Reference Completeness (不验证真实性)
- Completeness: 100.0% (11535/11535 findings reference Invoice_ID + Transaction_ID + Timestamp + Amount)

### Workflow (无 GT，验证可靠性)
- Success Rate: 100.0% (9/9 stages)
- Pipeline Runtime (synthetic 29-txn pipeline): 0.01s
- Full Kaggle 4-layer scan (7,000 rows): 0.40s
- Exceptions Found: 4, Opinion: MODIFIED
- Failed Stages: none
