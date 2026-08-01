# Phase 1: Anomaly Detection Benchmark KPI

**Target version:** v0.5.0
**Dataset:** Kaggle #1 (7,000 rows, 955 labeled anomalies)
**Architecture:** DetectionFacade → RiskScoringEngine (12 Signals, 3 RiskProfiles)

---

## KPI Targets

| Metric | Target | Current (2026-07-30) | Gap |
|--------|--------|---------------------|-----|
| Precision | > 50% | 14.5% | -35.5pp |
| Recall | > 80% | 99.8% | ✅ |
| F1 | > 60% | 25.4% | -34.6pp |
| Benchmark Runtime | < 30s | ~2s | ✅ |
| Reproducibility | 100% | ✅ (fixed seed) | ✅ |
| Random Seed | Fixed (42) | ✅ | ✅ |

---

## Recovery Strategy

1. **Signal Audit** — Rank signals by precision on labeled data:
   - Precision < 20% → REMOVE or demote to INFO
   - Precision 20-50% → demote to INFO (keep for explanation)
   - Precision > 50% → keep as SCORE signal

2. **High-FP signals identified** (2026-07-30 benchmark):
   - `audit_violation`: 19,593 triggers / 7,000 rows (280% trigger rate) — REMOVE
   - `province_mismatch`: 19,281 triggers — REMOVE
   - `night`: 6,366 triggers — INFO only
   - `weekend`: 5,976 triggers — INFO only
   - `temporal_burst`: 3,978 triggers — INFO only

3. **Keepers** (high precision signals):
   - `round_number`: 100% precision
   - `related_party`: 95.6%
   - `amount_spike`: 68.3%
   - `duplicate_invoice`: ~92%
   - `tax_mismatch`: moderate

4. **Profile weight adjustment** — after removing high-FP signals, re-calibrate
   RevenueFraud / PurchaseFraud / ExpenseFraud threshold values.

---

## Verification

```bash
# Run benchmark (must be 100% reproducible)
py -3.11 -m domain.finance.anomaly.evaluation.benchmark

# Expected output: benchmark_{date}.json with F1 >= 60%
# Verify: same seed → same numbers, every run
```

## Gate

- [ ] F1 ≥ 60% on Kaggle #1
- [ ] Report saved to `benchmark/` directory
- [ ] Per-signal precision table included
