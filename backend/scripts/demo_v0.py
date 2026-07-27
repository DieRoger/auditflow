"""Vertical Slice V0 — LLM Demo: 5 Agent chain with DeepSeek"""
import asyncio
import os
# 设置 DeepSeek API Key（优先使用环境变量，其次从 .env 加载）
os.environ.setdefault("DEEPSEEK_API_KEY", os.getenv("DEEPSEEK_API_KEY", ""))
from agents.evidence.agent import LlmEvidenceAgent
from agents.knowledge.agent import LlmKnowledgeAgent
from agents.planner.agent import LlmPlannerAgent
from agents.reviewer.agent import LlmReviewerAgent
from agents.risk.agent import LlmRiskAgent
from domain.contracts import AgentRequest


async def main():
    print("=" * 60)
    print("  AuditFlow - LLM-Powered Audit Demo")
    print("=" * 60)

    agents = {"planner": LlmPlannerAgent(), "knowledge": LlmKnowledgeAgent(),
              "risk": LlmRiskAgent(), "evidence": LlmEvidenceAgent(), "reviewer": LlmReviewerAgent()}
    ctx = {}

    # Step 1: Planner
    print("\n1. Planner Agent - task decomposition...")
    r = await agents["planner"].execute(AgentRequest(workflow_id="d", project_id="d", task_id="t",
        firm_id="d", client_id="d", engagement_id="d",
        inputs={"audit_area": "Revenue Recognition", "project_context": {"company": "ABC Mfg"}},
        context=ctx, memory={}))
    print(f"   Plan steps: {len(r.result.get('plan', []))}")
    ctx["planner_output"] = r.result

    # Step 2: Knowledge
    print("2. Knowledge Agent - standards retrieval...")
    r = await agents["knowledge"].execute(AgentRequest(workflow_id="d", project_id="d", task_id="t",
        firm_id="d", client_id="d", engagement_id="d",
        inputs={"audit_area": "Revenue Recognition"},
        context={"risk_summary": "Revenue growth 45% vs industry 10%"}, memory={}))
    print(f"   Standards: {len(r.result.get('standards', []))}")

    # Step 3: Risk
    print("3. Risk Agent - risk identification...")
    r = await agents["risk"].execute(AgentRequest(workflow_id="d", project_id="d", task_id="t",
        firm_id="d", client_id="d", engagement_id="d",
        inputs={"audit_area": "Revenue Recognition", "financial_data": {"revenue_growth": "45%"}},
        context=ctx, memory={}))
    risk_title = r.result.get("artifact", {}).get("content", {}).get("title", "N/A")
    risk_level = r.result.get("risk_level", "N/A")
    print(f"   Risk: {risk_title} [{risk_level}]")
    print(f"   Tokens: {r.metrics.get('tokens')}")
    ctx["risk_output"] = r.result

    # Step 4: Evidence
    print("4. Evidence Agent - evidence analysis...")
    r = await agents["evidence"].execute(AgentRequest(workflow_id="d", project_id="d", task_id="t",
        firm_id="d", client_id="d", engagement_id="d",
        inputs={"claims_to_verify": ["Revenue growth 45% exceeds industry"], "financial_data": {}},
        context=ctx, memory={}))
    print(f"   Coverage: {r.result.get('coverage',0):.0%}")

    # Step 5: Reviewer
    print("5. Reviewer Agent - quality review...")
    r = await agents["reviewer"].execute(AgentRequest(workflow_id="d", project_id="d", task_id="t",
        firm_id="d", client_id="d", engagement_id="d",
        inputs={}, context=ctx, memory={}))
    print(f"   Quality: {r.result.get('quality_score',0):.0%}")
    print(f"   Next: {r.next_action}")

    print("\n" + "=" * 60)
    print("  Done: All 5 agents used DeepSeek API")
    print("=" * 60)

asyncio.run(main())
