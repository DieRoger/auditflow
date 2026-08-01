"""PipelineEvaluator — Assessment / Procedure / Workflow 三层评估

不依赖 LLM（纯规则），可复现。
对每个 golden case:
  1. 构造 Assessment（模拟 AssessmentService 输出）
  2. ProcedurePlanningService.build_program
  3. 计算各层指标

输出: docs/engineering/EVALUATION_REPORT.md
"""

import json
import os
from datetime import datetime

from application.assessment.assessment import Assessment
from application.assessment.assessment_service import AssessmentService
from application.audit.procedure_planning import ProcedurePlanningService
from evaluation.pipeline_metrics import (
    AssessmentRiskAgreement, AssessmentPolicyCoverage,
    AssessmentFalseEscalation, ProcedureCoverage, AssertionMatch,
)

REPORT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "engineering", "EVALUATION_REPORT.md")


# ── Golden Cases (人工标注基线) ─────────────────────────────────
# 通过 AssessmentService 真实构建（自动生成 policy_decisions）

def _assessment(narrative: dict, findings: list[dict], materiality: float | None = None) -> Assessment:
    return AssessmentService().build(
        risk_artifact={"content": narrative},
        finding_artifact={"content": {"findings": findings}},
        materiality=materiality,
    )


GOLDEN_CASES = [
    {
        "id": "G001",
        "desc": "HIGH finding + HIGH narrative → HIGH",
        "assessment": _assessment(
            {"severity": "HIGH", "probability": 0.9, "area": "Revenue", "title": "Revenue fraud"},
            [{"severity": "HIGH", "score": 92, "confidence": 0.9,
              "affected_assertions": ["CUTOFF", "OCCURRENCE"]}],
        ),
        "expected_risk": "HIGH",
        "required_assertions": ["CUTOFF", "OCCURRENCE"],
        "min_decisions": 1,
    },
    {
        "id": "G002",
        "desc": "LOW narrative + no findings → LOW",
        "assessment": _assessment(
            {"severity": "LOW", "probability": 0.1, "area": "Revenue"},
            [],
        ),
        "expected_risk": "LOW",
        "required_assertions": ["OCCURRENCE"],
        "min_decisions": 0,
    },
    {
        "id": "G003",
        "desc": "HIGH narrative only, no findings → MEDIUM (Rule 3 downgrade)",
        "assessment": _assessment(
            {"severity": "HIGH", "probability": 0.85, "area": "Revenue"},
            [],
        ),
        "expected_risk": "MEDIUM",
        "required_assertions": ["OCCURRENCE"],
        "min_decisions": 1,
    },
    {
        "id": "G004",
        "desc": "HIGH finding but amount < materiality → LOW (Rule 8)",
        "assessment": _assessment(
            {"severity": "LOW", "probability": 0.2, "area": "Revenue"},
            [{"severity": "HIGH", "score": 90, "confidence": 0.9, "amount": 5000,
              "affected_assertions": ["OCCURRENCE"]}],
            materiality=500000,
        ),
        "expected_risk": "LOW",
        "required_assertions": ["OCCURRENCE"],
        "min_decisions": 2,
    },
    {
        "id": "G005",
        "desc": "10+ LOW findings → MEDIUM (Rule 2)",
        "assessment": _assessment(
            {"severity": "LOW", "probability": 0.3, "area": "Revenue"},
            [{"severity": "LOW", "score": 5, "confidence": 0.6,
              "affected_assertions": ["OCCURRENCE"]} for _ in range(12)],
        ),
        "expected_risk": "MEDIUM",
        "required_assertions": ["OCCURRENCE"],
        "min_decisions": 1,
    },
    {
        "id": "G006",
        "desc": "Low confidence HIGH findings → capped (Rule 7)",
        "assessment": _assessment(
            {"severity": "HIGH", "probability": 0.8, "area": "Revenue"},
            [{"severity": "HIGH", "score": 88, "confidence": 0.1,
              "affected_assertions": ["OCCURRENCE"]}],
        ),
        "expected_risk": "MEDIUM",
        "required_assertions": ["OCCURRENCE"],
        "min_decisions": 1,
    },
]


class PipelineEvaluator:
    """三层管线评估器（不依赖 LLM）"""

    def __init__(self):
        self._risk_metric = AssessmentRiskAgreement()
        self._policy_metric = AssessmentPolicyCoverage()
        self._escalation_metric = AssessmentFalseEscalation()
        self._coverage_metric = ProcedureCoverage()
        self._assertion_metric = AssertionMatch()

    def evaluate(self) -> dict:
        planner = ProcedurePlanningService()
        results = []

        for case in GOLDEN_CASES:
            assessment = case["assessment"]
            program = planner.build_program(assessment, area="Revenue")
            planned_assertions = []
            for p in program.procedures:
                planned_assertions.extend(a.value for a in p.assertions)

            # Assessment 层预测
            pred = {
                "overall_risk": assessment.overall_risk,
                "policy_decisions": assessment.policy_decisions,
            }
            truth = {
                "expected_risk": case["expected_risk"],
                "min_decisions": case["min_decisions"],
            }

            # Procedure 层预测
            proc_pred = {"planned_assertions": list(set(planned_assertions))}
            proc_truth = {"required_assertions": case["required_assertions"]}

            results.append({
                "id": case["id"],
                "desc": case["desc"],
                "assessment_agreement": self._risk_metric.compute(pred, truth),
                "policy_coverage": self._policy_metric.compute(pred, truth),
                "false_escalation": self._escalation_metric.compute(pred, truth),
                "procedure_coverage": self._coverage_metric.compute(proc_pred, proc_truth),
                "assertion_match": self._assertion_metric.compute(proc_pred, proc_truth),
                "planned_assertions": planned_assertions,
            })

        return self._aggregate(results)

    @staticmethod
    def _aggregate(results: list[dict]) -> dict:
        keys = ["assessment_agreement", "policy_coverage", "false_escalation",
                "procedure_coverage", "assertion_match"]
        agg = {}
        for k in keys:
            vals = [r[k] for r in results]
            agg[k] = round(sum(vals) / len(vals) * 100, 1) if vals else 0.0
        agg["cases"] = results
        agg["timestamp"] = datetime.now().isoformat()
        return agg


def workflow_evaluate() -> dict:
    """Layer 4: Workflow Success Rate — 真实执行管线 stages（无 LLM）"""
    from datetime import date
    from decimal import Decimal
    from application.assessment.assessment_service import AssessmentService
    from application.audit.procedure_planning import ProcedurePlanningService
    from application.audit.sampling import CutoffProcedureExecutor, generate_cutoff_program
    from application.assessment.review_queue import build_review_queue, ReviewDecision
    from domain.audit.entities.procedure import SamplingConfig, SamplingMethod
    from domain.audit.entities.evidence_graph import EvidenceMapper
    from domain.finance.entities.transaction import Document, DocumentType, Transaction

    completed = []
    failed = []

    # Stage 1: Data
    txns = [Transaction(transaction_id=f"T{i:04d}", transaction_date=date(2024, 12, 31),
                        amount=Decimal(100000 + i * 5000), party_id="ABC",
                        document_refs=[f"INV-{i:04d}"]) for i in range(1, 30)]
    completed.append("data_import")

    # Stage 2: Risk Assessment (rule-based fallback, 模拟 LLM 不可用路径)
    risk_ctx = {"severity": "HIGH", "probability": 0.85, "area": "Revenue", "title": "Revenue risk"}
    completed.append("risk_assessment")

    # Stage 3: Anomaly Detection (DetectionFacade)
    try:
        from application.detection.detection_facade import DetectionFacade
        rows = [{"id": t.transaction_id, "amount": float(t.amount), "date": str(t.transaction_date),
                 "customer": t.party_id, "invoice": t.document_refs[0]} for t in txns]
        findings = DetectionFacade().scan(rows)
        completed.append("anomaly_detection")
    except Exception as e:
        failed.append(f"anomaly_detection: {e}")

    # Stage 4: Assessment
    try:
        assessment = AssessmentService().build(
            risk_artifact={"content": risk_ctx},
            finding_artifact={"content": {"findings": findings}},
        )
        completed.append("assessment")
    except Exception as e:
        failed.append(f"assessment: {e}")
        return {"success_rate": 0.0, "completed": completed, "failed": failed}

    # Stage 5: Review Queue (HITL)
    queue = build_review_queue(assessment)
    queue.items[0].review(ReviewDecision.ACCEPT, comment="Approved")
    completed.append("review_queue")

    # Stage 6: Procedure Planning
    program = ProcedurePlanningService().build_program(assessment, area="Revenue")
    completed.append("procedure_planning")

    # Stage 7: Procedure Execution (cutoff test)
    records_raw = [{"canonical_refs": {"id": t.transaction_id},
                    "_txn_date": str(t.transaction_date),
                    "_ship_date": str(date(2025, 1, i - 24)) if i in (26, 27, 28, 29) else str(date(2024, 12, 31)),
                    "_amount": float(t.amount)} for i, t in enumerate(txns, 1)]
    cutoff_proc = generate_cutoff_program().procedures[0]
    cutoff_proc.sampling = SamplingConfig(method=SamplingMethod.ALL, population_size=len(txns),
                                          sample_size=len(txns), key_field="transaction_date")
    proc_findings = CutoffProcedureExecutor().execute(cutoff_proc, txns, records_raw, date(2024, 12, 31))
    completed.append("procedure_execution")

    # Stage 8: Evidence Graph
    docs = {}
    for i, t in enumerate(txns, 1):
        inv = Document(document_id=f"DINV{i}", document_type=DocumentType.INVOICE,
                       document_no=t.document_refs[0], document_date=t.transaction_date,
                       party_id=t.party_id, amount=t.amount)
        docs[inv.document_no] = inv
        if i not in (26, 27, 28, 29):
            dely = Document(document_id=f"DDEL{i}", document_type=DocumentType.DELIVERY,
                            document_no=f"DEL-{t.transaction_id}", document_date=t.transaction_date,
                            party_id=t.party_id, amount=t.amount)
            docs[dely.document_no] = dely
    graph = EvidenceMapper().build_graph(cutoff_proc, txns, proc_findings, docs)
    completed.append("evidence_graph")

    # Stage 9: Opinion
    opinion = "MODIFIED" if len(proc_findings) > 0 else "UNMODIFIED"
    completed.append("opinion")

    required = ["data_import", "risk_assessment", "anomaly_detection", "assessment",
                "review_queue", "procedure_planning", "procedure_execution",
                "evidence_graph", "opinion"]
    success = len(set(completed) & set(required)) / len(required)
    return {
        "success_rate": round(success * 100, 1),
        "completed": completed,
        "failed": failed,
        "exceptions_found": len(proc_findings),
        "opinion": opinion,
    }


def main():
    evaluator = PipelineEvaluator()
    report = evaluator.evaluate()
    wf = workflow_evaluate()

    print("=" * 70)
    print("  Pipeline Evaluation — Assessment / Procedure / Workflow (ISA 315/500)")
    print("=" * 70)
    print(f"\n  Cases: {len(report['cases'])}")
    print(f"  Assessment Risk Agreement : {report['assessment_agreement']}%")
    print(f"  Assessment Policy Coverage: {report['policy_coverage']}%")
    print(f"  False Escalation Rate     : {100 - report['false_escalation']}%")
    print(f"  Procedure Coverage        : {report['procedure_coverage']}%")
    print(f"  Assertion Match           : {report['assertion_match']}%")
    print(f"  Workflow Success Rate     : {wf['success_rate']}% "
          f"({len(wf['completed'])}/{len(wf['completed']) + len(wf['failed'])} stages)")
    print(f"  Exceptions Found          : {wf['exceptions_found']}, Opinion: {wf['opinion']}")
    if wf["failed"]:
        print(f"  FAILED STAGES: {wf['failed']}")

    for c in report["cases"]:
        print(f"\n  [{c['id']}] {c['desc']}")
        print(f"    agreement={c['assessment_agreement']:.0%} coverage={c['procedure_coverage']:.0%} "
              f"assertions={c['planned_assertions']}")

    # 保存 Markdown 报告
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    lines = [
        "# Evaluation Report — Assessment & Procedure & Workflow Layers",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Cases:** {len(report['cases'])} (rule-based golden, no LLM dependency)",
        "",
        "| Layer | Metric | Score |",
        "|-------|--------|-------|",
        f"| 2. Assessment | Risk Agreement | {report['assessment_agreement']}% |",
        f"| 2. Assessment | Policy Coverage | {report['policy_coverage']}% |",
        f"| 2. Assessment | False Escalation | {100 - report['false_escalation']}% |",
        f"| 3. Procedure | Procedure Coverage | {report['procedure_coverage']}% |",
        f"| 3. Procedure | Assertion Match | {report['assertion_match']}% |",
        f"| 4. Workflow | End-to-end Success | {wf['success_rate']}% |",
        f"| 4. Workflow | Exceptions Found | {wf['exceptions_found']} (Opinion: {wf['opinion']}) |",
        "",
        "## Per-Case Details",
        "",
    ]
    for c in report["cases"]:
        lines.append(f"### {c['id']}: {c['desc']}")
        lines.append(f"- Risk Agreement: {c['assessment_agreement']:.0%}")
        lines.append(f"- Procedure Coverage: {c['procedure_coverage']:.0%}")
        lines.append(f"- Planned Assertions: {c['planned_assertions']}")
        lines.append("")
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nReport: {REPORT_PATH}")


if __name__ == "__main__":
    main()
