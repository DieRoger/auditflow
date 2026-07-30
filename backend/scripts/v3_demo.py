"""Journal Entry Testing Demo + Materiality Engine"""

import asyncio, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"), override=True)

from datetime import date, timedelta
from decimal import Decimal
from domain.finance.services.journal_testing import JournalEntry, JournalAnomalyDetector


def generate_entries() -> list[JournalEntry]:
    """生成模拟日记账 — 包含异常"""
    entries = []
    base = date(2025, 12, 1)
    for i in range(100):
        entries.append(JournalEntry(
            journal_no=f"GL-2025-{i:04d}",
            description=f"Normal expense entry {i}",
            amount=Decimal(f"{100 + i * 7}"),
            posting_date=base + timedelta(days=i % 25),
            created_by="AP_User",
            is_manual=False,
        ))
    # 周末分录
    entries.append(JournalEntry(
        journal_no="GL-2025-101", description="Adjustment revenue", amount=Decimal("500000"),
        posting_date=date(2025, 12, 13), created_by="FIN_MGR", is_manual=True  # Saturday
    ))
    # 整数金额（常见造假金额）
    entries.append(JournalEntry(
        journal_no="GL-2025-102", description="Year-end accrual adjustment", amount=Decimal("100000"),
        posting_date=date(2025, 12, 31), created_by="FIN_MGR", is_manual=True
    ))
    # 重复摘要
    for i in range(5):
        entries.append(JournalEntry(
            journal_no=f"GL-2025-{201+i:04d}", description="Adj per management discussion",
            amount=Decimal("50000"), posting_date=date(2025, 12, 30),
            created_by="FIN_MGR", is_manual=True,
        ))
    # 手工大额
    entries.append(JournalEntry(
        journal_no="GL-2025-301", description="Manual adjustment per CFO instruction",
        amount=Decimal("200000"), posting_date=date(2025, 12, 28),
        created_by="CFO", is_manual=True,
    ))
    return entries


async def main():
    print("=" * 65)
    print("  V3 Capabilities — Journal Testing + Materiality")
    print("=" * 65)

    # ── 1. Journal Entry Testing ──
    print("\n[1] Journal Entry Testing")
    entries = generate_entries()
    detector = JournalAnomalyDetector()
    anomalies = detector.detect(entries)
    summary = detector.summary(anomalies)
    print(f"    Total entries scanned: {len(entries)}")
    print(f"    Anomalies detected:    {summary['total']} ({summary['high_risk']} HIGH)")
    for a in summary["details"]:
        if a["severity"] == "HIGH":
            print(f"    [HIGH] {a['type']}: {a['detail'][:80]}")

    # ── 2. Materiality Engine ──
    print("\n[2] Materiality Engine")
    from application.audit.materiality import MaterialityEngine

    financials = {
        "profit_before_tax": 85_000_000,
        "revenue": 850_000_000,
        "total_assets": 1_200_000_000,
        "equity": 420_000_000,
    }
    mater = MaterialityEngine()
    mat_result = mater.calculate(financials, audit_risk="HIGH")
    print(f"    Overall Materiality:   ${mat_result.overall:>10,.0f}")
    print(f"    Performance:           ${mat_result.performance:>10,.0f}")
    print(f"    Trivial Threshold:     ${mat_result.trivial:>10,.0f}")
    print(f"    Base: {mat_result.base} at {mat_result.base_pct:.1f}%")

    print(f"\n{'='*65}")
    print(f"  V3 Demo Complete")
    print(f"{'='*65}")


if __name__ == "__main__":
    asyncio.run(main())
