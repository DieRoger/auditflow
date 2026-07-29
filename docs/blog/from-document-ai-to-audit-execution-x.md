I just completed the biggest architecture pivot in AuditFlow: from Document AI → Evidence-driven Audit Execution Platform.

The problem: my system could READ financial documents with AI, but couldn't PERFORM an actual audit.

Real audit isn't PDF → LLM → Report. It's:
- Excel/TB import
- Sampling
- Cutoff testing
- Misstatement calculation
- Adjustment entries

Here's what I built (Phase A/B/C) and what I learned 🧵

1/ Canonical Audit Schema

The most important design decision: don't build business tables (sales_detail, invoice_register). Build canonical entities instead.

Transaction / Document / Party. 3 tables. Works for Revenue, Inventory, AP, AR — future cycles without schema changes.

docs/architecture/CANONICAL_AUDIT_SCHEMA.md ← froze before code

2/ Import Framework

ImportRecord.save_raw_data(forever=True). If mapping is wrong, correct+regenerate. No re-upload. Same as SAP/Oracle ETL.

This should be standard for any AI system ingesting external data.

3/ Procedure Engine

AuditProgram → AuditProcedure → execute(). 
29 transactions around period-end → 4 cutoff exceptions (13.8%)

$50K, $35K, $42K, $88K — shipped AFTER year-end but recognized BEFORE.

4/ Evidence Graph — my favorite

Required: [INVOICE, DELIVERY] for CUTOFF assertion
Present: ✓ INVOICE
Missing: ✗ DELIVERY
→ PARTIALLY SATISFIED

This is NOT an LLM's opinion. It's a structural check. LLMs find evidence. Rules verify sufficiency. Don't mix them.

5/ Key architecture decisions:

- ImportRecord → 0..1 Transaction (not 1:1 — validation failures)
- Canonical Schema ≠ Import Framework (different bounded contexts)
- Template Mapping before LLM auto-mapping (human confirms first)
- 77/77 tests passed after all changes — zero regression

Full article: [link]

#AIEngineering #AuditAI #SoftwareArchitecture
