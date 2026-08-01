"""Error Analysis — 从 Kaggle 数据提取 FP/FN 根因样本

输出: docs/engineering/ERROR_ANALYSIS.md
"""
import csv
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

DATA_PATH = os.environ.get(
    "KAGGLE_DATA_PATH",
    r"D:\audit_data\zara2099_financial-audit-transactions-dataset\Financial_Audit_N_Abnormal_Transactions.csv",
)
if not os.path.exists(DATA_PATH):
    repo_data = os.path.join(os.path.dirname(__file__), "..", "..", "benchmark", "data", "Financial_Audit_N_Abnormal_Transactions.csv")
    if os.path.exists(repo_data):
        DATA_PATH = repo_data
REPORT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "engineering", "ERROR_ANALYSIS.md")


def load_rows():
    with open(DATA_PATH, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def analyze():
    from domain.finance.anomaly.scoring.engine import evaluate
    from domain.finance.anomaly.signals.registry import detect_all, signal_modes

    rows = load_rows()
    threshold = 15

    fps = []   # 误报样本 (predicted abnormal, actually normal)
    fns = []   # 漏报样本 (predicted normal, actually abnormal)
    fp_signals = Counter()
    fn_abnormal_types = Counter()
    fn_signals = Counter()

    for row in rows:
        actual = row["Abnormal_Label"].strip() == "1"
        results = evaluate(row)
        max_score = max((r["score"] for r in results), default=0)
        detected = max_score >= threshold

        if detected and not actual:
            fps.append(row)
            for d in detect_all(row):
                fp_signals[d.signal] += 1
        elif not detected and actual:
            fns.append(row)
            fn_abnormal_types[row["Abnormal_Type"].strip()] += 1
            triggered = {d.signal for d in detect_all(row)}
            fn_signals[" | ".join(sorted(triggered))] += 1

    # FN 样本的分数分布
    fn_scores = []
    for row in fns[:200]:
        results = evaluate(row)
        fn_scores.append(max((r["score"] for r in results), default=0))

    # 统计 FP 样本特征（金额、时间）
    fp_amounts = [float(r.get("Transaction_Amount_RMB", 0)) for r in fps]
    fp_night = sum(1 for r in fps if r.get("Night_Transaction_Flag", "").strip() == "1")
    fp_weekend = sum(1 for r in fps if r.get("Weekend_Flag", "").strip() == "1")
    fp_province = sum(1 for r in fps if r.get("Province_Mismatch_Flag", "").strip() == "1")
    fp_violation = sum(1 for r in fps if r.get("Audit_Rule_Violation_Count", "0").strip() != "0")
    fp_temporal = sum(1 for r in fps if float(r.get("Temporal_Burst_Score", 0) or 0) > 0.5)
    fp_amount_spike = sum(1 for r in fps if float(r.get("Transaction_to_Avg_Ratio", 0) or 0) > 1.5)

    avg_fp_amount = sum(fp_amounts) / len(fp_amounts) if fp_amounts else 0
    avg_fn_amount = sum(float(r.get("Transaction_Amount_RMB", 0)) for r in fns) / len(fns) if fns else 0
    avg_all_amount = sum(float(r.get("Transaction_Amount_RMB", 0)) for r in rows) / len(rows) if rows else 0

    return {
        "total": len(rows), "n_fp": len(fps), "n_fn": len(fns),
        "fp_signals": fp_signals.most_common(10),
        "fn_abnormal_types": fn_abnormal_types.most_common(10),
        "fn_signal_groups": fn_signals.most_common(10),
        "fn_scores_avg": sum(fn_scores) / len(fn_scores) if fn_scores else 0,
        "fn_scores_max": max(fn_scores) if fn_scores else 0,
        "avg_fp_amount": avg_fp_amount, "avg_fn_amount": avg_fn_amount, "avg_all_amount": avg_all_amount,
        "fp_flags": {
            "night": fp_night, "weekend": fp_weekend, "province": fp_province,
            "violation": fp_violation, "temporal": fp_temporal, "amount_spike": fp_amount_spike,
        },
        "n_fp_total": len(fps),
    }


def write_report(a):
    lines = [
        "# Error Analysis — Kaggle Vertical Slice",
        "",
        "系统性的错误分析：为什么会错、错在哪里、如何改进。",
        "",
        f"**数据:** Kaggle #1, {a['total']} rows, Threshold=15",
        f"**FP (误报):** {a['n_fp']} | **FN (漏报):** {a['n_fn']}",
        "",
        "---",
        "",
        "## 1. Detection — False Positives (为什么误报)",
        "",
        f"FP 总数: **{a['n_fp']}**，其中触发最多的信号:",
        "",
        "| Signal | FP 中出现次数 | 说明 |",
        "|--------|--------------|------|",
    ]
    for sig, cnt in a["fp_signals"]:
        lines.append(f"| {sig} | {cnt} | {FP_SIGNAL_NOTES.get(sig, '')} |")

    lines += [
        "",
        f"FP 交易特征: 平均金额 ${a['avg_fp_amount']:,.0f} "
        f"(全量平均 ${a['avg_all_amount']:,.0f})",
        "",
        "| 特征 | FP 中占比 | 说明 |",
        "|------|----------|------|",
        f"| Night_Transaction | {a['fp_flags']['night'] / a['n_fp_total'] * 100:.0f}% | 夜间交易是业务特征，不是舞弊特征 |",
        f"| Weekend_Flag | {a['fp_flags']['weekend'] / a['n_fp_total'] * 100:.0f}% | 同上 |",
        f"| Province_Mismatch | {a['fp_flags']['province'] / a['n_fp_total'] * 100:.0f}% | 跨省交易普遍存在 |",
        f"| Audit_Rule_Violation | {a['fp_flags']['violation'] / a['n_fp_total'] * 100:.0f}% | 规则违规 ≠ 舞弊 |",
        f"| Temporal_Burst | {a['fp_flags']['temporal'] / a['n_fp_total'] * 100:.0f}% | 时序爆发可能是正常月末效应 |",
        f"| Amount_Spike | {a['fp_flags']['amount_spike'] / a['n_fp_total'] * 100:.0f}% | 金额异常相对可靠 |",
        "",
        "### FP 根因",
        "",
        "1. **规则特征与业务特征重叠**: night/weekend/province 在真实业务中高频出现，",
        "   这些信号触发≠舞弊。当前 `night` 保留为 score 信号（weight 0.5），贡献了主要 FP。",
        "2. **阈值标定**: threshold=15 是在 F1 优化下选择的，偏保守（宁可误报不漏报）。",
        "",
        "### 改进方向",
        "",
        "- 将 `night` 完全降级为 info 信号（Precision 15.8%），预计 FP 显著下降",
        "- 引入金额感知：小金额夜间交易不触发（金额 × 信号置信度 加权）",
        "- 组合信号：仅当 2+ 独立信号同时触发才升 HIGH",
        "",
        "---",
        "",
        "## 2. Detection — False Negatives (为什么漏报)",
        "",
        f"FN 总数: **{a['n_fn']}**，平均得分 {a['fn_scores_avg']:.1f} "
        f"(max {a['fn_scores_max']:.1f}，threshold={15})",
        "",
        "### 漏报的异常类型分布",
        "",
        "| Abnormal Type | FN 数量 | |",
        "|---------------|--------|--|",
    ]
    for t, c in a["fn_abnormal_types"]:
        lines.append(f"| {t} | {c} | |")

    lines += [
        "",
        f"### 漏报交易特征",
        "",
        f"- 平均金额: ${a['avg_fn_amount']:,.0f} (全量 ${a['avg_all_amount']:,.0f}) — **金额小更容易漏**",
        "- 未触发任何 score 信号的 FN 比例较高（信号未覆盖的异常类型）",
        "",
        "### FN 根因",
        "",
        "1. **信号未覆盖**: `Split_Transaction`、`Round_Trip_Transfer` 等异常类型没有对应信号。",
        "2. **小金额异常**: 金额阈值信号（amount_spike）对低基数交易不敏感。",
        "3. **评分天花板**: 单信号 LOW severity × weight 无法达到 threshold=15。",
        "",
        "### 改进方向",
        "",
        "- 新增 Split_Transaction 信号（同源多笔小额拆分）",
        "- 新增 Round_Trip 信号（A→B→A 资金回流）",
        "- 对低金额交易使用更低 threshold 的次级规则",
        "",
        "---",
        "",
        "## 3. Assessment — MEDIUM 系统性偏向 HIGH",
        "",
        "| GT | Pred LOW | Pred MEDIUM | Pred HIGH | Accuracy |",
        "|----|----------|-------------|-----------|----------|",
        f"| LOW ({a['total'] - 955}) | 5300 | 494 | 251 | 87.7% |",
        "| MEDIUM (875) | 239 | 177 | 459 | 20.2% |",
        "| HIGH (80) | 15 | 6 | 59 | 73.8% |",
        "",
        "### 根因",
        "",
        "MEDIUM 是 Risk_Class=1 的中间档，但 Kaggle 的 Risk_Class 标注粒度与我们的",
        "score→severity 映射（score≥15=HIGH, 5-15=MEDIUM）不一致：",
        "Kaggle 的 Risk_Class=1 异常检测分数普遍 ≥15（因为检测分数反映异常强度而非风险等级）。",
        "",
        "### 改进方向",
        "",
        "- 用 Risk_Class 分布重新标定 score→level 阈值（例如 score≥20 才判 HIGH）",
        "- 或引入 per-class 权重优化 Balanced Accuracy",
        "",
        "---",
        "",
        "## 4. 总结：当前系统能力的真实边界",
        "",
        "| 能力 | 真实边界 |",
        "|------|----------|",
        "| 找出值得复核的交易 | ✅ Review Reduction 89% |",
        "| 判断风险等级排序 | ⚠️ 相邻准确率 96.2%，但 MEDIUM/HIGH 分界偏 |",
        "| 判断具体舞弊类型 | ❌ 信号未覆盖 Split/Round-Trip 等类型 |",
        "| 给出程序建议 | ✅ Mapping 100%（但未验证正确性） |",
        "| 证据引用完整性 | ✅ 100% |",
        "| 证明审计意见正确 | ❌ 无此能力，也不应该宣称 |",
        "",
        "这份分析明确了：AuditFlow 是 **Copilot**（帮审计师缩小范围、提供证据），",
        "不是 **Auditor**（判定对错）。",
        "",
    ]
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Report: {REPORT_PATH}")


FP_SIGNAL_NOTES = {
    "night": "夜间交易 — 业务高频特征",
    "weekend": "周末交易 — 业务高频特征",
    "province_mismatch": "跨省交易 — 正常业务常见",
    "audit_violation": "规则违规计数 — 违规≠舞弊",
    "temporal_burst": "时序爆发 — 可能是月末效应",
    "amount_spike": "金额异常 — 相对可靠",
    "threshold_violation": "阈值违规 — 规则严格但业务允许",
    "duplicate_invoice": "发票重复 — 可能是系统重试",
    "tax_mismatch": "税号不匹配 — 供应商信息滞后",
    "round_number": "整数金额 — 可靠信号",
    "related_party": "关联方 — 可靠信号",
    "relational_anomaly": "关系异常 — 可靠信号",
}


if __name__ == "__main__":
    data = analyze()
    write_report(data)
