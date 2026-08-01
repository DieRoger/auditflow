# Benchmark v1.0 — FROZEN

**Status:** FROZEN (2026-08-01)
**Reason:** 所有评估指标已完整（F1/P/R/Balanced Accuracy/Review Reduction/Confusion Matrix/Error Analysis）。
不再调整权重、阈值或信号 —— 继续调参会破坏可复现性叙事。

## 冻结配置

| 项 | 值 |
|----|-----|
| Dataset | Kaggle #1 — Financial Audit Transactions (7,000 rows, 955 anomalies) |
| Data Path | `D:\audit_data\zara2099_financial-audit-transactions-dataset\Financial_Audit_N_Abnormal_Transactions.csv` |
| Seed | 42 (fixed, 100% reproducible) |
| External Threshold | 15 |
| Score Signals | 9 (duplicate_invoice, amount_spike, related_party, round_number, relational_anomaly, threshold_violation, tax_mismatch, temporal_burst, night) |
| Info Signals | 3 (weekend, province_mismatch, audit_violation) |
| Benchmark Script | `backend/scripts/kaggle_pipeline_validation.py` |
| Error Analysis | `backend/scripts/error_analysis.py` |
| Golden Cases | G001-G006 (rule-based, no LLM) |

## 冻结指标 (v1.0)

| Capability | Result |
|------------|--------|
| Review Reduction | **89.0%** |
| Assessment Accuracy (Balanced) | **79.1% (60.6%)** |
| Evidence Reference Completeness | **100.0%** |
| Procedure Mapping Coverage | **100.0%** |
| Detection F1 | **60.1%** |
| Workflow Success Rate | **100.0%** |
| Full Kaggle 4-layer Scan | **0.40s** |

## 引用规则

所有文章、README、论文、答辩引用本文件中的数字。
任何新的数字（调参/新数据集）必须创建 Benchmark v2.0 而不是覆盖 v1.0。

## 如何运行复现

```powershell
cd auditflow/backend
$env:PYTHONPATH = "src"
py -3.11 -m scripts.kaggle_pipeline_validation   # 四层 + Dashboard
py -3.11 -m scripts.error_analysis                # Error Analysis
py -3.11 -m scripts.run_pipeline_evaluation       # Golden Cases + Workflow
```
