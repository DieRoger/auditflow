"""Risk Scoring Engine — Detection → Profile → Score → Finding"""

from ..signals.registry import detect_all
from .profile import ALL_PROFILES


def evaluate(row: dict, risk_profiles: list[str] = None) -> list[dict]:
    """对单行交易评估多个风险类型"""
    detections = detect_all(row)
    profiles_to_run = risk_profiles or list(ALL_PROFILES.keys())
    results = []

    for key in profiles_to_run:
        profile = ALL_PROFILES[key]
        scoring = profile.score(detections)

        if scoring["score"] == 0:
            continue

        results.append({
            "risk": scoring["risk"],
            "score": scoring["score"],
            "severity": scoring["severity"],
            "threshold": scoring["threshold"],
            "flagged": scoring["flagged"],
            "procedure_template": scoring["procedure_template"],
            "detections": [d.to_dict() for d in detections],
            "detection_count": scoring["detections"],
        })

    return results
