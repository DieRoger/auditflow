"""Test LLM Risk Agent"""
import asyncio
import os
os.environ.setdefault("DEEPSEEK_API_KEY", os.getenv("DEEPSEEK_API_KEY", ""))
from agents.risk.agent import LlmRiskAgent
from domain.contracts import AgentRequest


async def test():
    agent = LlmRiskAgent()
    req = AgentRequest(workflow_id="demo_001", project_id="test", task_id="t1",
        firm_id="f1", client_id="c1", engagement_id="e1",
        inputs={"audit_area": "Revenue Recognition",
                "financial_data": {"revenue_growth": "45%", "industry_avg": "10%", "receivable_days": 120}})
    resp = await agent.execute(req)
    print(f"Status: {resp.status}")
    risk = resp.result.get("artifact", {}).get("content", {})
    print(f"Risk: {risk.get('title', 'N/A')}")
    print(f"Severity: {risk.get('severity')}")
    print(f"Confidence: {resp.confidence}")
    print(f"Tokens: {resp.metrics.get('tokens')}")
    print(f"Model: {resp.metrics.get('model')}")

asyncio.run(test())
