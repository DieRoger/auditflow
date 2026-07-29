"""Revenue Cutoff Demo v2 — Phase B Procedure Engine

展示: Excel Import → Risk → AuditProgram → Sampling → Procedure → Findings → Working Paper

用法: python -m scripts.revenue_cutoff_demo
"""

import asyncio
import os
import sys
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"), override=True)


def generate_sample_excel() -> str:
    """Revenue Cutoff 测试 Excel — 24笔正常 + 5笔异常"""
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = "Sales Detail"
    ws.append(["销售日期", "客户名称", "销售金额", "发票号", "发货日期"])
    for d in range(1, 25):
        ws.append([f"2025-12-{d:02d}", f"Customer_{d}", 10000 + d*500, f"INV-2025-{d:03d}", f"2025-12-{d:02d}"])
    # Cutoff issues
    ws.append(["2025-12-31", "ABC Corp",     50000, "INV-101", "2026-01-02"])
    ws.append(["2025-12-31", "XYZ Ltd",      35000, "INV-102", "2026-01-03"])
    ws.append(["2025-12-30", "Global Inc",   42000, "INV-103", "2026-01-05"])
    ws.append(["2025-12-31", "Local Trading",15000, "INV-104", "2025-12-31"])
    ws.append(["2025-12-29", "Mega Co",      88000, "INV-105", "2026-01-01"])
    path = Path(__file__).parent / "sample_sales.xlsx"
    wb.save(str(path))
    return str(path)


async def run_demo():
    print("=" * 65)
    print("  AuditFlow — Revenue Cutoff Demo v2 (Phase B)")
    print("=" * 65)

    # 1. Generate + Import
    print("\n[1] Excel Import → Canonical Schema")
    excel_path = generate_sample_excel()
    from infrastructure.excel.excel_adapter import ExcelAdapter
    adapter = ExcelAdapter()
    session, records = adapter.parse(excel_path)
    records, valid_count = adapter.validate(records)
    transactions, parties = adapter.generate_transactions(records)
    print(f"    {session.row_count} rows → {valid_count} valid → {len(transactions)} txns")

    # Build enriched records (add computed fields for procedure)
    enriched = []
    for rec in records:
        if rec.status != rec.status.__class__.VALID:
            continue
        raw = rec.raw_data
        ship_val = adapter._find_value(raw, adapter._mapping.mappings.get("shipping_date", {}).get("aliases", []))
        try:
            sd = adapter._parse_date(str(ship_val)) if ship_val else None
        except ValueError:
            sd = None
        txn_val = adapter._find_value(raw, adapter._mapping.mappings.get("transaction_date", {}).get("aliases", []))
        try:
            td = adapter._parse_date(str(txn_val)) if txn_val else None
        except ValueError:
            td = None
        enriched.append({
            "canonical_refs": rec.canonical_refs or {},
            "_ship_date": sd,
            "_txn_date": td,
            "_amount": adapter._find_value(raw, adapter._mapping.mappings.get("amount", {}).get("aliases", [])),
        })

    # 2. Risk
    print("\n[2] Risk Assessment")
    from agents.risk.agent import LlmRiskAgent
    from domain.contracts import AgentRequest
    agent = LlmRiskAgent()
    resp = await agent.execute(AgentRequest(
        workflow_id="demo", project_id="demo", task_id="risk",
        firm_id="demo", client_id="demo", engagement_id="demo",
        inputs={"audit_area": "Revenue Cutoff", "financial_data": {
            "total_transactions": len(transactions), "period": "FY2025"}},
    ))
    risk = resp.result.get("artifact", {}).get("content", {})
    print(f"    {risk.get('severity','?')}: {risk.get('title','N/A')}")

    # 3. AuditProgram
    print("\n[3] Audit Program → Sampling → Execute")
    from application.audit.sampling import CutoffProcedureExecutor, generate_cutoff_program
    from domain.audit.entities.procedure import SamplingConfig, SamplingMethod

    program = generate_cutoff_program()
    proc = program.procedures[0]
    proc.sampling.population_size = len(transactions)
    print(f"    Program: {proc.name} ({proc.procedure_type.value})")
    print(f"    Assertions: {[a.value for a in proc.assertions]}")
    print(f"    Objective: {proc.objective}")

    # 4. Execute
    executor = CutoffProcedureExecutor()
    findings = executor.execute(proc, transactions, enriched, date(2025, 12, 31))
    print(f"    Sample: {len(transactions)} items")
    print(f"    Findings: {len(findings)}")

    for f in findings:
        print(f"    [{f.severity.value}] {f.description}")
        if f.amount:
            print(f"       Amount: ${f.amount} | Txn: {f.transaction_ref[:12]}")

    # 5. Working Paper
    print(f"\n[5] Working Paper")
    print(f"    {'='*55}")
    print(f"    Revenue Cutoff — Audit Working Paper")
    print(f"    {'='*55}")
    print(f"    Period: FY2025 | Cutoff: 2025-12-31")
    print(f"    Assertions: Occurrence, Cutoff")
    print(f"    Procedure: {proc.objective}")
    print(f"    Sample: {len(transactions)} transactions")
    print(f"    Exceptions: {len(findings)}")
    if findings:
        print(f"\n    Issues:")
        for i, f in enumerate(findings, 1):
            print(f"      [{i}] {f.description}")
    print(f"    {'='*55}")

    # Summary
    print(f"\n{'='*65}")
    print(f"  Demo Complete")
    print(f"  {'='*65}")
    print(f"  Risk: {risk.get('severity')} — {risk.get('title')}")
    print(f"  Program: {program.summary()}")
    print(f"  Exception Rate: {len(findings)}/{len(transactions)} ({len(findings)/len(transactions)*100:.1f}%)")
    print(f"  {'='*65}")

    os.remove(excel_path)


if __name__ == "__main__":
    asyncio.run(run_demo())
