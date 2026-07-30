"""Kaggle Dataset #1 — Anomaly Detection 规则调优

优化策略:
  1. 扩展检测规则（使用 59 列中的更多信号）
  2. 加权评分（每项规则赋予权重）
  3. 阈值调优（找 Precision/Recall 平衡点）
"""

import csv, json, math

DATA_PATH = r"D:\audit_data\zara2099_financial-audit-transactions-dataset\Financial_Audit_N_Abnormal_Transactions.csv"


def load_data():
    with open(DATA_PATH, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


# ── 优化规则引擎 ──

def compute_score(row) -> float:
    """计算交易异常评分（分数越高越可能异常）"""
    score = 0.0

    try:
        amount = float(row["Transaction_Amount_RMB"])
        hist_avg = float(row["Historical_Avg_Amount_RMB"])
        ratio = float(row["Transaction_to_Avg_Ratio"])
        threshold_ratio = float(row["Amount_Threshold_Ratio"])
    except:
        amount, hist_avg, ratio, threshold_ratio = 0, 0, 0, 0

    # 1. 金额异常 (+1～+4)
    if ratio > 5 and amount > 10000:
        score += 4
    elif ratio > 3:
        score += 2
    elif ratio > 2:
        score += 1

    # 2. 超过审批阈值 (+1～+3)
    if threshold_ratio > 1.5:
        score += 3
    elif threshold_ratio > 1.0:
        score += 1

    # 3. 整数大额 (+2)
    if amount > 50000 and amount % 10000 == 0:
        score += 2

    # 4. 周末/深夜 (+1)
    if row.get("Weekend_Flag", "").strip() == "1":
        score += 1
    if row.get("Night_Transaction_Flag", "").strip() == "1":
        score += 1

    # 5. 关联方 (+3)
    if row.get("Related_Party_Flag", "").strip() == "1":
        score += 3

    # 6. 审计规则违规 (+2 per count)
    try:
        violations = int(row.get("Audit_Rule_Violation_Count", 0))
        score += min(violations * 2, 6)
    except:
        pass

    # 7. 发票异常 (+3)
    if row.get("Duplicate_Invoice_Flag", "").strip() == "1":
        score += 3
    if row.get("Tax_Validation_Flag", "").strip() == "0":
        score += 2

    # 8. 省份不匹配 (+2)
    if row.get("Province_Mismatch_Flag", "").strip() == "1":
        score += 2

    # 9. 关系异常分数 (+1～+5)
    try:
        rel_score = float(row.get("Relational_Anomaly_Score", 0))
        if rel_score > 0.8:
            score += 5
        elif rel_score > 0.6:
            score += 3
        elif rel_score > 0.4:
            score += 1
    except:
        pass

    # 10. 时间突发分数 (+1～+3)
    try:
        burst = float(row.get("Temporal_Burst_Score", 0))
        if burst > 0.8:
            score += 3
        elif burst > 0.5:
            score += 1
    except:
        pass

    # 11. 复杂交易结构 (+2)
    if row.get("Edge_Type", "").strip() in ("CYCLE", "PAD"):
        score += 2

    return score


def evaluate(rows: list, threshold: float) -> dict:
    """在给定阈值下评估性能"""
    tp = fp = fn = tn = 0
    scores = []
    for row in rows:
        actual = row["Abnormal_Label"].strip() == "1"
        score = compute_score(row)
        detected = score >= threshold
        scores.append(score)

        if detected and actual:   tp += 1
        elif detected and not actual: fp += 1
        elif not detected and actual: fn += 1
        else: tn += 1

    precision = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return {"threshold": threshold, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": round(precision, 1), "recall": round(recall, 1),
            "f1": round(f1, 1), "fp_rate": round(fp / (fp + tn) * 100, 1)}


def main():
    rows = load_data()
    print("=" * 65)
    print("  Anomaly Detection — 规则调优")
    print("=" * 65)
    print(f"\n  数据: {len(rows)} rows")

    # 多阈值测试
    print(f"\n{'='*65}")
    print(f"  阈值扫描")
    print(f"{'='*65}")
    print(f"  {'Threshold':>9} {'Prec':>6} {'Recall':>7} {'F1':>5} {'TP':>4} {'FP':>5} {'FN':>4} {'FP Rate':>8}")
    print(f"  {'-'*8} {'-'*5} {'-'*6} {'-'*4} {'-'*3} {'-'*4} {'-'*3} {'-'*7}")

    best = {"f1": 0}
    for th in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
        result = evaluate(rows, th)
        marker = " ← BEST" if result["f1"] > best["f1"] else ""
        if result["f1"] > best["f1"]:
            best = result
        print(f"  {th:>8}  {result['precision']:>5.1f}% {result['recall']:>5.1f}%  "
              f"{result['f1']:>4.1f}% {result['tp']:>4} {result['fp']:>5} {result['fn']:>4}  "
              f"{result['fp_rate']:>5.1f}%{marker}")

    # 最佳配置明细
    print(f"\n{'='*65}")
    print(f"  最佳阈值: {best['threshold']}")
    print(f"{'='*65}")
    print(f"  Precision:     {best['precision']}%")
    print(f"  Recall:        {best['recall']}%")
    print(f"  F1 Score:      {best['f1']}%")
    print(f"  True Pos:      {best['tp']}")
    print(f"  False Pos:     {best['fp']}")
    print(f"  False Neg:     {best['fn']}")
    print(f"  False Positive Rate: {best['fp_rate']}%")

    # 与旧规则对比
    print(f"\n{'='*65}")
    print(f"  优化前后对比")
    print(f"{'='*65}")
    old = evaluate(rows, 1)  # 旧规则等效于阈值=1
    print(f"  {'Metric':<20} {'Before':>10} {'After':>10}")
    print(f"  {'-'*20} {'-'*10} {'-'*10}")
    print(f"  {'Threshold':<20} {'1.0 (any rule)':>10} {best['threshold']:>10}")
    print(f"  {'Precision':<20} {old['precision']:>9.1f}% {best['precision']:>9.1f}%")
    print(f"  {'Recall':<20} {old['recall']:>9.1f}% {best['recall']:>9.1f}%")
    print(f"  {'F1':<20} {old['f1']:>9.1f}% {best['f1']:>9.1f}%")
    print(f"  {'False Positives':<20} {old['fp']:>10} {best['fp']:>10}")


if __name__ == "__main__":
    main()
