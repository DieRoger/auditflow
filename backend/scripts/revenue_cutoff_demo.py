"""Revenue Cutoff Demo — Phase A MVP Vertical Slice

展示: Excel Import → Canonical Schema → Risk → Procedure → Finding

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


def generate_sample_excel():
    """生成 Revenue Cutoff 测试 Excel"""
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sales Detail"

    # Header
    ws.append(["销售日期", "客户名称", "销售金额", "发票号", "发货日期"])

    # Sample data (15 rows)
    # Normal: 8 transactions
    for d in range(1, 25):
        ws.append([f"2025-12-{d:02d}", f"Customer_{d}", 10000 + d * 500, f"INV-2025-{d:03d}", f"2025-12-{d:02d}"])

    # Revenue cutoff issues: shipped after period (should be Q1 2026 revenue)
    ws.append(["2025-12-31", "ABC Corp",      50000, "INV-2025-101", "2026-01-02"])  # ← Cutoff issue
    ws.append(["2025-12-31", "XYZ Ltd",       35000, "INV-2025-102", "2026-01-03"])  # ← Cutoff issue
    ws.append(["2025-12-30", "Global Inc",    42000, "INV-2025-103", "2026-01-05"])  # ← Cutoff issue
    ws.append(["2025-12-31", "Local Trading", 15000, "INV-2025-104", "2025-12-31"])  # OK
    ws.append(["2025-12-29", "Mega Co",       88000, "INV-2025-105", "2025-12-31"])  # OK (shipped within period)

    path = Path(__file__).parent / "sample_sales.xlsx"
    wb.save(str(path))
    return str(path)


def cutoff_check(transactions: list, cutoff_date: date = date(2025, 12, 31)):
    """Revenue Cutoff 程序: 检查交易日期 vs 发货日期"""
    findings = []
    for txn in transactions:
        # 发货日期从 Document 关联中查找
        shipping_date = None
        ps = getattr(txn, "document_refs", [])
        # （简化：如果有 Delivery Document 引用且日期 > cutoff，标记异常）
        if hasattr(txn, "_delivery_date") and txn._delivery_date:
            shipping_date = txn._delivery_date

        if shipping_date and shipping_date > cutoff_date:
            findings.append({
                "transaction_id": txn.transaction_id,
                "transaction_date": txn.transaction_date.isoformat(),
                "amount": str(txn.amount),
                "shipping_date": shipping_date.isoformat(),
                "issue": "Revenue recognized before shipment — should be Q1 2026 revenue",
                "severity": "HIGH",
            })

    return findings


async def run_demo():
    print("=" * 65)
    print("  AuditFlow — Revenue Cutoff Audit Demo (Phase A MVP)")
    print("=" * 65)

    # ── Step 1: Generate test data ──
    print("\n[1] Generating sample Excel...")
    excel_path = generate_sample_excel()
    print(f"    Created: {excel_path}")

    # ── Step 2: Import Excel → Canonical Schema ──
    print("\n[2] Importing Excel → Canonical Schema...")
    from infrastructure.excel.excel_adapter import ExcelAdapter
    adapter = ExcelAdapter()
    session, records = adapter.parse(excel_path)
    records, valid_count = adapter.validate(records)
    transactions, parties = adapter.generate_transactions(records)

    print(f"    ImportSession: {session.session_id}")
    print(f"    Rows: {session.row_count} total, {valid_count} valid")
    print(f"    Transactions: {len(transactions)}, Parties: {len(parties)}")

    # ── Step 3: Risk Analysis via Risk Agent ──
    print("\n[3] Running Risk Agent...")
    from agents.risk.agent import LlmRiskAgent
    from domain.contracts import AgentRequest

    monthly_revenue = {}
    for txn in transactions:
        period = txn.transaction_date.strftime("%Y-%m")
        monthly_revenue[period] = monthly_revenue.get(period, Decimal("0")) + txn.amount

    dec_revenue = float(monthly_revenue.get("2025-12", Decimal("0")))
    total_revenue = float(sum(monthly_revenue.values()))
    dec_pct = round(dec_revenue / total_revenue * 100, 1) if total_revenue else 0

    agent = LlmRiskAgent()
    resp = await agent.execute(AgentRequest(
        workflow_id="cutoff_demo", project_id="demo", task_id="risk",
        firm_id="demo", client_id="demo", engagement_id="demo",
        inputs={
            "audit_area": "Revenue Recognition — Cutoff",
            "financial_data": {
                "december_revenue": f"${dec_revenue:,.0f}",
                "december_pct_of_year": f"{dec_pct}%",
                "total_transactions": len(transactions),
                "period": "FY2025",
            },
        },
    ))
    risk = resp.result.get("artifact", {}).get("content", {})
    print(f"    Risk: {risk.get('title', 'N/A')}")
    print(f"    Severity: {risk.get('severity', '?')} (prob: {risk.get('probability', 0):.0%})")
    print(f"    Indicators: {risk.get('indicators', [])}")

    # ── Step 4: Revenue Cutoff Procedure ──
    print("\n[4] Executing Revenue Cutoff Procedure...")
    findings = []
    cutoff_date = date(2025, 12, 31)

    for rec in records:
        if rec.status != rec.status.__class__.VALID:
            continue
        raw = rec.raw_data

        # 获取发货日期
        ship_val = adapter._find_value(raw, adapter._mapping.mappings.get("shipping_date", {}).get("aliases", []))
        if not ship_val:
            continue

        try:
            from infrastructure.excel.excel_adapter import ExcelAdapter
            ship_date = ExcelAdapter._parse_date(str(ship_val))
        except ValueError:
            continue

        txn_date_str = adapter._find_value(raw, adapter._mapping.mappings.get("transaction_date", {}).get("aliases", []))
        txn_date = ExcelAdapter._parse_date(str(txn_date_str)) if txn_date_str else None

        if ship_date > cutoff_date and txn_date and txn_date <= cutoff_date:
            amt = adapter._find_value(raw, adapter._mapping.mappings.get("amount", {}).get("aliases", [])) or "0"
            party = adapter._find_value(raw, adapter._mapping.mappings.get("party_name", {}).get("aliases", [])) or "Unknown"
            refs = rec.canonical_refs or {}
            findings.append({
                "transaction_id": refs.get("id", "N/A"),
                "transaction_date": str(txn_date),
                "amount": amt,
                "party": party,
                "shipping_date": str(ship_date),
                "issue": f"Revenue recognized {txn_date} but shipped {ship_date} — should be Q1 2026 revenue",
            })

    print(f"    Sample: {len(records)} transactions")
    print(f"    Exceptions: {len(findings)}")

    for f in findings:
        print(f"    EXCEPTION: {f['transaction_id']}")
        print(f"       {f['party']} | Date: {f['transaction_date']} | Ship: {f['shipping_date']} | Amount: ${f['amount']}")
        print(f"       {f['issue']}")

    # ── Step 5: Working Paper Summary ──
    print("\n[5] Generating Working Paper...")
    print(f"    {'='*60}")
    print(f"    Revenue Cutoff — Audit Working Paper")
    print(f"    {'='*60}")
    print(f"    Period: FY2025 | Cutoff Date: 2025-12-31")
    print(f"    Sample: {len(transactions)} items selected")
    print(f"    Exceptions: {len(findings)} identified")
    if findings:
        print(f"\n    Exception Details:")
        for i, f in enumerate(findings, 1):
            print(f"      [{i}] {f['transaction_id']}: ${f['amount']} recognized {f['transaction_date']}")
            print(f"          Shipped: {f['shipping_date']} — {f['issue']}")
    print(f"    {'='*60}")

    # ── Summary ──
    print(f"\n{'='*65}")
    print(f"  Demo Complete — Vertical Slice Verified")
    print(f"  {'='*65}")
    print(f"  Excel → Canonical Schema:  {len(transactions)} txns, {len(parties)} parties")
    print(f"  Risk Assessment:          {risk.get('severity', '?')} — {risk.get('title', 'N/A')}")
    print(f"  Cutoff Exceptions:        {len(findings)} found")
    print(f"  {'='*65}")

    # Cleanup
    os.remove(excel_path)
    os.remove(excel_path.replace(".xlsx", ".xlsx")) if False else None  # no-op


if __name__ == "__main__":
    asyncio.run(run_demo())
