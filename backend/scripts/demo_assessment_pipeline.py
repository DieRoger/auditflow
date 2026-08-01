"""End-to-End Revenue Cutoff Demo — Assessment-driven Pipeline

完整链路:
  Excel/Transactions → Risk Agent (LLM) + AnomalyDetectionAgent (Rule)
    → AssessmentBuilder → ProcedurePlanningService → CutoffProcedureExecutor

用法: py -3.11 -m scripts.demo_assessment_pipeline
"""

import asyncio
import json
import sys
import os
from datetime import date
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"), override=True)

from domain.contracts import AgentRequest
from application.assessment.assessment_service import AssessmentService
from application.audit.procedure_planning import ProcedurePlanningService
from application.audit.sampling import CutoffProcedureExecutor, generate_cutoff_program
from domain.audit.entities.procedure import (
    AuditProcedure, SamplingConfig, SamplingMethod, ProcedureType, AuditAssertion,
)
from domain.finance.entities.transaction import Transaction


def build_mock_transactions() -> list[Transaction]:
    """构造 Revenue Cutoff 测试用交易 (29 条，含 4 个截止例外)

    例外: txn_date <= Dec 31 但 ship_date > Dec 31（收入确认在正确的期间但发货在下一期间）
    """
    txns = []
    base = date(2024, 12, 31)  # 报告截止日
    for i in range(1, 30):
        txn_date = base
        amt = Decimal(str(100000 + i * 5000))

        # T26-T29: 截止日前入账但下期发货（例外）
        if i in (26, 27, 28, 29):
            txn_date = base

        cust = "ABC Corp" if i <= 15 else "XYZ Ltd"
        txns.append(Transaction(
            transaction_id=f"T{i:04d}",
            transaction_date=txn_date,
            amount=amt,
            description=f"Sales to {cust}",
            party_id=cust,
            document_refs=[f"INV-{i:04d}"],
        ))
    return txns


def build_records_raw(txns: list[Transaction]) -> list[dict]:
    """构造 ExcelAdapter 风格的 raw records（CutoffProcedureExecutor 需要）"""
    records = []
    base = date(2024, 12, 31)
    for i, txn in enumerate(txns, 1):
        ship = base
        if i in (26, 27, 28, 29):
            ship = date(2025, 1, i - 24)
        records.append({
            "_id": str(i),
            "canonical_refs": {"id": txn.transaction_id, "type": "transaction"},
            "_txn_date": txn.transaction_date.isoformat(),
            "_ship_date": ship.isoformat(),
            "_amount": float(txn.amount),
            "_customer": txn.party_id or "",
            "_invoice": txn.document_refs[0] if txn.document_refs else "",
        })
    return records


async def run_risk_agent(txns: list[Transaction]) -> dict:
    """调用真实 LLM Risk Agent（注入 ISA 520 Ratio/Trend 分析）"""
    try:
        from agents.risk.agent import LlmRiskAgent
        from application.assessment.risk_context import build_risk_context

        # ISA 520: 先计算比率和趋势，再交给 LLM 解释
        risk_ctx = build_risk_context(txns)
        ctx_dict = risk_ctx.to_risk_context()

        financial_data = {
            "revenue_growth": f"{sum(1 for t in risk_ctx.anomalies if 'Revenue' in t.metric) > 0 and '+' or ''}{next((t.change_pct for t in risk_ctx.anomalies if 'Revenue' in t.metric), 0):.0f}%",
            "industry_avg": "10%",
            "receivable_days": 120,
            "revenue": f"${sum(float(t.amount) for t in txns):,.0f}",
            "transaction_count": len(txns),
            # ISA 520 structured context
            "ratio_analysis": ctx_dict["ratio_risks"],
            "trend_analysis": ctx_dict["trend_anomalies"],
            "significant_accounts": ctx_dict["significant_accounts"],
            "risk_flags": ctx_dict["overall_risk_flags"],
        }

        agent = LlmRiskAgent()
        req = AgentRequest(
            workflow_id="demo-assessment-001", project_id="p1", task_id="t1",
            firm_id="f1", client_id="c1", engagement_id="e1",
            inputs={"audit_area": "Revenue Recognition", "financial_data": financial_data},
        )
        resp = await agent.execute(req)
        artifact = resp.result.get("artifact", {})
        print(f"  [Risk Agent] severity={artifact.get('content',{}).get('severity','?')} probability={resp.confidence:.0%}")
        print(f"  [ISA 520] {len(risk_ctx.ratios.ratios)} ratios, {len(risk_ctx.anomalies)} trend anomalies, {len(risk_ctx.significant_accounts)} sig accounts")
        return artifact
    except Exception as e:
        print(f"  [Risk Agent] LLM unavailable ({e}), using fallback with ISA 520 context")
        risk_ctx = build_risk_context(txns)
        ctx_dict = risk_ctx.to_risk_context()
        return {
            "artifact_type": "risk_finding",
            "content": {
                "severity": "HIGH", "probability": 0.85, "title": "Revenue recognition risk",
                "area": "Revenue",
                "indicators": [
                    f"{len(risk_ctx.ratios.high_risk_ratios())} high-risk ratios",
                    f"{len(risk_ctx.anomalies)} trend anomalies",
                    *[a['metric'] for a in ctx_dict['trend_anomalies'][:3]],
                ],
            },
        }


async def run_anomaly_detection(txns: list[Transaction]) -> dict:
    """调用 AnomalyDetectionAgent"""
    from agents.anomaly_detection.agent import AnomalyDetectionAgent
    agent = AnomalyDetectionAgent()
    rows = [
        {"id": t.transaction_id, "amount": float(t.amount), "date": t.transaction_date.isoformat(),
         "customer": t.party_id or "", "invoice": t.document_refs[0] if t.document_refs else ""}
        for t in txns
    ]
    req = AgentRequest(
        workflow_id="demo-assessment-001", project_id="p1", task_id="t2",
        firm_id="f1", client_id="c1", engagement_id="e1",
        inputs={"transactions": rows},
    )
    resp = await agent.execute(req)
    findings_total = resp.result.get("findings_total", 0)
    print(f"  [AnomalyDetection] {findings_total} findings found, confidence={resp.confidence:.0%}")
    return resp.result.get("artifact", {})


def build_documents(txns: list[Transaction], exception_txn_ids: set[str]) -> dict:
    """构造 Evidence Graph 用文档集合

    正常交易: INVOICE + DELIVERY 齐全
    截止例外: 只有 INVOICE，DELIVERY 缺失（发货在下期，本期无发货单）
    """
    from domain.finance.entities.transaction import Document, DocumentType

    docs: dict[str, Document] = {}
    for txn in txns:
        inv = Document(
            document_id=f"DOC-INV-{txn.transaction_id}",
            document_type=DocumentType.INVOICE,
            document_no=txn.document_refs[0] if txn.document_refs else "",
            document_date=txn.transaction_date,
            party_id=txn.party_id,
            amount=txn.amount,
            reference_no=txn.transaction_id,
        )
        # EvidenceMapper 通过 txn.document_refs (INV-XXXX) 查找 → key 用 document_no
        if inv.document_no:
            docs[inv.document_no] = inv

        if txn.transaction_id not in exception_txn_ids:
            dely = Document(
                document_id=f"DOC-DEL-{txn.transaction_id}",
                document_type=DocumentType.DELIVERY,
                document_no=f"DEL-{txn.transaction_id}",
                document_date=txn.transaction_date,
                party_id=txn.party_id,
                amount=txn.amount,
                reference_no=txn.transaction_id,
            )
            docs[dely.document_no] = dely
    return docs


def evidence_coverage_metric(graph, total_findings: int) -> dict:
    """Evidence Coverage (ISA 500) — 从 EvidenceGraph 计算

    - evidence_presence: 有 >=1 条 PRESENT 证据的 finding 比例
    - evidence_completeness: 所需证据类型全部 PRESENT 的 finding 比例
    """
    from domain.audit.entities.evidence_graph import EvidenceStatus

    if total_findings == 0:
        return {"total": 0, "presence": 0.0, "completeness": 0.0}

    # 按 finding 分组：每个 finding 聚合所有 assertion 的证据节点
    # （build_graph 按 finding 顺序追加节点，各组 assertion 的 finding 顺序一致）
    per_finding: list[list] = []
    if graph.assertions:
        n_findings = max(
            len(a.evidence_nodes) // len(a.required_evidence_types)
            if a.required_evidence_types else 0
            for a in graph.assertions
        )
        for i in range(n_findings):
            group: list = []
            for assertion in graph.assertions:
                required = assertion.required_evidence_types
                if not required:
                    continue
                nodes = assertion.evidence_nodes
                group.extend(nodes[i * len(required):(i + 1) * len(required)])
            per_finding.append(group)

    with_evidence = 0
    fully_evidenced = 0
    for group in per_finding:
        present_types = {n.evidence_type for n in group if n.status == EvidenceStatus.PRESENT}
        if present_types:
            with_evidence += 1
        required_types = {n.evidence_type for n in group}
        if present_types and present_types >= required_types:
            fully_evidenced += 1

    presence = with_evidence / total_findings * 100
    completeness = fully_evidenced / total_findings * 100
    return {
        "total": total_findings,
        "with_evidence": with_evidence,
        "fully_evidenced": fully_evidenced,
        "presence_pct": presence,
        "completeness_pct": completeness,
    }


async def main():
    print("=" * 70)
    print("  AuditFlow — Assessment-driven Revenue Cutoff Demo")
    print("=" * 70)

    txns = build_mock_transactions()
    records_raw = build_records_raw(txns)
    print(f"\n[Data] {len(txns)} transactions, 4 cutoff exceptions implanted")

    # Phase 1: 并行风险分析
    print("\n[Phase 1] Parallel Risk Assessment")
    risk_art, finding_art = await asyncio.gather(
        run_risk_agent(txns),
        run_anomaly_detection(txns),
    )

    # Phase 2: Assessment 融合
    print("\n[Phase 2] AssessmentBuilder merge")
    builder = AssessmentService()
    assessment = builder.build(risk_artifact=risk_art, finding_artifact=finding_art)
    print(f"  overall_risk={assessment.overall_risk} confidence={assessment.confidence:.0%}")
    print(f"  rules: {assessment.policy_decisions}")

    # Phase 2.5: Review Queue (HITL — ISA 500)
    print("\n[Phase 2.5] Review Queue (HITL)")
    from application.assessment.review_queue import (
        build_review_queue, ReviewDecision, ReviewStatus,
    )
    queue = build_review_queue(assessment)
    item = queue.items[0]
    print(f"  Pending review: [{item.risk_level}] {item.summary}")
    print(f"  Evidence status: {item.evidence_summary}")
    # 模拟审计师决策 — MEDIUM risk + 证据不完整 → NEED_MORE_EVIDENCE
    if item.risk_level == "MEDIUM" and "incomplete" in item.evidence_summary:
        item.review(ReviewDecision.NEED_MORE_EVIDENCE, comment="Request delivery notes for cutoff exceptions")
        print(f"  Reviewer decision: NEED_MORE_EVIDENCE (request delivery notes)")
    else:
        item.review(ReviewDecision.ACCEPT, comment="Approved by reviewer")
        print(f"  Reviewer decision: ACCEPT")
    print(f"  Queue: {queue.summary()}")

    # Phase 3: 程序规划
    print("\n[Phase 3] ProcedurePlanningService")
    planner = ProcedurePlanningService()
    program = planner.build_program(assessment, area="Revenue")
    print(f"  area={program.area} risk={program.risk_level} procedures={len(program.procedures)}")
    for p in program.procedures:
        print(f"    - {p.name} [{p.procedure_type.value}] sampling={p.sampling.method.value}")

    # Phase 4: 执行（使用标准 Cutoff 程序）
    print("\n[Phase 4] CutoffProcedureExecutor")
    executor = CutoffProcedureExecutor()
    cutoff_proc = generate_cutoff_program().procedures[0]
    cutoff_proc.sampling = SamplingConfig(method=SamplingMethod.ALL, population_size=len(txns), sample_size=len(txns), key_field="transaction_date")
    findings = executor.execute(cutoff_proc, txns, records_raw, date(2024, 12, 31))
    print(f"  exceptions found: {len(findings)}")
    for f in findings:
        print(f"    - [{f.severity.value}] {f.description} (txn={f.transaction_ref}, amt={f.amount})")

    # Phase 5: Evidence Graph + Evidence Coverage (ISA 500)
    print("\n[Phase 5] Evidence Graph & Coverage (ISA 500)")
    exception_txn_ids = {f.transaction_ref for f in findings}
    documents = build_documents(txns, exception_txn_ids)
    from domain.audit.entities.evidence_graph import EvidenceMapper
    graph = EvidenceMapper().build_graph(cutoff_proc, txns, findings, documents)
    summary = graph.summary()
    print(f"  Overall Conclusion: {summary['overall']}")
    print(f"  Overall Coverage  : {summary['overall_coverage']}")
    for a in summary["assertions"]:
        print(f"    - [{a['type']}] coverage={a['coverage']} present={a['present']} missing={a['missing']}")
    print(f"  Missing Evidence  : {len(summary['missing_evidence'])} items")

    # Evidence Coverage 指标 (ISA 500)
    coverage_metric = evidence_coverage_metric(graph, len(findings))
    print(f"  Evidence Presence    : {coverage_metric['presence_pct']:.0f}% "
          f"({coverage_metric['with_evidence']}/{coverage_metric['total']} findings have >=1 evidence)")
    print(f"  Evidence Completeness: {coverage_metric['completeness_pct']:.0f}% "
          f"({coverage_metric['fully_evidenced']}/{coverage_metric['total']} findings fully evidenced)")

    # 结果摘要
    print("\n" + "=" * 70)
    print("  Pipeline Summary")
    print("=" * 70)
    print(f"  Risk Assessment  : {assessment.overall_risk} ({assessment.confidence:.0%} confidence)")
    print(f"  Anomaly Findings : {len(assessment.detected_findings)}")
    print(f"  Procedures       : {len(program.procedures)}")
    print(f"  Exceptions       : {len(findings)}")
    print(f"  Opinion          : {('MODIFIED' if len(findings) > 0 else 'UNMODIFIED')}")
    print(f"\n  All new components connected end-to-end:")
    print(f"    FindingArtifact -> AnomalyDetectionAgent -> AssessmentBuilder")
    print(f"    -> ProcedurePlanningService -> CutoffProcedureExecutor")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
