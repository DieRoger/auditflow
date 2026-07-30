"""Kaggle Dataset #1 评估 — Financial Audit Transactions

7,000 rows, 59 colums, 955 条异常(Abnormal_Label=1)
测试内容: Anomaly Detection 检出率 vs Kaggle 标注
"""

import csv, os

DATA_PATH = r"D:\audit_data\zara2099_financial-audit-transactions-dataset\Financial_Audit_N_Abnormal_Transactions.csv"


def load_data():
    with open(DATA_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows, reader.fieldnames


def kaggle_anomalies(rows):
    """统计 Kaggle 标注的异常类型分布"""
    types = {}
    for r in rows:
        if r["Abnormal_Label"].strip() == "1":
            atype = r["Abnormal_Type"].strip()
            types[atype] = types.get(atype, 0) + 1
    return types


def auditflow_detection(row):
    """AuditFlow Anomaly Detection 规则"""
    flags = []
    try:
        amount = float(row["Transaction_Amount_RMB"])
    except:
        amount = 0
    # 周末交易
    if row["Weekend_Flag"].strip() == "1":
        flags.append(("WEEKEND", "周末交易"))
    # 大额整数金额
    if amount > 0 and amount % 10000 == 0:
        flags.append(("ROUND_AMOUNT", f"整数金额 {amount:.0f}"))
    # 关联方
    if row["Related_Party_Flag"].strip() == "1":
        flags.append(("RELATED_PARTY", "关联方交易"))
    # 审计规则违规
    try:
        violations = int(row["Audit_Rule_Violation_Count"])
        if violations > 0:
            flags.append(("VIOLATION", f"违规次数 {violations}"))
    except:
        pass
    return flags


def evaluate():
    print("=" * 65)
    print("  Dataset #1: Financial Audit Transactions — 评估")
    print("=" * 65)

    rows, cols = load_data()
    print(f"\n  数据: {len(rows)} rows, {len(cols)} cols")

    # Kaggle 标注
    kaggle_types = kaggle_anomalies(rows)
    total_kaggle = sum(kaggle_types.values())
    print(f"\n  Kaggle 标注异常: {total_kaggle} ({total_kaggle/len(rows)*100:.1f}%)")
    for t, c in sorted(kaggle_types.items(), key=lambda x: -x[1]):
        print(f"    {t:<35} {c}")

    # AuditFlow 检测
    tp, fp, fn = 0, 0, 0
    details = []
    for row in rows:
        actual = row["Abnormal_Label"].strip() == "1"
        detected = len(auditflow_detection(row)) > 0

        if detected and actual:
            tp += 1
        elif detected and not actual:
            fp += 1
        elif not detected and actual:
            fn += 1

    precision = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    print(f"\n{'='*65}")
    print(f"  AuditFlow Anomaly Detection 评估结果")
    print(f"{'='*65}")
    print(f"  True Positives:  {tp}")
    print(f"  False Positives: {fp}")
    print(f"  False Negatives: {fn}")
    print(f"  Precision:       {precision:.1f}%")
    print(f"  Recall:          {recall:.1f}%")
    print(f"  F1 Score:        {f1:.1f}%")
    print(f"{'='*65}")


if __name__ == "__main__":
    evaluate()
