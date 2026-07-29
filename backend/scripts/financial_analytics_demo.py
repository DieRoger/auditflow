"""Financial Analytics Demo — 财务分析引擎 + Risk Agent 联动

证明: 结构化财务数据 → 比率/趋势/异常 → Risk Agent 获得更深度的风险洞察
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"), override=True)

from domain.finance.services.analytics import (
    AccountAnalyzer, FinancialRiskIndicators, RatioEngine, TrendEngine,
)


async def main():
    print("=" * 65)
    print("  Financial Analytics → Risk Agent — Demo")
    print("=" * 65)

    # 1. 构建模拟财务数据（来自 Canonical Schema 的聚合）
    current = {
        "revenue": 850_000_000,
        "gross_profit": 280_000_000,
        "net_income": 85_000_000,
        "current_assets": 380_000_000,
        "current_liabilities": 475_000_000,
        "total_assets": 1_200_000_000,
        "total_liabilities": 780_000_000,
        "receivables": 280_000_000,
        "inventory": 120_000_000,
        "cogs": 570_000_000,
    }
    prior = {
        "revenue": 620_000_000,
        "net_income": 75_000_000,
        "total_assets": 1_050_000_000,
        "receivables": 180_000_000,
        "inventory": 85_000_000,
        "current_liabilities": 350_000_000,
    }

    print("\n[1] Ratio Analysis")
    ratio_engine = RatioEngine()
    ratios = ratio_engine.analyze(current)
    for r in ratios.ratios:
        flag = "!!" if r.risk_level == "HIGH" else "!" if r.risk_level == "MEDIUM" else "  "
        print(f"    {flag} {r.name:<20} {r.value:>8.2f} ({r.risk_level})")

    print("\n[2] Trend Analysis")
    trend_engine = TrendEngine()
    trends = trend_engine.analyze(current, prior)
    anomalies = trend_engine.anomaly_trends(trends)
    for t in trends:
        flag = "[ANOMALY]" if t.anomaly else "        "
        arrow = "↑" if t.direction == "up" else "↓" if t.direction == "down" else "→"
        print(f"    {flag} {t.metric:<20} {arrow} {t.change_pct:+.1f}%")

    print("\n[3] Significant Accounts")
    analyzer = AccountAnalyzer()
    account_data = {
        "Revenue": 850_000_000,
        "Receivables": 280_000_000,
        "Inventory": 120_000_000,
        "Cash": 50_000_000,
        "Fixed Assets": 500_000_000,
        "Goodwill": 50_000_000,
        "Payables": 150_000_000,
        "Long-term Debt": 200_000_000,
    }
    significant = analyzer.identify_significant(account_data, total=current["total_assets"])
    for a in significant:
        print(f"    {a['account']:<20} {a['percentage']:>5.1f}% ({a['risk']})")

    # 4. 构建 FinancialRiskIndicators → Risk Agent
    indicators = FinancialRiskIndicators(
        ratios=ratios,
        trends=trends,
        anomalies=anomalies,
        significant_accounts=significant,
    )

    print(f"\n[4] Risk Agent — analyzing FinancialRiskIndicators...")
    from agents.risk.agent import LlmRiskAgent
    from domain.contracts import AgentRequest

    agent = LlmRiskAgent()
    ctx = indicators.to_risk_context()
    resp = await agent.execute(AgentRequest(
        workflow_id="analytics_demo", project_id="demo", task_id="risk",
        firm_id="demo", client_id="demo", engagement_id="demo",
        inputs={
            "audit_area": "Overall Financial Statement Risk",
            "financial_data": ctx,
        },
    ))
    risk = resp.result.get("artifact", {}).get("content", {})
    print(f"\n    Risk: {risk.get('title', 'N/A')}")
    print(f"    Severity: {risk.get('severity', '?')} (prob: {risk.get('probability', 0):.0%})")
    print(f"    Indicators: {risk.get('indicators', [])}")
    print(f"    Related Standards: {risk.get('related_standards', [])}")

    print(f"\n{'='*65}")
    print(f"  Demo Complete — Financial Analytics → Risk Agent verified")
    print(f"{'='*65}")


if __name__ == "__main__":
    asyncio.run(main())
