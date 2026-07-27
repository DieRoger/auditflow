"""Sprint 1 Demo — 真实 PDF 检索 → Agent → Report

流程:
  1. 从 PGVector 检索 Top-K chunks（针对审计提问）
  2. 将 chunks 注入 Workflow Engine context
  3. Knowledge Agent 基于 chunks 回答（不再凭空生成）
  4. Risk → Evidence → Reviewer → Workpaper → Report
"""

import asyncio
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"), override=True)


async def retrieve_chunks(query: str, top_k: int = 5) -> list[dict]:
    """从 PGVector 检索相关 chunk"""
    from infrastructure.vector.local_embedding import LocalEmbeddingProvider
    from sqlalchemy.ext.asyncio import create_async_engine
    from infrastructure.vector.pgvector_store import PGVectorStore

    provider = LocalEmbeddingProvider()
    vec = await provider.embed([query])

    db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://auditflow:auditflow@localhost:5432/auditflow")
    engine = create_async_engine(db_url)
    chunks = []
    async with engine.connect() as conn:
        store = PGVectorStore(conn)
        results = await store.search(vec[0], top_k=top_k)
        for r in results:
            meta = r.metadata or {}
            chunks.append({
                "page": meta.get("page", "?"),
                "score": meta.get("_score", 0),
                "content": r.content,
                "chunk_id": r.id,
                "document_id": meta.get("source", meta.get("file", "unknown")),
            })
    await engine.dispose()
    return chunks


async def run_workflow_with_chunks(chunks: list[dict]) -> dict:
    """Workflow Engine — chunk 注入 context"""
    from agents.base import AgentRegistry
    from agents.planner.agent import LlmPlannerAgent
    from agents.knowledge.agent import LlmKnowledgeAgent
    from agents.risk.agent import LlmRiskAgent
    from agents.evidence.agent import LlmEvidenceAgent
    from agents.reviewer.agent import LlmReviewerAgent
    from workflows.engine import WorkflowEngine
    from workflows.models import AgentNode, Edge, GraphDefinition

    registry = AgentRegistry()
    registry.register(LlmPlannerAgent)
    registry.register(LlmKnowledgeAgent)
    registry.register(LlmRiskAgent)
    registry.register(LlmEvidenceAgent)
    registry.register(LlmReviewerAgent)

    # 构建 chunk summary 给 planner
    chunk_summary = json.dumps([{"page": c["page"], "preview": c["content"][:100]} for c in chunks], ensure_ascii=False)

    graph = GraphDefinition(
        nodes=[
            AgentNode(id="planner", agent_name="planner_agent", input_mapping={
                "audit_area": "Audit Standards and Requirements",
                "project_context": {"document_chunks": chunk_summary},
            }),
            AgentNode(id="knowledge", agent_name="knowledge_agent", input_mapping={
                "audit_area": "Audit Standards and Requirements",
            }),
            AgentNode(id="risk", agent_name="risk_agent", input_mapping={
                "audit_area": "Audit Standards",
                "financial_data": {},
            }),
            AgentNode(id="evidence", agent_name="evidence_agent", input_mapping={
                "claims_to_verify": ["Auditor responsibilities", "Audit procedures and standards"],
                "financial_data": {},
            }),
            AgentNode(id="reviewer", agent_name="reviewer_agent", input_mapping={}),
        ],
        edges=[
            Edge(source="planner", target="knowledge"),
            Edge(source="knowledge", target="risk"),
            Edge(source="risk", target="evidence"),
            Edge(source="evidence", target="reviewer"),
        ],
        entry_point="planner",
        end_nodes=["reviewer"],
    )

    engine = WorkflowEngine(registry)
    wf_id = await engine.create(graph)

    # 将 chunks 注入初始 context（平铺到 agent_results 顶层）
    state = engine.get_state(wf_id)
    state.agent_results["document_chunks"] = chunks

    results = {}
    async def on_event(event):
        p = event.payload
        a = p.get("agent_name", "")
        et = event.event_type.value
        if et == "agent_started":
            print(f"    >> {a}...")
        elif et == "agent_completed":
            tok = p.get("tokens", 0)
            dur = p.get("duration_ms", 0)
            conf = p.get("confidence", 0)
            print(f"    OK {a} ({dur}ms, tok={tok}, conf={conf:.0%})")
            results[a] = f"{dur}ms/{tok}tok/{conf:.0%}"
        elif et == "agent_failed":
            print(f"    FAIL {a}: {p.get('error_type', 'unknown')}")
        elif et == "workflow_completed":
            print(f"    ** Pipeline COMPLETE")

    engine.on_event(on_event)
    state = await engine.run(wf_id)
    return {"state": state, "results": results, "workflow_id": wf_id}


async def main():
    print("=" * 70)
    print("  Sprint 1: Real PDF → Retrieval → Agent → Report")
    print("=" * 70)

    # 1. 检索
    query = "审计师的责任和审计准则要求"
    print(f"\n[1/4] Retrieving chunks for: \"{query}\"")
    chunks = await retrieve_chunks(query, top_k=5)
    print(f"      Found {len(chunks)} chunks")
    for i, c in enumerate(chunks, 1):
        print(f"      [{i}] page={c['page']}  score={c['score']:.4f}")

    # 2. Workflow
    print(f"\n[2/4] Running audit workflow with {len(chunks)} context chunks...")
    print(f"      Pipeline: Planner → Knowledge → Risk → Evidence → Reviewer")
    wf = await run_workflow_with_chunks(chunks)
    state = wf["state"]

    if state.status == "FAILED":
        print(f"\n      ERROR: {state.error}")

    # 检查 Risk Agent 的 Citation 是否真实
    risk_result = state.agent_results.get("risk", {})
    risk_citations = risk_result.get("citations", [])
    print(f"\n      Risk citations: {len(risk_citations)}")
    for i, c in enumerate(risk_citations):
        doc = c.get("document_id", "?")
        page = c.get("page", "?")
        cid = c.get("chunk_id", "?")
        conf = c.get("confidence", 0)
        print(f"        [{i}] doc={doc} page={page} chunk={cid} conf={conf:.2f}")

    # 3. Workpaper
    print(f"\n[3/4] Generating workpaper...")
    from services.workpaper_generator import WorkpaperGenerator, WorkpaperSection
    risk_result = state.agent_results.get("risk", {}).get("result", {})
    risk_content = risk_result.get("artifact", {}).get("content", {})
    generator = WorkpaperGenerator()
    wp = generator.generate(
        title="Sprint 1 — Audit Standard Analysis",
        client="AuditFlow Demo",
        period="2024",
        sections=[
            WorkpaperSection(section_id="summary", title="Summary", content=f"Analysis based on {len(chunks)} document chunks"),
            WorkpaperSection(section_id="findings", title="Key Findings", content=risk_content.get("title", "N/A")),
        ],
    )
    wp_md = wp.to_markdown()

    # 4. Report
    print(f"[4/4] Generating report...")
    from services.report_generator import ReportGenerator
    report = ReportGenerator().generate(client="AuditFlow Demo", period="2024")
    report_md = report.to_markdown()

    # 输出
    output_dir = os.path.join(os.path.dirname(__file__), "sprint1_output")
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "workpaper.md"), "w", encoding="utf-8") as f:
        f.write(wp_md)
    with open(os.path.join(output_dir, "report.md"), "w", encoding="utf-8") as f:
        f.write(report_md)

    # 摘要
    print(f"\n{'='*70}")
    print(f"  Summary")
    print(f"{'='*70}")
    print(f"  Chunks retrieved: {len(chunks)} from PGVector")
    print(f"  Workflow: {state.status} ({wf['workflow_id']})")
    for name, perf in wf["results"].items():
        print(f"    {name}: {perf}")
    print(f"  Output: {output_dir}/")
    print(f"  Overall: {'PASS' if state.status == 'COMPLETED' else 'FAIL'}")
    print(f"{'='*70}")


if __name__ == "__main__":
    asyncio.run(main())
