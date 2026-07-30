"""Evaluation — 利用 Kaggle Dataset #1 (955 条标注) 作为 Benchmark

每次修改 Signal/RiskProfile 后自动跑:
  cd backend && $env:PYTHONPATH="src" && py -3.11 -m domain.finance.anomaly.evaluation.benchmark
"""

import csv, json, os, sys

DATA_PATH = r"D:\audit_data\zara2099_financial-audit-transactions-dataset\Financial_Audit_N_Abnormal_Transactions.csv"


def load_data() -> list[dict]:
    with open(DATA_PATH, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def evaluate(rows: list[dict], threshold: float = 10.0) -> dict:
    """在全量数据上评估 Risk Scoring Engine"""
    from domain.finance.anomaly.scoring.engine import RiskScoringEngine
    engine = RiskScoringEngine()

    tp = fp = fn = tn = 0
    for row in rows:
        actual = row["Abnormal_Label"].strip() == "1"
        results = engine.assess(row)
        # 使用所有 profile 中的最高分判定
        max_score = max((r["score"] for r in results), default=0)
        detected = max_score >= threshold

        if detected and actual: tp += 1
        elif detected and not actual: fp += 1
        elif not detected and actual: fn += 1
        else: tn += 1

    precision = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return {"total": len(rows), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": round(precision, 1), "recall": round(recall, 1),
            "f1": round(f1, 1)}


def compare_thresholds(rows: list[dict], thresholds: list[float] = None):
    """多阈值对比"""
    thresholds = thresholds or [5, 7, 8, 9, 10, 12, 15]
    print(f"{'Threshold':>9} {'Prec':>6} {'Recall':>7} {'F1':>5} {'TP':>4} {'FP':>5} {'FN':>4}")
    print(f"{'-'*8} {'-'*5} {'-'*6} {'-'*4} {'-'*3} {'-'*4} {'-'*3}")
    best = {"f1": 0}
    for t in thresholds:
        r = evaluate(rows, t)
        m = " ← BEST" if r["f1"] > best["f1"] else ""
        if r["f1"] > best["f1"]:
            best = r
        print(f"  {t:>8}  {r['precision']:>5.1f}% {r['recall']:>5.1f}%  {r['f1']:>4.1f}%"
              f" {r['tp']:>4} {r['fp']:>5} {r['fn']:>4}{m}")
    return best


if __name__ == "__main__":
    rows = load_data()
    print(f"Benchmark: {len(rows)} rows ({sum(1 for r in rows if r['Abnormal_Label'].strip()=='1')} anomalies)\n")
    best = compare_thresholds(rows)
    print(f"\nF1 最优阈值: {best['f1']}% at F1={best['f1']}%")
