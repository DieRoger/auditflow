"""Risk Scoring Engine — Detection → Profile → Score → Finding"""

from ..signals.registry import detect_all, score_signals, signal_modes
from .profile import ALL_PROFILES


def evaluate(row: dict, risk_profiles: list[str] = None) -> list[dict]:
    """对单行交易评估多个风险类型

    评分仅使用 mode='score' 的信号。info 信号保留在 detections 字段中用于解释。
    """
    all_detections = detect_all(row)
    scoring_detections = score_signals(row)
    profiles_to_run = risk_profiles or list(ALL_PROFILES.keys())
    results = []

    for key in profiles_to_run:
        profile = ALL_PROFILES[key]
        scoring = profile.score(scoring_detections)

        if scoring["score"] == 0:
            continue

        results.append({
            "risk": scoring["risk"],
            "score": scoring["score"],
            "severity": scoring["severity"],
            "threshold": scoring["threshold"],
            "flagged": scoring["flagged"],
            "procedure_template": scoring["procedure_template"],
            "detections": [d.to_dict() for d in all_detections],  # 保留所有信号用于解释
            "score_signals": [d.to_dict() for d in scoring_detections],  # 参与评分的信号
            "detection_count": scoring["detections"],
        })

    return results


def scan_all(rows: list[dict]) -> list[dict]:
    """批量扫描，返回降噪后的 Finding 摘要列表

    每个 row 只保留最高评分的 risk，避免同一行产生多条 LOW Finding。
    返回 dict 结构可直接用于构造 FindingItem。
    """
    all_findings: dict[str, list[dict]] = {}  # risk_type → rows

    for row in rows:
        results = evaluate(row)
        if not results:
            continue
        best = max(results, key=lambda r: r["score"])
        all_findings.setdefault(best["risk"], []).append(best)

    summary = []
    for risk_type, rows_ in all_findings.items():
        best_row = max(rows_, key=lambda r: r["score"])
        signals = []
        for r in rows_:
            for d in r.get("detections", []):
                signals.append(d)
        # 去重 signal
        seen = set()
        unique = []
        for s in signals:
            k = s.get("signal", "")
            if k not in seen:
                seen.add(k)
                unique.append(s)

        summary.append({
            "risk_type": risk_type,
            "severity": best_row["severity"],
            "score": best_row["score"],
            "affected_count": len(rows_),
            "triggered_signals": unique,
            "procedure_template": best_row["procedure_template"],
            "affected_assertions": ["OCCURRENCE"] + (
                ["CUTOFF"] if "cutoff" in risk_type.lower() else []
            ),
        })

    return summary
