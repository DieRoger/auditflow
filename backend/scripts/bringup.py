"""System Bring-up — Workflow Engine 驱动 5 Agent 端到端审计管线

用法: python -m scripts.bringup

与 demo_v0.py 的区别:
  - Agent 通过 AgentRegistry 注册和查找（不直接 new）
  - 上下文通过 WorkflowState 流转（不手动 ctx["key"]）
  - Event + Trace 自动记录
"""

import asyncio
import json
import sys
import os

# 确保 backend/src 在 path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# 加载 .env（从项目根目录 auditflow/.env）
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"), override=True)

from agents.base import AgentRegistry
from agents.planner.agent import LlmPlannerAgent
from agents.knowledge.agent import LlmKnowledgeAgent
from agents.anomaly_detection.agent import AnomalyDetectionAgent
from agents.risk.agent import LlmRiskAgent
from agents.evidence.agent import LlmEvidenceAgent
from agents.reviewer.agent import LlmReviewerAgent
from workflows.engine import WorkflowEngine
from workflows.models import AgentNode, Edge, GraphDefinition


def build_graph() -> GraphDefinition:
    """定义 5 Agent 线性审计管线

    Planner → Knowledge → AnomalyDetection → Risk → Evidence → Reviewer
    (AnomalyDetection 的 Finding 作为 Risk Agent 的 ISA 240/315 输入)
    """
    return GraphDefinition(
        nodes=[
            AgentNode(
                id="planner",
                agent_name="planner_agent",
                input_mapping={
                    "audit_area": "Revenue Recognition",
                    "project_context": {"company": "ABC Manufacturing Inc.", "industry": "Industrial Equipment"},
                },
            ),
            AgentNode(
                id="knowledge",
                agent_name="knowledge_agent",
                input_mapping={"audit_area": "Revenue Recognition"},
            ),
            AgentNode(
                id="anomaly_detection",
                agent_name="anomaly_detection_agent",
                input_mapping={"transactions": []},  # 由外部注入实际交易数据
            ),
            AgentNode(
                id="risk",
                agent_name="risk_agent",
                input_mapping={
                    "audit_area": "Revenue Recognition",
                    "financial_data": {
                        "revenue_growth": "45%",
                        "industry_avg": "10%",
                        "receivable_days": 120,
                        "revenue": "$850M",
                    },
                },
            ),
            AgentNode(
                id="evidence",
                agent_name="evidence_agent",
                input_mapping={
                    "claims_to_verify": [
                        "Revenue growth 45% exceeds industry average 10%",
                        "Accounts receivable days increased to 120",
                    ],
                    "financial_data": {},
                },
            ),
            AgentNode(
                id="reviewer",
                agent_name="reviewer_agent",
                input_mapping={},
            ),
        ],
        edges=[
            Edge(source="planner", target="knowledge"),
            Edge(source="knowledge", target="anomaly_detection"),
            Edge(source="anomaly_detection", target="risk"),
            Edge(source="risk", target="evidence"),
            Edge(source="evidence", target="reviewer"),
        ],
        entry_point="planner",
        end_nodes=["reviewer"],
    )


async def main():
    print("=" * 70)
    print("  AuditFlow System Bring-up — Workflow Engine 驱动 5 Agent")
    print("=" * 70)

    # 1. 注册 Agent
    registry = AgentRegistry()
    registry.register(LlmPlannerAgent)
    registry.register(LlmKnowledgeAgent)
    registry.register(AnomalyDetectionAgent)
    registry.register(LlmRiskAgent)
    registry.register(LlmEvidenceAgent)
    registry.register(LlmReviewerAgent)
    print(f"\n[Registry] 已注册 {len(registry.list_agents())} 个 Agent: {registry.list_agents()}")

    # 2. 构建 Workflow
    engine = WorkflowEngine(registry)
    graph = build_graph()
    wf_id = await engine.create(graph)
    print(f"[Workflow] 已创建: {wf_id}")

    # 3. 注册事件监听（实时输出）
    async def on_event(event):
        payload = event.payload
        agent = payload.get("agent_name", "")
        et = event.event_type.value
        if et == "agent_started":
            print(f"  >> {agent}: START")
        elif et == "agent_completed":
            print(f"  OK {agent}: DONE ({payload.get('duration_ms', 0)}ms, {payload.get('tokens', 0)} tokens, confidence={payload.get('confidence', 0):.0%})")
        elif et == "agent_failed":
            print(f"  FAIL {agent}: ERROR ({payload.get('error_type', 'unknown')})")
        elif et == "workflow_completed":
            print(f"\n  ** Workflow COMPLETED!")

    engine.on_event(on_event)

    # 4. 执行
    print("\n[Pipeline] Planner → Knowledge → Risk → Evidence → Reviewer\n")
    state = await engine.run(wf_id)

    # 5. 输出结果
    print("\n" + "=" * 70)
    print("  结果摘要")
    print("=" * 70)

    for node_id, result in state.agent_results.items():
        artifact = result.get("artifact", {})
        content = artifact.get("content", {})
        atype = artifact.get("artifact_type", "unknown")

        print(f"\n--- {node_id} ({atype}) ---")
        if atype == "audit_plan":
            plan = result.get("plan", [])
            print(f"  审计步骤: {len(plan)} 个")
            for p in plan:
                print(f"    Step {p.get('step', '?')}: {p.get('agent', '?')} → {p.get('task', '?')}")
        elif atype == "risk_finding":
            print(f"  风险: {content.get('title', 'N/A')}")
            print(f"  严重性: {content.get('severity', 'N/A')}")
            print(f"  概率: {content.get('probability', 0):.0%}")
            print(f"  相关准则: {content.get('related_standards', [])}")
        elif atype == "evidence_package":
            print(f"  覆盖率: {result.get('coverage', 0):.0%}")
            claims = content.get("claims", [])
            for c in claims:
                status = "[OK]" if c.get("matched") else "[MISS]"
                print(f"  {status} {c.get('claim', 'N/A')[:60]}")
        elif atype == "review_report":
            print(f"  审查结论: {content.get('review_result', 'N/A')}")
            print(f"  质量分: {content.get('quality_score', 0):.0%}")
            print(f"  幻觉风险: {content.get('hallucination_risk', 0):.0%}")
            for issue in content.get("issues", []):
                print(f"  WARN [{issue.get('severity', '?')}] {issue.get('description', '?')}")
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False)[:300])

    # 6. Trace 摘要
    traces = await engine.get_traces(wf_id)
    print(f"\n[Trace] 共 {len(traces)} 条执行记录")
    for t in traces:
        print(f"  [{t.event_type}] {t.agent_name} (step {t.step})" + (f" — error: {t.error}" if t.error else f" — {t.duration_ms}ms"))

    print(f"\n[Workflow] 状态: {state.status}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
