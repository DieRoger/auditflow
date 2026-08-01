"""Evaluation — Kaggle Dataset #1 Benchmark (可重复评估)

输出: benchmark_report.json + benchmark_report.md
"""

import csv, json, os
from datetime import datetime

DATA_PATH = r"D:\audit_data\zara2099_financial-audit-transactions-dataset\Financial_Audit_N_Abnormal_Transactions.csv"
REPORT_DIR = os.path.join(os.path.dirname(__file__), "reports")


def load_data() -> list[dict]:
    with open(DATA_PATH, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def evaluate(rows: list[dict], threshold: float = 10.0) -> dict:
    """全量评估"""
    from domain.finance.anomaly.scoring.engine import evaluate as score_evaluate

    tp = fp = fn = tn = 0
    signal_stats: dict[str, dict] = {}
    risk_stats: dict[str, dict] = {}

    for row in rows:
        actual = row["Abnormal_Label"].strip() == "1"
        results = score_evaluate(row)
        max_score = max((r["score"] for r in results), default=0)
        detected = max_score >= threshold

        if detected and actual: tp += 1
        elif detected and not actual: fp += 1
        elif not detected and actual: fn += 1
        else: tn += 1

        for r in results:
            rname = r["risk"]
            risk_stats.setdefault(rname, {"tp": 0, "fp": 0, "fn": 0, "tn": 0})
            rf = r["flagged"]
            if rf and actual:
                risk_stats[rname]["tp"] += 1
            elif rf and not actual:
                risk_stats[rname]["fp"] += 1
            elif not rf and actual:
                risk_stats[rname]["fn"] += 1
            else:
                risk_stats[rname]["tn"] += 1

            for d in r.get("detections", []):
                sname = d["signal"]
                signal_stats.setdefault(sname, {"triggered": 0, "anomaly_hit": 0})
                signal_stats[sname]["triggered"] += 1
                if actual:
                    signal_stats[sname]["anomaly_hit"] += 1

    precision = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return {
        "total": len(rows), "threshold": threshold,
        "confusion_matrix": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "metrics": {"precision": round(precision, 1), "recall": round(recall, 1), "f1": round(f1, 1)},
        "by_signal": signal_stats,
        "by_risk": risk_stats,
    }


def run_benchmark():
    rows = load_data()
    os.makedirs(REPORT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"Benchmark: {len(rows)} rows ({sum(1 for r in rows if r['Abnormal_Label'].strip()=='1')} anomalies)\n")

    # 多阈值扫描
    thresholds = [5, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    all_results = {}
    best_runs = {"metrics": {"f1": 0}}

    print(f"{'Threshold':>9} {'Prec':>6} {'Recall':>7} {'F1':>5} {'TP':>4} {'FP':>5}")
    print(f"{'-'*8} {'-'*5} {'-'*6} {'-'*4} {'-'*3} {'-'*4}")

    for t in thresholds:
        r = evaluate(rows, t)
        all_results[str(t)] = r
        cm = r["confusion_matrix"]
        m = " ← BEST" if r["metrics"]["f1"] > best_runs["metrics"]["f1"] else ""
        if r["metrics"]["f1"] > best_runs["metrics"]["f1"]:
            best_runs = r
        print(f"  {t:>8}  {r['metrics']['precision']:>5.1f}% {r['metrics']['recall']:>5.1f}%  "
              f"{r['metrics']['f1']:>4.1f}% {cm['tp']:>4} {cm['fp']:>5}{m}")

    # 最佳结果明细
    b = best_runs
    cm = b["confusion_matrix"]
    total = b["total"]
    flagged = cm["tp"] + cm["fp"]
    review_reduction = (1 - flagged / total) * 100 if total > 0 else 0

    print(f"\nBest: threshold={b['threshold']}, F1={b['metrics']['f1']}%")
    print(f"  Precision: {b['metrics']['precision']}% | Recall: {b['metrics']['recall']}%")
    print(f"  Review Reduction: {review_reduction:.0f}% ({flagged}/{total} flagged for review)")

    # Per-Signal
    print(f"\n  Per-Signal:")
    for sname, s in sorted(b["by_signal"].items(), key=lambda x: -x[1]["triggered"]):
        prec = s["anomaly_hit"] / s["triggered"] * 100 if s["triggered"] else 0
        print(f"    {sname:<25} {s['triggered']:>6}x  {prec:>5.1f}% anomalies")

    # 保存 JSON
    report = {
        "timestamp": ts, "dataset": total, "best_threshold": b["threshold"],
        "best_metrics": b["metrics"],
        "review_reduction": {"flagged": flagged, "total": total, "reduction_pct": round(review_reduction, 1)},
        "all_thresholds": all_results,
    }
    json_path = os.path.join(REPORT_DIR, f"benchmark_{ts}.json")
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport: {json_path}")
    return best_runs


if __name__ == "__main__":
    run_benchmark()
