"""Human Evaluation + Citation Support LLM Judge

用法: py -3.11 scripts/human_eval.py
"""

import asyncio
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"), override=True)

from human_eval_cases import HUMAN_CASES


def soft_match(predicted: list[str], expected: list[str]) -> float:
    """宽松匹配：expected 中任一关键词出现在任一 predicted 中"""
    pred_text = " ".join(p.lower() for p in predicted)
    exp_lower = [e.lower() for e in expected]
    matched = sum(1 for e in exp_lower if e in pred_text or any(e in p.lower() for p in predicted))
    return matched / len(exp_lower) if exp_lower else 0.0


def evidence_recall(agent_text: str, gold_keywords: list[str]) -> float:
    """Agent 输出中是否提到了 gold 关键词"""
    text_lower = agent_text.lower()
    found = sum(1 for kw in gold_keywords if kw.lower() in text_lower)
    return found / len(gold_keywords) if gold_keywords else 0.0


def print_bar(score: float, label: str, width: int = 40):
    filled = int(score * width)
    bar = "#" * filled + " " * (width - filled)
    print(f"    {label:<30} {score:.1%} |{bar}|")


async def run_human_eval():
    """Human Evaluation — 对 10 个标注 Case 跑 Risk Agent"""
    from agents.risk.agent import LlmRiskAgent
    from domain.contracts import AgentRequest

    agent = LlmRiskAgent()
    results = []
    metrics = {"risk_accuracy": 0.0, "severity_accuracy": 0.0, "evidence_recall": 0.0}

    print(f"\n{'='*65}")
    print(f"  Human Evaluation — {len(HUMAN_CASES)} annotated cases")
    print(f"{'='*65}\n")

    for case in HUMAN_CASES:
        req = AgentRequest(
            workflow_id="human_eval", project_id="human", task_id=case["id"],
            firm_id="eval", client_id="eval", engagement_id="eval",
            inputs=case["input"],
        )
        resp = await agent.execute(req)
        rd = resp.model_dump()
        res = rd.get("result", rd)
        gold = case["gold"]

        # Metrics
        risk_acc = soft_match(res.get("detected_risks", []), gold["expected_risks"])
        sev_acc = 1.0 if res.get("severity", "").lower() == gold["severity"].lower() else 0.0
        ev_recall = evidence_recall(str(res), gold["evidence_keywords"])

        metrics["risk_accuracy"] += risk_acc
        metrics["severity_accuracy"] += sev_acc
        metrics["evidence_recall"] += ev_recall

        result = {
            "id": case["id"],
            "description": case["description"],
            "gold_severity": gold["severity"],
            "agent_severity": res.get("severity", "N/A"),
            "gold_risks": gold["expected_risks"],
            "agent_risks": res.get("detected_risks", []),
            "risk_accuracy": round(risk_acc, 4),
            "severity_accuracy": sev_acc,
            "evidence_recall": round(ev_recall, 4),
        }
        results.append(result)

        status = "[OK]" if sev_acc == 1.0 and risk_acc > 0 else "[WARN]"
        print(f"  {status} {case['id']}: {case['description'][:40]}")
        print(f"       Gold: {gold['severity']} / {'; '.join(gold['expected_risks'])}")
        print(f"       Agent: {res.get('severity','?')} / {'; '.join(res.get('detected_risks',[]))}")
        print(f"       risk_acc={risk_acc:.0%} sev_acc={sev_acc:.0%} ev_recall={ev_recall:.0%}")
        print()

    n = len(HUMAN_CASES)
    avg = {k: round(v / n, 4) for k, v in metrics.items()}

    print(f"{'='*65}")
    print(f"  Results ({n} cases)")
    print(f"{'='*65}")
    print_bar(avg["risk_accuracy"], "Risk Classification")
    print_bar(avg["severity_accuracy"], "Severity Agreement")
    print_bar(avg["evidence_recall"], "Evidence Recall")
    print()

    # Summary per case
    print(f"{'='*65}")
    print(f"  Per-Case Detail")
    print(f"{'='*65}")
    for r in results:
        sev_match = "[OK]" if r["severity_accuracy"] else "[FAIL]"
        print(f"  {r['id']}: risk={r['risk_accuracy']:.0%} sev={sev_match} ev={r['evidence_recall']:.0%}")
        print(f"       Gold:   {r['gold_severity']} | {'; '.join(r['gold_risks'])}")
        print(f"       Agent:  {r['agent_severity']} | {'; '.join(r['agent_risks'])}")

    return {"metrics": avg, "cases": results}


async def run_citation_support_judge():
    """LLM Judge — 判断 citation 是否支持 risk claim"""
    from infrastructure.llm.deepseek_provider import DeepSeekProvider
    from infrastructure.llm.models import LLMMessage

    provider = DeepSeekProvider()
    test_cases = [
        {"risk": "Revenue recognition risk", "evidence": "The company's revenue grew 45% in Q4, primarily from contracts signed in the last week of December."},
        {"risk": "Inventory obsolescence risk", "evidence": "The company has a strong balance sheet with $500M in cash and marketable securities."},
        {"risk": "Going concern risk", "evidence": "Current ratio of 0.8, debt of $50M due within 6 months, only $10M cash available."},
    ]

    print(f"\n{'='*65}")
    print(f"  Citation Support — LLM Judge")
    print(f"{'='*65}\n")

    prompt_template = """You are an audit evidence validator. Determine if the provided EVIDENCE supports the RISK claim.

RISK: {risk}
EVIDENCE: {evidence}

Respond with ONLY a JSON object:
{{"supports": true/false, "confidence": 0.0-1.0, "reason": "one sentence explanation"}}"""

    for tc in test_cases:
        prompt = prompt_template.format(risk=tc["risk"], evidence=tc["evidence"])
        resp = await provider.generate([
            LLMMessage(role="system", content="You are an audit evidence validator. Return ONLY valid JSON."),
            LLMMessage(role="user", content=prompt),
        ])
        try:
            result = json.loads(resp.content)
            supports = result.get("supports", False)
            conf = result.get("confidence", 0)
            reason = result.get("reason", "")
        except (json.JSONDecodeError, AttributeError):
            supports = False
            conf = 0
            reason = "Parse failed"

        status = "OK" if supports else "NO"
        print(f"  [{status}] (conf={conf:.0%}) {tc['risk'][:45]}")
        print(f"           evidence: {tc['evidence'][:60]}...")
        print(f"           reason: {reason}")
        print()

    print(f"  Tested {len(test_cases)} claim-evidence pairs")


async def main():
    print("=" * 70)
    print("  AuditFlow Human Evaluation + Citation Support")
    print("=" * 70)

    # Step 1: Human Evaluation
    result = await run_human_eval()

    # Step 2: Citation Support LLM Judge
    await run_citation_support_judge()

    # Save
    out = os.path.join(os.path.dirname(__file__), "human_eval_output")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, f"human_eval_{datetime.now().strftime('%H%M%S')}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n  Report: {path}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
