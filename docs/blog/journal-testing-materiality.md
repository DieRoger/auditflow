---
title: "Detecting Audit Anomalies at Scale — Journal Entry Testing and Materiality Estimation"
description: "How AuditFlow detects journal entry anomalies (weekend posting, round numbers, duplicates) and calculates ISA 320 materiality thresholds — replacing auditor intuition with deterministic rules."
date: "2026-07-30"
tags:
  - AI
  - Engineering
  - Audit
  - Evidence
  - Anomaly Detection
categories:
  - Build Log
  - Engineering Decisions
slug: journal-testing-materiality
draft: false
author: Luo Runjie
readingTime: 12
difficulty: Advanced
---

## Background

By the end of V2, AuditFlow could analyze financial statements, execute cutoff procedures, evaluate evidence sufficiency, and calculate misstatements. But two gaps remained.

First, **journal entry testing**. In a real audit, the general ledger is often the first place auditors look for fraud. Manual journal entries, weekend postings, round-number amounts, and duplicate descriptions are classic red flags. Every audit firm has their own version of this analysis, but it's almost always done with Excel macros that are fragile, undocumented, and non-reproducible.

Second, **materiality**. The ISA 320 materiality calculation was being done by the PlanningEngine, but only for a single base (total assets). Real audit requires multiple bases (profit, revenue, assets, equity), three tiers (overall, performance, trivial), and risk-adjusted percentages.

V3 built both of these as standalone engines that feed into the existing Risk Agent and Misstatement Engine.

---

## Journal Entry Testing

### The Six Anomaly Patterns

The `JournalAnomalyDetector` implements six detection rules, all deterministic:

| Pattern | Detection Logic | Typical Risk |
|---------|----------------|-------------|
| **Weekend Posting** | Journal entry on Saturday or Sunday | Fraud (avoids normal review) |
| **Night Posting** | Entry timestamp between 10 PM and 6 AM (planned) | Unauthorized entries |
| **Round Number** | Amount divisible by 1,000; flagged if ≥ $50K | Earnings management |
| **Duplicate Description** | Same text appears ≥ 3 times | Systematic manipulation |
| **Manual Entry** | Non-system entry with high amount | Judgment override |
| **End-of-Period** | Posting date ≥ 28th of month | Window-dressing |

The design principle here is important: **anomaly detection should not use LLMs**. A weekend posting is a weekend posting regardless of what the LLM "thinks" about it. The rules are simple, transparent, and testable.

The output is a structured `AnomalyResult` with severity (LOW/MEDIUM/HIGH), type, and a human-readable explanation.

### Test Results

From a synthetic dataset of 100 normal entries plus seeded anomalies:

```
Total entries scanned: 100
Anomalies detected:    47 (9 HIGH)

[HIGH] Round amount: $500,000 (common fraud amount)
[HIGH] Large manual entry: $500,000 (Adjustment revenue)
[HIGH] Round amount: $100,000 (common fraud amount)
[HIGH] Round amount: $50,000 × 5 (duplicate descriptions)
[HIGH] Large manual entry: $200,000 (CFO instruction)
```

The 47 total includes 25 duplicate-description hits (5 identical entries across 5 transactions), 8 end-of-period entries, 5 round-number matches, 2 manual entry flags, and 1 weekend posting. The 9 HIGH-severity flags all correspond to amounts or patterns that warrant immediate investigation.

The system does not make judgments about whether these anomalies are actual fraud. That's the auditor's role. It surfaces them with context — amount, description, timestamp — and lets the auditor decide.

---

## Materiality Engine

ISA 320 defines materiality as "misstatements that could influence the economic decisions of users." The standard allows professional judgment, but provides benchmarks:

| Base | Common % | Example ($85M PBT) |
|------|----------|-------------------|
| Profit Before Tax | 5% | $4,250,000 |
| Revenue | 0.5% | $4,250,000 |
| Total Assets | 1% | $12,000,000 |
| Equity | 1% | $4,200,000 |

The `MaterialityEngine` calculates three tiers:

**Overall Materiality**: The most conservative of the four benchmarks. For our demo engagement: $4,200,000 (equity-based, 1%).

**Performance Materiality**: A fraction of overall materiality, adjusted for audit risk:

| Risk Level | Factor | Performance ($4.2M overall) |
|------------|--------|---------------------------|
| Low | 100% | $4,200,000 |
| Medium | 75% | $3,150,000 |
| High | 50% | $2,100,000 |

**Trivial Threshold**: 5% of overall materiality ($210,000). Misstatements below this are considered clearly immaterial.

The engine applies a simpler-is-better philosophy: choose the lowest base, multiply by the standard percentage, then apply a risk adjustment. No LLM. No scoring model. Just arithmetic that can be traced back to ISA 320 paragraph references.

### Integration with Misstatement Engine

The Phase D Misstatement Engine already classifies findings as Known/Likely/Projected. The Materiality Engine completes the loop by providing the thresholds:

```
MisstatementSummary.total_all = $215,000 (known cutoff errors)
Tolerable Error = $4,200,000 (overall materiality)
Performance Materiality = $2,100,000 (HIGH risk engagement)
Trivial Threshold = $210,000

$215,000 > $2,100,000? No → within performance materiality
$215,000 > $4,200,000? No → within overall materiality
```

This integrated loop means the audit opinion engine can now determine opinion type based on objective materiality thresholds, not arbitrary classifications.

---

## The Numbers

```
Journal Testing:     100 entries → 47 anomalies (9 HIGH)
Materiality:         $4.2M overall / $2.1M performance / $210K trivial
ISA 320 Bases:       PBT, Revenue, Assets, Equity (all calculated)
Risk Adjustment:     50% (HIGH risk) / 75% (MEDIUM) / 100% (LOW)
```

---

## Lessons Learned

1. **Anomaly detection is a rules problem, not an ML problem.** Weekend posting, round numbers, and duplicate descriptions are trivial to check with simple comparisons. An ML model would add complexity, latency, and false positives without clear benefit.

2. **Materiality calculation is arithmetic, not judgment.** ISA 320 provides clear benchmarks. The engine's "choose the lowest base" rule is actually more conservative than most auditors. Implementing ISA 320 as code removes variability across engagements.

3. **Thresholds should be configurable, not hardcoded.** The ISA percentages and risk factors are default values. Different audit firms use different factors (e.g., 5% vs 10% for trivial). The engine accepts these as parameters.

4. **Journal entry testing and materiality are complementary.** The former identifies anomalies; the latter measures whether those anomalies matter. Neither is useful without the other.

---

## Next Step

V4 extends the system further with multi-period analysis (3-year trend comparisons) and a confirmation manager module for AR/AP confirmations.

---

## Key Takeaways

1. Journal entry anomalies should be detected by rules, not ML
2. ISA 320 materiality is arithmetic expressed as code
3. Six detection patterns cover the majority of audit JE testing
4. Three-tier materiality (overall/performance/trivial) is standard professional practice
5. Detection and measurement are complementary — one finds issues, the other sizes them
