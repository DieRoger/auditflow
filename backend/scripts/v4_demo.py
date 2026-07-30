"""V4 Demo — Multi-period Analysis + Confirmation Manager"""

import asyncio, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"), override=True)

from decimal import Decimal
from domain.finance.services.multi_period import MultiPeriodAnalyzer
from domain.audit.entities.confirmation import (
    ConfirmationManager, ConfirmationRegister, ConfirmationStatus,
)


async def main():
    print("=" * 65)
    print("  V4 Demo — Multi-period + Confirmation Manager")
    print("=" * 65)

    # ── 1. Multi-period Analysis ──
    print("\n[1] Multi-period Analysis")
    periods = {
        "2022": {"revenue": 500_000_000, "net_income": 42_000_000, "total_assets": 800_000_000,
                 "receivables": 120_000_000, "inventory": 60_000_000, "current_liabilities": 250_000_000,
                 "cash": 80_000_000, "cogs": 320_000_000},
        "2023": {"revenue": 620_000_000, "net_income": 55_000_000, "total_assets": 950_000_000,
                 "receivables": 180_000_000, "inventory": 85_000_000, "current_liabilities": 320_000_000,
                 "cash": 65_000_000, "cogs": 400_000_000},
        "2024": {"revenue": 750_000_000, "net_income": 72_000_000, "total_assets": 1_050_000_000,
                 "receivables": 230_000_000, "inventory": 100_000_000, "current_liabilities": 380_000_000,
                 "cash": 50_000_000, "cogs": 490_000_000},
        "2025": {"revenue": 850_000_000, "net_income": 85_000_000, "total_assets": 1_200_000_000,
                 "receivables": 280_000_000, "inventory": 120_000_000, "current_liabilities": 475_000_000,
                 "cash": 30_000_000, "cogs": 570_000_000},
    }

    analyzer = MultiPeriodAnalyzer()
    result = analyzer.analyze(periods)

    for t in result.trends:
        val_str = " → ".join(f"${v/1_000_000:.0f}M" for v in t.values)
        chg_str = "; ".join(f"{c:+.1%}" for c in t.changes)
        flag = " !!" if t.pattern in ("reversal", "volatile", "declining") else ""
        print(f"    {t.metric:<20} {val_str}  ({chg_str}) [{t.pattern}]{flag}")

    if result.red_flags:
        print(f"\n    Red Flags ({len(result.red_flags)}):")
        for f in result.red_flags:
            print(f"      [WARN] {f[:90]}")

    # ── 2. Confirmation Manager ──
    print("\n[2] Confirmation Manager")
    register = ConfirmationRegister(engagement_id="ENG-2025-001")
    manager = ConfirmationManager()

    ar_data = [
        {"customer_name": "Customer A", "balance": 500000},
        {"customer_name": "Customer B", "balance": 350000},
        {"customer_name": "Customer C", "balance": 280000},
        {"customer_name": "Customer D", "balance": 150000},
        {"customer_name": "Customer E", "balance": 120000},
    ]
    register = manager.generate_ar_confirmations(register, ar_data)
    # Simulate responses
    for i, req in enumerate(register.requests):
        if i == 0:
            manager.record_response(req.request_id, Decimal("498000"), ConfirmationStatus.DIFFERENCE)
        elif i == 1:
            manager.record_response(req.request_id, Decimal("350000"), ConfirmationStatus.AGREED)
        elif i == 3:
            req.status = ConfirmationStatus.NO_REPLY
            req.alternative_procedure_note = "Verified via subsequent payment received Jan 2026"
            req.status = ConfirmationStatus.ALTERNATIVE
        else:
            manager.record_response(req.request_id, req.amount_confirmed, ConfirmationStatus.AGREED)

    s = register.summary()
    print(f"    Total confirmations: {s['total']}")
    print(f"    Sent:               {s['sent']}")
    print(f"    Received (agreed):  {s['received']}")
    print(f"    Differences:        {s['differences']}")
    print(f"    Coverage:           {s['coverage']}%")

    for req in register.requests:
        status_icon = {ConfirmationStatus.AGREED: "OK", ConfirmationStatus.DIFFERENCE: "DIF",
                       ConfirmationStatus.ALTERNATIVE: "ALT"}.get(req.status, "PEN")
        amt = f"${req.amount_confirmed:,}"
        resp = f" → ${req.response_amount:,}" if req.response_amount else ""
        diff = f" (diff: ${abs(req.difference):,})" if req.difference else ""
        print(f"    [{status_icon}] {req.party_name:<20} {amt}{resp}{diff}")

    print(f"\n{'='*65}")
    print(f"  V4 Demo Complete")
    print(f"{'='*65}")


if __name__ == "__main__":
    asyncio.run(main())
