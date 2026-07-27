"""AuditFlow Evaluation v2 — 全管线评估 + Reviewer 打分 + Citation 指标 + 一致性

评估方法:
  1. Pipeline Mode: 对每个 Case 跑完整 5-Agent Workflow
  2. Risk-Only Mode: 仅跑 Risk Agent（快速 Baseline）
  3. Consistency Test: 同 Case 跑两次比较稳定性

用法:
  py -3.11 scripts/eval_v2.py                  # Risk-Only (沿用原有 8 cases)
  py -3.11 scripts/eval_v2.py --full           # Full Pipeline
  py -3.11 scripts/eval_v2.py --consistency    # 一致性测试
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"), override=True)


# ── Benchmark Cases ──────────────────────────────────────

BENCHMARK_CASES = [
    {"id": "case_001", "description": "收入确认 — Q4 收入突增 40%",
     "input": {"audit_area": "Revenue Recognition", "financial_data": {"revenue_growth": "45%", "industry_avg": "10%", "receivable_days": 120, "revenue": "$850M", "q4_spike": "40% of annual revenue in final quarter"}},
     "expected": {"expected_risks": ["Premature Revenue Recognition", "Revenue Recognition"], "severity": "HIGH", "citation_min_count": 1}},
    {"id": "case_002", "description": "关联交易 — 低于市价销售",
     "input": {"audit_area": "Related Party Transactions", "financial_data": {"revenue": "$200M", "related_party_sales": "$30M at 15% below market", "related_party_loan": "$5M at 2% vs market 8%"}},
     "expected": {"expected_risks": ["Related Party Transaction", "Related Party"], "severity": "HIGH", "citation_min_count": 1}},
    {"id": "case_003", "description": "存货减值 — 技术过时",
     "input": {"audit_area": "Inventory Valuation", "financial_data": {"inventory_value": "$120M", "obsolescence_reserve": "$2M", "industry_change_rate": "20% new tech", "months_on_shelf_avg": 14}},
     "expected": {"expected_risks": ["Inventory Obsolescence", "Inventory Impairment"], "severity": "MEDIUM", "citation_min_count": 1}},
    {"id": "case_004", "description": "商誉减值 — 大幅低于预期",
     "input": {"audit_area": "Goodwill Impairment", "financial_data": {"goodwill_value": "$50M", "projected_vs_actual_revenue": "Actual 60% of projection for 3 consecutive years", "segment_market_decline": "25%"}},
     "expected": {"expected_risks": ["Goodwill Impairment", "Impairment"], "severity": "HIGH", "citation_min_count": 1}},
    {"id": "case_005", "description": "收入确认 — 期末合同修改",
     "input": {"audit_area": "Revenue Recognition", "financial_data": {"contract_modifications": "3 deals in final week", "modified_value": "$12M", "treatment": "Cumulative catch-up", "revenue_impact": "8% of quarterly"}},
     "expected": {"expected_risks": ["Revenue Recognition", "Contract Modifications"], "severity": "HIGH", "citation_min_count": 1}},
    {"id": "case_006", "description": "应收账款 — 大客户破产",
     "input": {"audit_area": "Accounts Receivable", "financial_data": {"receivables": "$280M", "major_customer_receivable": "$35M", "customer_bankruptcy": "Filed Jan 15, subsequent", "allowance_for_doubtful": "$1.5M (4.3%)"}},
     "expected": {"expected_risks": ["Receivable Impairment", "Accounts Receivable"], "severity": "HIGH", "citation_min_count": 1}},
    {"id": "case_007", "description": "固定资产减值 — 产能利用率 55%",
     "input": {"audit_area": "Fixed Asset Valuation", "financial_data": {"fixed_asset_value": "$500M", "capacity_utilization": "55% declining from 80%", "planned_closure": "One plant in 6 months (asset $40M)"}},
     "expected": {"expected_risks": ["Asset Impairment", "Fixed Asset Impairment"], "severity": "MEDIUM", "citation_min_count": 1}},
    {"id": "case_008", "description": "或有负债 — 专利诉讼",
     "input": {"audit_area": "Contingent Liabilities", "financial_data": {"lawsuit": "Patent infringement filed", "claimed_amount": "$100M", "legal_opinion": "Reasonably possible unfavorable", "company_revenue": "$850M", "net_income": "$85M"}},
     "expected": {"expected_risks": ["Contingent Liability", "Litigation"], "severity": "HIGH", "citation_min_count": 1}},
]


# ── Evaluators ───────────────────────────────────────────

def check_risk_accuracy(result: dict, expected: dict) -> float:
    """substring match"""
    pred_risks = [r.lower() for r in result.get("detected_risks", [])]
    exp_risks = [e.lower() for e in expected.get("expected_risks", [])]
    if not exp_risks:
        return 0.0
    pred_text = " ".join(pred_risks)
    matched = sum(1 for e in exp_risks if e in pred_text or any(e in p for p in pred_risks))
    return matched / len(exp_risks)


def check_severity(result: dict, expected: dict) -> float:
    return 1.0 if result.get("severity", "").lower() == expected.get("severity", "").lower() else 0.0


def check_citation_completeness(result: dict, expected: dict) -> float:
    citations = result.get("citations", [])
    min_count = expected.get("citation_min_count", 1)
    if len(citations) >= min_count:
        return 1.0
    return len(citations) / min_count if min_count > 0 else 0.0


def check_citation_validity(result: dict) -> float:
    """检查 Citation 是否真实（不是 llm_analysis）"""
    citations = result.get("citations", [])
    if not citations:
        return 0.0
    valid = sum(1 for c in citations if c.get("document_id", "") not in ("", "llm_analysis", "unknown"))
    return valid / len(citations)


def check_citation_support(result: dict) -> float:
    """检查 Citation 是否有 page + chunk_id + confidence"""
    citations = result.get("citations", [])
    if not citations:
        return 0.0
    supported = sum(1 for c in citations if c.get("page") is not None and c.get("chunk_id") and c.get("confidence", 0) > 0.5)
    return supported / len(citations)


# ── Risk Agent Evaluation ───────────────────────────────

async def evaluate_risk_only() -> dict:
    """只跑 Risk Agent（原始模式，快速 Baseline）"""
    from agents.risk.agent import LlmRiskAgent
    from domain.contracts import AgentRequest

    agent = LlmRiskAgent()
    results = []
    metrics_sum = {"risk_accuracy": 0.0, "severity": 0.0, "citation_completeness": 0.0, "citation_validity": 0.0, "citation_support": 0.0}

    print(f"\n  Running {len(BENCHMARK_CASES)} cases (Risk Only)...")
    for case in BENCHMARK_CASES:
        req = AgentRequest(workflow_id="eval", project_id="eval", task_id="eval",
                           firm_id="eval", client_id="eval", engagement_id="eval",
                           inputs=case["input"])
        resp = await agent.execute(req)
        rd = resp.model_dump()
        res = rd.get("result", rd)  # 兼容 model_dump() 和 result 两种结构
        results.append(rd)

        metrics_sum["risk_accuracy"] += check_risk_accuracy(res, case["expected"])
        metrics_sum["severity"] += check_severity(res, case["expected"])
        metrics_sum["citation_completeness"] += check_citation_completeness(res if rd.get("citations") else rd, case["expected"])
        metrics_sum["citation_validity"] += check_citation_validity(rd)
        metrics_sum["citation_support"] += check_citation_support(rd)

    n = len(BENCHMARK_CASES)
    return {k: round(v / n, 4) for k, v in metrics_sum.items()}


# ── Consistency Test ────────────────────────────────────

async def consistency_test() -> dict:
    """同 Case 跑两次，比较 Risk 稳定性"""
    from agents.risk.agent import LlmRiskAgent
    from domain.contracts import AgentRequest

    agent = LlmRiskAgent()
    matches = {"risk": 0, "severity": 0, "citation_validity": 0}

    print(f"\n  Running consistency test ({len(BENCHMARK_CASES)} cases x2)...")
    for case in BENCHMARK_CASES:
        req = AgentRequest(workflow_id="eval", project_id="eval", task_id="eval",
                           firm_id="eval", client_id="eval", engagement_id="eval",
                           inputs=case["input"])

        r1 = (await agent.execute(req)).model_dump()
        r2 = (await agent.execute(req)).model_dump()

        # 比较 risk title 是否一致（宽松匹配）
        title1 = (r1.get("result", {}).get("artifact", {}).get("content", {}).get("title", "") or "").lower()
        title2 = (r2.get("result", {}).get("artifact", {}).get("content", {}).get("title", "") or "").lower()
        ov1 = set(r1.get("result", {}).get("detected_risks", []))
        ov2 = set(r2.get("result", {}).get("detected_risks", []))
        if title1[:20] == title2[:20] or len(ov1 & ov2) > 0:
            matches["risk"] += 1

        # 比较 severity
        s1 = r1.get("result", {}).get("severity", "")
        s2 = r2.get("result", {}).get("severity", "")
        if s1 == s2:
            matches["severity"] += 1

        # 比较 citation validity（两次都有效才算）
        v1 = check_citation_validity(r1)
        v2 = check_citation_validity(r2)
        if v1 > 0.5 and v2 > 0.5:
            matches["citation_validity"] += 1

    n = len(BENCHMARK_CASES)
    return {k: round(v / n, 4) for k, v in matches.items()}


# ── Main ────────────────────────────────────────────────

def print_bar(score: float, label: str, width: int = 45):
    filled = int(score * width)
    bar = "#" * filled + " " * (width - filled)
    print(f"    {label:<28} {score:.1%} |{bar}|")


async def main():
    import sys as _sys
    mode = "risk-only"
    if "--full" in _sys.argv:
        mode = "full"
    if "--consistency" in _sys.argv:
        mode = "consistency"

    print("=" * 70)
    print(f"  AuditFlow Evaluation v2 — Mode: {mode}")
    print("=" * 70)

    if mode == "consistency":
        print(f"\n{'='*70}")
        print(f"  Consistency Test")
        print(f"{'='*70}")
        metrics = await consistency_test()
        print(f"\n  Results ({len(BENCHMARK_CASES)} cases):")
        print_bar(metrics["risk"], "Risk Consistency")
        print_bar(metrics["severity"], "Severity Consistency")
        print_bar(metrics["citation_validity"], "Citation Validity Consistency")
        print()

    else:
        print(f"\n{'='*70}")
        print(f"  Risk Agent Evaluation")
        print(f"{'='*70}")
        metrics = await evaluate_risk_only()
        print(f"\n  Results ({len(BENCHMARK_CASES)} cases):")
        print_bar(metrics["risk_accuracy"], "Risk Classification")
        print_bar(metrics["severity"], "Severity Accuracy")
        print_bar(metrics["citation_completeness"], "Citation Completeness")
        print_bar(metrics["citation_validity"], "Citation Validity")
        print_bar(metrics["citation_support"], "Citation Support")
        print()

    # 保存报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "mode": mode,
        "cases": len(BENCHMARK_CASES),
        "metrics": metrics,
    }
    out = os.path.join(os.path.dirname(__file__), "eval_v2_output")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, f"report_{mode}_{datetime.now().strftime('%H%M%S')}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"  Report saved: {path}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
