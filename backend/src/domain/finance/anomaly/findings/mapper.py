"""Finding Mapper — 将 Scoring Engine 结果映射为 Canonical Finding"""

from .finding import Assertion, EvidenceRef, Finding, ProcedureRef


def to_finding(scoring_result: dict) -> Finding:
    """将 Scoring Engine 的评分结果转为 Finding"""
    return Finding(
        risk_type=scoring_result.get("risk", "Unknown Risk"),
        severity=scoring_result.get("severity", "LOW"),
        score=scoring_result.get("score", 0),
        triggered_signals=scoring_result.get("detections", []),
        recommended_procedures=[ProcedureRef(
            procedure_id=scoring_result.get("procedure_template", ""),
            name=scoring_result.get("risk", ""),
        )] if scoring_result.get("procedure_template") else [],
        affected_assertions=[
            Assertion(name="OCCURRENCE"),
            Assertion(name="CUTOFF") if "cutoff" in scoring_result.get("risk", "").lower() else None,
        ],
    )


def score_to_findings(results: list[dict]) -> list[Finding]:
    """批量转换"""
    return [to_finding(r) for r in results]
