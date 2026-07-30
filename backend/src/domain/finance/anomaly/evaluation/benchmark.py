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
    # 按 Signal 统计
    signal_stats: dict[str, dict] = {}
    # 按 Risk 统计
    risk_stats: dict[str, dict] = {}

    for row in rows:
        actual = row["Abnormal_Label"].strip() == "1"
        results = engine.assess(row)
        max_score = max((r["score"] for r in results), default=0)
        detected = max_score >= threshold

        if detected and actual: tp += 1
        elif detected and not actual: fp += 1
        elif not detected and actual: fn += 1
        else: tn += 1

        # 按 Signal 统计（TP = signal triggered + actual anomaly）
        for r in results:
            risk_name = r["risk"]
            risk_stats.setdefault(risk_name, {"tp": 0, "fp": 0, "fn": 0, "tn": 0})
            risk_flag = r["flagged"]
            if risk_flag and actual:
                risk_stats[risk_name]["tp"] += 1
            elif risk_flag and not actual:
                risk_stats[risk_name]["fp"] += 1
            elif not risk_flag and actual:
                risk_stats[risk_name]["fn"] += 1
            else:
                risk_stats[risk_name]["tn"] += 1

            for s in r.get("signals", []):
                sname = s["signal"]
                signal_stats.setdefault(sname, {"tp": 0, "fp": 0})
                if actual:
                    signal_stats[sname]["tp"] += 1  # 信号触发 + 实际异常
                else:
                    signal_stats[sname]["fp"] += 1  # 信号触发但无异常

    precision = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return {
        "total": len(rows),
        "confusion_matrix": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "precision": round(precision, 1), "recall": round(recall, 1), "f1": round(f1, 1),
        "by_signal": signal_stats,
        "by_risk": risk_stats,
    }


def compare_thresholds(rows: list[dict], thresholds: list[float] = None):
    """多阈值对比 — 含 Per-Signal 和 Per-Risk 指标"""
    thresholds = thresholds or [5, 7, 8, 9, 10, 12, 15]
    print(f"{'Threshold':>9} {'Prec':>6} {'Recall':>7} {'F1':>5} {'TP':>4} {'FP':>5} {'FN':>4}")
    print(f"{'-'*8} {'-'*5} {'-'*6} {'-'*4} {'-'*3} {'-'*4} {'-'*3}")
    best = {"f1": 0}
    for t in thresholds:
        r = evaluate(rows, t)
        m = " ← BEST" if r["f1"] > best["f1"] else ""
        if r["f1"] > best["f1"]:
            best = r
        cm = r["confusion_matrix"]
        print(f"  {t:>8}  {r['precision']:>5.1f}% {r['recall']:>5.1f}%  {r['f1']:>4.1f}%"
              f" {cm['tp']:>4} {cm['fp']:>5} {cm['fn']:>4}{m}")
    return best


if __name__ == "__main__":
    rows = load_data()
    print(f"Benchmark: {len(rows)} rows ({sum(1 for r in rows if r['Abnormal_Label'].strip()=='1')} anomalies)\n")
    best = compare_thresholds(rows)
    print(f"\nF1 最优阈值: {best['f1']}% at threshold={best.get('threshold', 'N/A')}")

    # Per-Signal 指标
    print(f"\n{'='*65}")
    print(f"  Per-Signal Performance (at optimal threshold)")
    print(f"{'='*65}")
    by_signal = best.get("by_signal", {})
    print(f"  {'Signal':<25} {'Triggered':>9} {'Anomaly Hit':>11}")
    print(f"  {'-'*25} {'-'*9} {'-'*11}")
    for sname, stats in sorted(by_signal.items(), key=lambda x: -x[1].get("tp", 0)):
        print(f"  {sname:<25} {stats.get('tp',0)+stats.get('fp',0):>9} {stats.get('tp',0):>11}")

    # Per-Risk 指标
    print(f"\n  Per-Risk Performance")
    print(f"  {'Risk':<20} {'Prec':>6} {'Recall':>7} {'F1':>5}")
    print(f"  {'-'*20} {'-'*5} {'-'*6} {'-'*4}")
    for rname, stats in sorted(best.get("by_risk", {}).items()):
        p = stats["tp"] / (stats["tp"] + stats["fp"]) * 100 if (stats["tp"] + stats["fp"]) > 0 else 0
        r = stats["tp"] / (stats["tp"] + stats["fn"]) * 100 if (stats["tp"] + stats["fn"]) > 0 else 0
        f = 2 * p * r / (p + r) if (p + r) > 0 else 0
        print(f"  {rname:<20} {p:>5.1f}% {r:>5.1f}%  {f:>4.1f}%")
