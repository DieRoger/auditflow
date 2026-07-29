---
title: "From Document AI to Audit Execution Platform — The Schema That Changed Everything"
description: "Why AuditFlow needed a Canonical Audit Schema, an Import Framework, and a Procedure Engine — and how shifting from PDF-only input to structured financial data transformed the system from an AI chatbot into an audit execution platform."
date: "2026-07-30"
tags:
  - AI
  - Architecture
  - Agent
  - Engineering
  - Audit
  - RAG
  - Evidence
categories:
  - Engineering Decisions
  - Build Log
slug: from-document-ai-to-audit-execution
draft: false
author: Luo Runjie
readingTime: 20
difficulty: Advanced
---

## Background

Two weeks ago, AuditFlow looked like a success. The system could take a PDF, parse it through PyMuPDF, chunk it, embed it into PGVector, run five specialized AI agents against it, and output an ISA 700-compliant audit report. The demo was convincing. The evaluation metrics showed 75% severity accuracy. Three thousand document chunks were indexed across 67 documents.

But there was a problem I couldn't ignore: **the system couldn't actually perform an audit.**

Not a real one. Not the kind an accounting firm does every day.

Here is what a real audit looks like:

```
General Ledger / Trial Balance
    ↓
Risk Assessment
    ↓
Audit Program (specific procedures)
    ↓
Substantive Procedures (sampling, cutoff testing, confirmation)
    ↓
Evidence Collection (invoice, delivery note, contract)
    ↓
Misstatement Evaluation (known → likely → projected)
    ↓
Adjustment Entries (AJE / RJE)
    ↓
Audit Opinion
```

And here is what AuditFlow looked like:

```
PDF
    ↓
RAG
    ↓
LLM
    ↓
Report
```

The gap was not in quality. It was in **kind**. We had built a brilliant document analysis tool, but we hadn't built an audit system. An LLM can describe a risk. An audit system must *test* a risk.

---

## The Moment of Clarity

The realization crystallized during a review session when someone asked: "How would you audit revenue cutoff on this system?"

The answer was uncomfortable: "The Risk Agent would identify cutoff as a risk, and the Evidence Agent would find relevant text in the PDF." But auditing revenue cutoff isn't about finding text. It's about:

1. Taking the **sales detail** (from Excel, not PDF)
2. Sampling transactions around period-end
3. Comparing **transaction dates** to **shipping dates**
4. Identifying mismatches as exceptions
5. Calculating the projected misstatement
6. Documenting the finding in a working paper

None of these steps could happen with PDF-only input. The PDF tells you the *policy*. The structured data tells you *what actually happened.*

This is the fundamental difference between **reading about an audit** and **performing one.**

---

## The Architecture Pivot

The decision was to redesign the data architecture around a concept I called **Canonical Audit Schema** — a unified data model that represents financial transactions, documents, and parties in a way that all subsequent audit procedures could consume without knowing where the data came from.

Before the pivot:

```
PDF → OCR → RAG → Agent
```

After the pivot:

```
                    ┌─────────────────────────┐
                    │    Audit Data Hub        │
                    │                          │
  Excel/CSV ────────┤  Import Framework        │
  PDF ──────────────┤  (ImportSession/Record)  │
  (existing)        │                          │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │  Canonical Audit Schema   │
                    │  Transaction / Document   │
                    │  / Party                  │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │  Audit Procedure Engine   │
                    │  Risk → Program → Execute │
                    │  → Evidence Graph         │
                    └──────────────────────────┘
```

The key architectural insight was: **the Import Framework and the Canonical Schema belong to different bounded contexts.** The Import Context is responsible for *how data arrives* (Excel columns, CSV parsing, validation errors). The Finance Domain is responsible for *what the data means* (a Transaction, a Document, a Party). Mixing them would pollute the audit domain model with import concerns.

---

## Phase A: The Canonical Schema

I froze the schema in two documents before writing any code:

- `docs/architecture/CANONICAL_AUDIT_SCHEMA.md` — the Finance Domain
- `docs/architecture/IMPORT_FRAMEWORK.md` — the Import Context

The Finance Domain has three entities (MVP):

| Entity | Key fields | Purpose |
|--------|-----------|---------|
| `Transaction` | type, date, period, amount, party_id, document_refs | One auditable business transaction |
| `Document` | type (INVOICE/DELIVERY/CONTRACT), number, date | Evidence supporting transactions |
| `Party` | type (CUSTOMER/VENDOR), name | Counterparty reference |

The Import Context has four entities:

| Entity | Key design decision |
|--------|-------------------|
| `ImportSession` | Aggregates one file upload, tracks status |
| `ImportRecord` | One row of raw Excel data, **raw_data is never modified** |
| `MappingProfile` | Reusable column-to-field mapping |
| `ValidationResult` | Aggregated per-session |

The most important design decision: **ImportRecord holds `canonical_refs: {type: "transaction", id: UUID}` instead of embedding a Transaction.** This means ImportRecord → 0..1 Transaction, not 1:1. A validation failure means an ImportRecord exists but no Transaction was generated. The user can correct the mapping and regenerate without re-uploading the file.

This is how SAP, Oracle, and Kingdee all work internally. It's not a clever optimization — it's standard ETL architecture, applied to audit data.

---

## The Excel Problem

The Excel Adapter has one job: turn spreadsheet rows into ImportRecords. This sounds trivial, but it isn't, because **audit firms do not use standard column names.**

A single firm might label the invoice date column as "日期", "销售日期", "Sales_Date", or "Invoice Date" — across different projects from different ERP exports within the same engagement.

The first instinct is to use an LLM to auto-detect column meanings. I rejected this for Phase A. The reason: an LLM with 96% confidence on column mapping will still be wrong 4% of the time, and a wrong column mapping in audit can mean sampling the wrong transactions entirely — a catastrophic failure mode.

Instead, Phase A uses **Template Mapping**: the user opens a preview, sees the first five rows, and selects which column maps to each canonical field. The system saves this as a MappingProfile. Next time, it loads the profile. One click.

Phase B will add LLM *suggestion* — the model suggests mappings, but the user must confirm. Auto-mapping only comes in Phase C, and even then, only when confidence exceeds 90%.

This progression was deliberate: **never trust the AI with irreversible data transformations before there is a human in the loop.**

---

## Phase B: The Procedure Engine

With the Canonical Schema in place, I built the Audit Procedure Engine — the component that executes specific audit procedures against structured data.

The domain model:

```python
AuditProgram          # A set of procedures for one audit area
  └── AuditProcedure  # One procedure (e.g., Revenue Cutoff Test)
        ├── assertions: [CUTOFF, OCCURRENCE]
        ├── sampling: SamplingConfig(method, size)
        └── findings: [AuditFinding]
```

The `SamplingEngine` supports three methods: **random** (fixed seed for reproducibility), **MUS** (monetary unit sampling — larger amounts get higher probability), and **all** (no sampling, test the entire population).

The `CutoffProcedureExecutor` is a concrete procedure that takes transactions, cutoff dates, and enriched records (with both transaction and shipping dates extracted from ImportRecords), and returns findings:

```
Sample: 29 transactions around FY2025 period-end
Findings: 4 exceptions

[HIGH] Revenue recognized 2025-12-31 but shipped 2026-01-02 — $50,000
[HIGH] Revenue recognized 2025-12-31 but shipped 2026-01-03 — $35,000
[HIGH] Revenue recognized 2025-12-30 but shipped 2026-01-05 — $42,000
```

Exception rate: 13.8%. This is a real audit metric.

---

## Phase C: The Evidence Graph

One problem the existing system had: the Evidence Agent would produce a "confidence" score (which was usually just the LLM's self-assessment), and the Reviewer Agent would accept or reject it. But neither component could answer a fundamental question: **is the evidence sufficient?**

The Evidence Graph answers this structurally:

```
Assertion: CUTOFF
  Required evidence: [INVOICE, DELIVERY]
  Present: ✓ INVOICE (1 found)
  Missing: ✗ DELIVERY
  Conclusion: PARTIALLY SATISFIED (50%)

Assertion: OCCURRENCE
  Required evidence: [INVOICE, CONTRACT, DELIVERY]
  Present: ✓ INVOICE
  Missing: ✗ CONTRACT, ✗ DELIVERY
  Conclusion: PARTIALLY SATISFIED (33%)

Overall: PARTIALLY SATISFIED
```

This is not an LLM's opinion. It's a structural check: does the evidence match the assertion's requirements?

The `EvidenceMapper` uses a fixed mapping table:

```python
REQUIRED_EVIDENCE = {
    "CUTOFF":      ["INVOICE", "DELIVERY"],
    "OCCURRENCE":  ["INVOICE", "CONTRACT", "DELIVERY"],
    "COMPLETENESS": ["INVOICE", "SHIPPING"],
    "ACCURACY":    ["INVOICE", "RECALCULATION"],
    ...
}
```

This is intentionally not LLM-powered. Evidence sufficiency is a rules problem, not a reasoning problem. An LLM should not decide whether you have enough evidence — it should find the evidence. The graph should verify it.

The LLM handles the fuzzy part: finding relevant documents, understanding their content, extracting assertions. The graph handles the deterministic part: checking completeness.

---

## What This Means for the System

Before this pivot, AuditFlow was a **document AI assistant**. It could read and reason about financial documents, but it couldn't execute audit procedures.

After Phase A/B/C, it's now an **evidence-driven audit execution platform:**

1. Import structured data (Excel, future ERP exports) alongside PDFs
2. Map to a canonical audit schema (not ad-hoc transformation)
3. Generate an audit program based on risk assessment
4. Execute specific procedures (cutoff, sampling, recalculation)
5. Build an evidence graph per assertion with sufficiency scoring
6. Produce a working paper with quantified findings

The existing components — the five agents, the Workflow Engine, the PDF pipeline, the evaluation framework — all still work. They were not replaced. They were given a new input channel. The Risk Agent now has structured financial data to work with, not just document text. The Evidence Agent can include procedure findings alongside document citations. The Reviewer Agent gets the Evidence Graph's structural conclusion, not just a self-reported confidence score.

---

## The Numbers

The full Revenue Cutoff Demo runs in under 30 seconds:

| Phase | Component | Result |
|-------|-----------|--------|
| Import | 29 rows → Canonical | 29 Transactions + 29 Parties |
| Risk | DeepSeek LLM | HIGH — Premature Revenue Recognition |
| Program | AuditProcedure | CUTOFF_TEST, assertions: [Cutoff, Occurrence] |
| Execute | CutoffProcedureExecutor | 4 findings (13.8% exception rate) |
| Evidence Graph | Assertion sufficiency | CUTOFF 50%, OCCURRENCE 33% |
| Working Paper | Structured output | Exceptions listed with amounts |

Existing test suite: 77/77 passed, zero regression. This is the real test — adding a new data channel without breaking the existing document pipeline.

---

## Lessons Learned

1. **Data architecture determines system capability.** Adding a canonical schema didn't just add a feature — it changed what kind of system AuditFlow could be. Without structured data, it's a reader. With it, it's an executor.

2. **Don't let LLMs make reversible decisions irreversible.** The Excel import might auto-map columns eventually, but the raw data must always be preserved. If the mapping is wrong, the user can correct it and regenerate. This pattern — LLM suggests, human confirms, system records — should apply to every irreversible transformation.

3. **Bounded Contexts matter even in single-developer projects.** Separating Import Context from Finance Domain felt like over-engineering at first. It paid off immediately when I realized ImportRecords could hold validation state without polluting the Transaction model.

4. **Evidence sufficiency is not an LLM problem.** The Evidence Graph uses a fixed rules table, not a model. This is faster, more reliable, and more explainable. LLMs should handle the fuzzy part (finding evidence); deterministic rules should handle the checkable part (is it sufficient?).

---

## Next Step

Phase D: the Misstatement Engine. Take the 4 cutoff exceptions, calculate known misstatement amounts, determine whether they require adjustment entries (AJE), and project the effect on the overall financial statements. This turns findings into accounting actions — the bridge between audit procedure and audit opinion.

---

## Key Takeaways

1. A document AI system is not an audit system — structured data is the missing half
2. Canonical schemas are worth the upfront cost; they enable every procedure that follows
3. Separate Import from Domain: raw data persistence enables remapping without re-upload
4. LLMs find evidence; deterministic rules verify sufficiency — don't mix the two
5. Breaking no existing tests is the real proof that your architecture extension was clean
