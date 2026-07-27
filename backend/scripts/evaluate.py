"""Evaluation — 一键评估 + Baseline 建立

评估 Risk Agent 的风险识别能力，同时验证 Evidence 和 Grounding。
建立 Baseline 指标，后续可对比 Prompt 优化的效果。

用法: python -m scripts.evaluate
"""

import asyncio
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"), override=True)


# ── 审计风险 Benchmark Cases ──────────────────────────────

BENCHMARK_CASES = [
    {
        "id": "case_001",
        "description": "收入确认 — Q4 收入突增",
        "input": {
            "audit_area": "Revenue Recognition",
            "financial_data": {
                "revenue_growth": "45%",
                "industry_avg": "10%",
                "receivable_days": 120,
                "revenue": "$850M",
                "q4_spike": "40% of annual revenue in final quarter",
            },
        },
        "expected": {
            "expected_risks": ["Premature Revenue Recognition", "Revenue Recognition"],
            "severity": "HIGH",
            "citation_min_count": 1,
        },
    },
    {
        "id": "case_002",
        "description": "关联交易 — 低于市价销售",
        "input": {
            "audit_area": "Related Party Transactions",
            "financial_data": {
                "revenue": "$200M",
                "related_party_sales": "$30M at 15% below market",
                "related_party_loan": "$5M at 2% vs market 8%",
                "industry_avg_interest": "8%",
            },
        },
        "expected": {
            "expected_risks": ["Related Party Transaction", "Related Party"],
            "severity": "HIGH",
            "citation_min_count": 1,
        },
    },
    {
        "id": "case_003",
        "description": "存货减值 — 技术进步导致产品过时",
        "input": {
            "audit_area": "Inventory Valuation",
            "financial_data": {
                "inventory_value": "$120M",
                "obsolescence_reserve": "$2M",
                "industry_change_rate": "20% new tech adoption",
                "months_on_shelf_avg": 14,
                "revenue_decline": "15% in legacy product line",
            },
        },
        "expected": {
            "expected_risks": ["Inventory Obsolescence", "Inventory Impairment"],
            "severity": "MEDIUM",
            "citation_min_count": 1,
        },
    },
    {
        "id": "case_004",
        "description": "商誉减值 — 收购业务未达标",
        "input": {
            "audit_area": "Goodwill Impairment",
            "financial_data": {
                "goodwill_value": "$50M",
                "acquisition_date": "2021",
                "projected_vs_actual_revenue": "Actual 60% of projection for 3 consecutive years",
                "segment_market_decline": "25%",
                "planned_restructuring": "Yes",
            },
        },
        "expected": {
            "expected_risks": ["Goodwill Impairment", "Impairment"],
            "severity": "HIGH",
            "citation_min_count": 1,
        },
    },
    {
        "id": "case_005",
        "description": "收入确认 — 合同修改在报告期末",
        "input": {
            "audit_area": "Revenue Recognition",
            "financial_data": {
                "contract_modifications": "3 deals in final week of period",
                "modified_value": "$12M",
                "treatment": "Cumulative catch-up method applied",
                "revenue_impact": "8% of quarterly revenue",
            },
        },
        "expected": {
            "expected_risks": ["Revenue Recognition", "Contract Modifications"],
            "severity": "HIGH",
            "citation_min_count": 1,
        },
    },
    {
        "id": "case_006",
        "description": "应收账款 — 大客户破产",
        "input": {
            "audit_area": "Accounts Receivable",
            "financial_data": {
                "receivables": "$280M",
                "major_customer_receivable": "$35M",
                "customer_bankruptcy": "Filed on Jan 15, subsequent to year end",
                "allowance_for_doubtful": "$1.5M (4.3% of risk)",
                "industry_default_rate": "2.1%",
            },
        },
        "expected": {
            "expected_risks": ["Receivable Impairment", "Accounts Receivable"],
            "severity": "HIGH",
            "citation_min_count": 1,
        },
    },
    {
        "id": "case_007",
        "description": "固定资产 — 减值迹象",
        "input": {
            "audit_area": "Fixed Asset Valuation",
            "financial_data": {
                "fixed_asset_value": "$500M",
                "asset_type": "Manufacturing equipment in declining industry",
                "capacity_utilization": "55% (declining from 80% 2 years ago)",
                "planned_closure": "One plant to close in 6 months (asset value $40M)",
            },
        },
        "expected": {
            "expected_risks": ["Asset Impairment", "Fixed Asset Impairment"],
            "severity": "MEDIUM",
            "citation_min_count": 1,
        },
    },
    {
        "id": "case_008",
        "description": "诉讼 — 专利侵权可能产生重大负债",
        "input": {
            "audit_area": "Contingent Liabilities",
            "financial_data": {
                "lawsuit": "Patent infringement filed against company",
                "claimed_amount": "$100M",
                "legal_opinion": "Reasonably possible unfavorable outcome",
                "disclosed_in_financials": "No, as contingent liability",
                "company_revenue": "$850M",
                "net_income": "$85M",
            },
        },
        "expected": {
            "expected_risks": ["Contingent Liability", "Litigation"],
            "severity": "HIGH",
            "citation_min_count": 1,
        },
    },
]


async def evaluate_risk_agent() -> dict:
    """用 Benchmark Cases 评估 Risk Agent"""
    from evaluation.metrics import (
        RiskClassificationAccuracy,
        SeverityAccuracy,
        CitationCompleteness,
        EvaluationReport,
    )
    from evaluation.runner import EvaluationRunner
    from agents.risk.agent import LlmRiskAgent

    # 构建 Benchmark
    from evaluation.metrics import Benchmark, BenchmarkCase
    agent_name = "risk_agent"

    cases = []
    for c in BENCHMARK_CASES:
        cases.append(BenchmarkCase(
            id=c["id"],
            description=c["description"],
            input=c["input"],
            expected=c["expected"],
            evaluation_metrics=["risk_classification_accuracy", "severity_accuracy", "citation_completeness"],
        ))

    benchmark = Benchmark(name="audit_risk_baseline", version="v1", cases=cases)

    metrics = [
        RiskClassificationAccuracy(),
        SeverityAccuracy(),
        CitationCompleteness(),
    ]

    runner = EvaluationRunner(metrics)
    agent = LlmRiskAgent()

    print(f"  Running {len(cases)} cases through {agent_name}...")
    report: EvaluationReport = await runner.run(agent, benchmark)
    return report.model_dump()


async def run_grounding_check(agent_results: list[dict]) -> dict:
    """对 Agent 输出做事后 Grounding 验证"""
    from infrastructure.evidence.grounding import GroundingChecker

    checker = GroundingChecker()
    total_claims = 0
    grounded_claims = 0
    avg_hallucination = 0.0
    details = []

    for i, result in enumerate(agent_results):
        case = BENCHMARK_CASES[i]
        artifact = result.get("result", {}).get("artifact", {})
        content = artifact.get("content", {})
        title = content.get("title", "N/A")
        citations = result.get("citations", [])

        total_claims += 1
        g = await checker.verify(title, citations)
        details.append({
            "case_id": case["id"],
            "claim": title[:60],
            "grounded": g.grounded,
            "score": g.score,
            "hallucination_risk": g.hallucination_risk,
            "reason": "No citations" if g.hallucination_risk >= 0.8 else "OK",
        })
        if g.grounded:
            grounded_claims += 1
        avg_hallucination += g.hallucination_risk

    avg_hallucination /= len(agent_results) if agent_results else 1

    return {
        "total_claims": total_claims,
        "grounded_claims": grounded_claims,
        "grounding_rate": round(grounded_claims / total_claims, 4) if total_claims else 0,
        "avg_hallucination_risk": round(avg_hallucination, 4),
        "details": details,
    }


async def main():
    print("=" * 70)
    print("  AuditFlow Evaluation — Risk Agent Baseline")
    print("=" * 70)
    print()

    # Step 1: Risk Agent Evaluation
    print("[1/3] Running Risk Agent benchmark...")
    report = await evaluate_risk_agent()
    metrics = report["metrics"]

    print(f"\n  Agent: {report['agent_name']}")
    print(f"  Benchmark: {report['benchmark_name']}")
    print(f"  Duration: {report['duration_seconds']}s")
    print()
    print("  Metrics:")
    for name, score in metrics.items():
        bar = "#" * int(score * 50)
        space = " " * (50 - int(score * 50))
        print(f"    {name:<28} {score:.2%} |{bar}{space}|")

    # Step 2: Run all cases individually for Grounding
    print(f"\n[2/3] Running Grounding Check on Agent outputs...")
    from agents.risk.agent import LlmRiskAgent

    agent = LlmRiskAgent()
    all_results = []
    for i, case in enumerate(BENCHMARK_CASES):
        domain_contracts_module = __import__("domain.contracts", fromlist=["AgentRequest"])
        AgentRequest = domain_contracts_module.AgentRequest
        req = AgentRequest(
            workflow_id="eval",
            project_id="eval",
            task_id="eval",
            firm_id="eval",
            client_id="eval",
            engagement_id="eval",
            inputs=case["input"],
        )
        resp = await agent.execute(req)
        all_results.append(resp.model_dump())
        print(f"    [{i+1}/{len(BENCHMARK_CASES)}] {case['id']}: {resp.result.get('artifact',{}).get('content',{}).get('title','N/A')[:50]}...")

    grounding = await run_grounding_check(all_results)
    g = grounding
    bar_g = "#" * int(g["grounding_rate"] * 50)
    print(f"\n  Grounding Rate: {g['grounding_rate']:.0%} |{bar_g}{' '*(50-int(g['grounding_rate']*50))}|")
    print(f"  Avg Hallucination Risk: {g['avg_hallucination_risk']:.0%}")
    print()
    for d in g["details"]:
        icon = "GROUNDED" if d["grounded"] else "UNGROUNDED"
        print(f"    [{icon}] {d['claim'][:55]} ({d['hallucination_risk']:.0%} risk)")
        if not d["grounded"]:
            print(f"           {d['reason']}")

    # Step 3: 输出报告
    print(f"\n[3/3] Generating Baseline report...")

    report_data = {
        "timestamp": datetime.now().isoformat(),
        "agent_name": report["agent_name"],
        "benchmark_name": report["benchmark_name"],
        "cases": len(BENCHMARK_CASES),
        "metrics": metrics,
        "grounding": {
            "rate": grounding["grounding_rate"],
            "avg_hallucination_risk": grounding["avg_hallucination_risk"],
        },
        "duration_seconds": report["duration_seconds"],
        "passed": report["passed"],
    }

    output_dir = os.path.join(os.path.dirname(__file__), "eval_output")
    os.makedirs(output_dir, exist_ok=True)

    path = os.path.join(output_dir, "baseline_report.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    print(f"  Report saved: {path}")
    print()

    # 验收标准检查
    print("=" * 70)
    print("  Acceptance Checklist")
    print("=" * 70)

    has_recall = "risk_classification_accuracy" in metrics
    print(f"  [{'OK' if has_recall else 'FAIL'}] Risk Classification Accuracy: {metrics.get('risk_classification_accuracy', 0):.0%}")

    has_severity = "severity_accuracy" in metrics
    print(f"  [{'OK' if has_severity else 'FAIL'}] Severity Accuracy: {metrics.get('severity_accuracy', 0):.0%}")

    has_citation = "citation_completeness" in metrics
    print(f"  [{'OK' if has_citation else 'FAIL'}] Citation Completeness: {metrics.get('citation_completeness', 0):.0%}")

    ground_ok = grounding["grounding_rate"] > 0
    print(f"  [{'OK' if ground_ok else 'FAIL'}] Grounding Check: {grounding['grounded_claims']}/{grounding['total_claims']} grounded")

    print(f"\n  Overall: {sum([has_recall, has_severity, has_citation, ground_ok])}/4 passed")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
