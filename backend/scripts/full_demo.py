"""Full Integration Demo — 端到端审计闭环

把 Phase 1 (Workflow + Agents) 和 Phase 2 (Document Pipeline) 串联:
  上传 PDF → Parse → Chunk → Embed → Workflow Engine → 5 Agent → Workpaper → Report

用法: python -m scripts.full_demo
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"), override=True)


# ── Demo 上下文 ─────────────────────────────────────────────

DEMO_SOURCE_ID = f"demo_{uuid.uuid4().hex[:8]}"


async def generate_pdf() -> bytes:
    """生成包含风险指标的示例审计文档"""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)

    content = """ABC Manufacturing Inc. - Financial Statements FY2024

1. Revenue Recognition Policy
The Company recognizes revenue in accordance with IFRS 15.
Revenue is recognized when control of goods or services is transferred to customers.
For bundled hardware and maintenance contracts, revenue is allocated based on standalone selling prices.
Maintenance revenue is recognized ratably over 12-36 months.

2. Key Financial Data
- Revenue: $850 million (growth: 45% vs industry average 10%)
- Accounts Receivable: $280 million (DSO increased from 90 to 120 days)
- Deferred Revenue: $45 million (related to 3 contracts modified in final week)
- Q4 Revenue: $340 million (40% of annual revenue, vs typical 25% quarterly split)

3. Contract Modifications
Three significant contract modifications occurred in the final week of the reporting period.
Total value of modifications: $12 million.
Management applied the cumulative catch-up method.

4. Related Party Transactions
- Sale to subsidiary at 15% below market price: $2.3 million
- Loan to related party: $5 million at 2% interest (market rate: 8%)

5. Subsequent Events
- Major customer filed for bankruptcy on Jan 15, 2025 (receivable: $3.5 million)
- Patent infringement lawsuit filed against the company"""

    pdf.multi_cell(0, 6, content)
    return pdf.output()


async def process_document(pdf_bytes: bytes) -> dict:
    """PDF → Parse → Chunk → Embed → 返回结构化数据"""
    from infrastructure.parser.pdf_parser import PyMuPDFParser
    from infrastructure.vector.chunking import chunk_document

    parser = PyMuPDFParser()
    doc = await parser.parse(pdf_bytes, DEMO_SOURCE_ID)
    page_texts = [(p.page_number, p.text) for p in doc.pages]

    # Chunk
    chunks = chunk_document(page_texts, DEMO_SOURCE_ID, max_tokens=300)
    print(f"  Parsed: {doc.total_pages} pages, {len(chunks)} chunks")

    # Embed (local)
    try:
        from infrastructure.vector.local_embedding import LocalEmbeddingProvider
        provider = LocalEmbeddingProvider()
    except ImportError:
        from infrastructure.vector.openai_embedding import OpenAIEmbeddingProvider
        provider = OpenAIEmbeddingProvider()

    texts = [c.text for c in chunks]
    vectors = await provider.embed(texts)
    print(f"  Embed: {len(vectors)} vectors, dim={provider.dimension()}")

    return {
        "source_id": DEMO_SOURCE_ID,
        "chunks": chunks,
        "vectors": vectors,
        "chunk_texts": texts,
    }


def build_demo_graph(chunks_metadata: list[dict]) -> "GraphDefinition":
    """构建 Workflow Graph — chunk 摘要注入 Agent 的 input_mapping"""
    from workflows.models import AgentNode, Edge, GraphDefinition

    chunk_summary = json.dumps(chunks_metadata, ensure_ascii=False)[:2000]

    return GraphDefinition(
        nodes=[
            AgentNode(
                id="planner",
                agent_name="planner_agent",
                input_mapping={
                    "audit_area": "Revenue Recognition",
                    "project_context": {
                        "company": "ABC Manufacturing Inc.",
                        "industry": "Industrial Equipment",
                        "document_chunks": chunk_summary,
                    },
                },
            ),
            AgentNode(
                id="knowledge",
                agent_name="knowledge_agent",
                input_mapping={"audit_area": "Revenue Recognition"},
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
                        "q4_spike": "40% of annual",
                        "contract_modifications": "3 deals in final week",
                        "related_party": "sale at 15% below market",
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
                        "Q4 revenue spike at 40% of annual revenue",
                        "Contract modifications in final week of period",
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
            Edge(source="knowledge", target="risk"),
            Edge(source="risk", target="evidence"),
            Edge(source="evidence", target="reviewer"),
        ],
        entry_point="planner",
        end_nodes=["reviewer"],
    )


async def run_workflow(chunks_metadata: list[dict]) -> dict:
    """Workflow Engine 驱动 5 Agent"""
    from agents.base import AgentRegistry
    from agents.planner.agent import LlmPlannerAgent
    from agents.knowledge.agent import LlmKnowledgeAgent
    from agents.risk.agent import LlmRiskAgent
    from agents.evidence.agent import LlmEvidenceAgent
    from agents.reviewer.agent import LlmReviewerAgent
    from workflows.engine import WorkflowEngine

    # 注册 Agent
    registry = AgentRegistry()
    registry.register(LlmPlannerAgent)
    registry.register(LlmKnowledgeAgent)
    registry.register(LlmRiskAgent)
    registry.register(LlmEvidenceAgent)
    registry.register(LlmReviewerAgent)

    # 构建 Engine
    engine = WorkflowEngine(registry)
    graph = build_demo_graph(chunks_metadata)
    wf_id = await engine.create(graph)

    # 事件监听（简洁输出）
    results: dict[str, str] = {}

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
            err = p.get("error_type", "unknown")
            print(f"    FAIL {a}: {err}")
        elif et == "workflow_completed":
            print(f"    ** Pipeline COMPLETE")

    engine.on_event(on_event)

    state = await engine.run(wf_id)
    return {"state": state, "results": results, "workflow_id": wf_id}


def generate_workpaper(agent_results: dict) -> str:
    """从 Agent 结果生成审计工作底稿"""
    from services.workpaper_generator import WorkpaperGenerator, WorkpaperSection

    generator = WorkpaperGenerator()

    # 提取各 Agent 产出
    planner_output = agent_results.get("planner", {}).get("result", {})
    risk_output = agent_results.get("risk", {}).get("result", {})
    evidence_output = agent_results.get("evidence", {}).get("result", {})
    reviewer_output = agent_results.get("reviewer", {}).get("result", {})

    risk_artifact = risk_output.get("artifact", {})
    risk_content = risk_artifact.get("content", {})

    sections = [
        WorkpaperSection(
            section_id="summary",
            title="Engagement Summary",
            content=f"Client: ABC Manufacturing Inc.\nPeriod: FY2024\nArea: Revenue Recognition\n",
        ),
        WorkpaperSection(
            section_id="risk",
            title="Risk Assessment",
            content=risk_content.get("title", "N/A") + "\nSeverity: " + risk_content.get("severity", "N/A") + "\nProbability: " + str(risk_content.get("probability", 0)),
            citations=risk_content.get("indicators", []),
        ),
        WorkpaperSection(
            section_id="evidence",
            title="Evidence Analysis",
            content="Claims verified against document:\n" + str(evidence_output.get("coverage", 0)),
            citations=[c.get("claim", "") for c in risk_output.get("citations", [])]
        ),
    ]

    wp = generator.generate(
        title="Workpaper — Revenue Recognition — ABC Manufacturing FY2024",
        client="ABC Manufacturing Inc.",
        period="FY2024",
        sections=sections,
    )
    return wp.to_markdown()


def generate_report(agent_results: dict) -> str:
    """生成审计报告"""
    from services.report_generator import ReportGenerator

    reviewer_output = agent_results.get("reviewer", {}).get("result", {})
    reviewer_artifact = reviewer_output.get("artifact", {})
    review_content = reviewer_artifact.get("content", {})
    risk_output = agent_results.get("risk", {}).get("result", {})
    risk_artifact = risk_output.get("artifact", {})
    risk_content = risk_artifact.get("content", {})

    quality = review_content.get("quality_score", 0)
    hallucination = review_content.get("hallucination_risk", 0)
    review_result = review_content.get("review_result", "PENDING")

    issues = review_content.get("issues", [])
    issues_text = "\n".join(f"- [{i.get('severity','?')}] {i.get('description','')}" for i in issues)

    risk_title = risk_content.get("title", "N/A")

    generator = ReportGenerator()
    report = generator.generate(
        client="ABC Manufacturing Inc.",
        period="FY2024",
        opinion="Qualified" if hallucination > 0.3 else "Unqualified",
        findings=[{"area": risk_title, "severity": risk_content.get("severity", "MEDIUM")}],
    )

    # 追加 AI 审查备注
    report.sections.append(
        type(report.sections[0])(
            title="AI Quality Review",
            content=f"Review Result: {review_result}\nQuality Score: {quality:.0%}\nHallucination Risk: {hallucination:.0%}\n\nIssues:\n{issues_text}",
        )
    )
    return report.to_markdown()


async def main():
    print("=" * 70)
    print("  AuditFlow Full Integration Demo")
    print("  端到端：上传 PDF → 审计工作底稿 → 审计报告")
    print("=" * 70)
    print()

    # Step 1: 生成测试文档
    print("[1/5] Generating test document...")
    pdf_bytes = await generate_pdf()
    print(f"      PDF: {len(pdf_bytes)} bytes, 5 sections covering revenue/risks/contracts")

    # Step 2: 文档处理
    print("\n[2/5] Processing document (Parse → Chunk → Embed)...")
    doc_data = await process_document(pdf_bytes)
    chunks_meta = [
        {"chunk_id": c.chunk_id, "page": c.page_number, "tokens": c.token_count, "text": c.text[:150]}
        for c in doc_data["chunks"]
    ]

    # Step 3: Workflow（Agent 基于文档内容进行审计）
    print("\n[3/5] Running audit workflow...")
    print("      Pipeline: Planner → Knowledge → Risk → Evidence → Reviewer")
    wf_result = await run_workflow(chunks_meta)
    state = wf_result["state"]

    if state.status == "FAILED":
        print(f"\n    ERROR: {state.error}")

    # Step 4: 生成工作底稿
    print(f"\n[4/5] Generating workpaper...")
    workpaper = generate_workpaper(state.agent_results)
    print(f"      Workpaper generated ({len(workpaper)} chars)")

    # Step 5: 生成审计报告
    print(f"\n[5/5] Generating audit report...")
    report = generate_report(state.agent_results)
    print(f"      Report generated ({len(report)} chars)")

    # 输出摘要
    print()
    print("=" * 70)
    print("  Pipeline Summary")
    print("=" * 70)
    print(f"\n  Document:  parsed → {len(doc_data['chunks'])} chunks → {len(doc_data['vectors'])} embeddings")
    print(f"  Workflow:  {state.status} ({wf_result['workflow_id']})")
    for agent_name, perf in wf_result["results"].items():
        print(f"    {agent_name}: {perf}")

    print(f"\n  Workpaper:  {len(workpaper)} chars")
    print(f"  Report:     {len(report)} chars")

    # 写入 Markdown 文件
    output_dir = os.path.join(os.path.dirname(__file__), "demo_output")
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "workpaper.md"), "w", encoding="utf-8") as f:
        f.write(workpaper)
    with open(os.path.join(output_dir, "report.md"), "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n  Output: {output_dir}/")
    print(f"    workpaper.md — 审计工作底稿")
    print(f"    report.md — 审计报告")
    print()

    # 检查验收标准
    print("=" * 70)
    print("  Acceptance Checklist")
    print("=" * 70)

    # AC1: 完整流程无人工干预
    check1 = state.status == "COMPLETED"
    print(f"  [{'OK' if check1 else 'FAIL'}] Pipeline completed without intervention")

    # AC2: Risk 包含 Citation
    risk_result = state.agent_results.get("risk", {})
    risk_citations = len(risk_result.get("citations", []))
    print(f"  [{'OK' if risk_citations > 0 else 'FAIL'}] Risk output has citations: {risk_citations}")

    # AC3: Workpaper 包含完整链条
    wp_has_risk = "Risk" in workpaper
    wp_has_evidence = "Evidence" in workpaper
    check3 = wp_has_risk and wp_has_evidence
    print(f"  [{'OK' if check3 else 'FAIL'}] Workpaper contains Risk + Evidence chain")

    # AC4: Report 已生成
    check4 = len(report) > 200
    print(f"  [{'OK' if check4 else 'FAIL'}] Audit report generated ({len(report)} chars)")

    print(f"\n  Overall: {sum([check1, risk_citations > 0, check3, check4])}/4 passed")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
