---
title: "The Final Step — How AuditFlow's Completion Engine Determines Audit Opinions"
description: "From Partner Review to Audit Opinion: how AuditFlow's Phase E Completion Engine synthesizes misstatement findings, evidence sufficiency, and quality control reviews to determine the final audit opinion — DISCLAIMER for a $215K cutoff failure."
date: "2026-07-30"
tags:
  - AI
  - Engineering
  - Audit
  - Evidence
  - Completion
categories:
  - Build Log
  - Engineering Decisions
slug: audit-completion-engine
draft: false
author: Luo Runjie
readingTime: 12
difficulty: Advanced
---

## Background

After four phases of building — importing structured data, executing cutoff procedures, evaluating evidence graphs, and calculating misstatements — the last question remains: what does all of this add up to?

In a real audit, this is the **Completion** stage: partner review, engagement quality control review, management representation, and — most importantly — the audit opinion. ISA 700 (forming an opinion), ISA 705 (modified opinions), and ISA 706 (emphasis of matter) govern this stage.

Phase E built the domain model and decision logic for this final step.

---

## The Design

### Opinion Determination Logic

The core decision: given everything we now know about the audit, what opinion type is appropriate?

```text
Misstatement exceeds tolerable?  ─┬─ Yes ─┬─ Evidence insufficient? ─── DISCLAIMER
                                  │        └─ Evidence sufficient? ───── ADVERSE
                                  │
                                  └─ No ───┬─ Evidence insufficient? ─── QUALIFIED
                                           └─ Evidence sufficient? ───── UNQUALIFIED
```

In our Revenue Cutoff Demo, the result was clear:

| Condition | Value |
|-----------|-------|
| Misstatement exceeds tolerable | Yes ($215K > $50K) |
| Evidence sufficient | No (CUTOFF 50%, OCC 33%) |
| **Result** | **DISCLAIMER OF OPINION** |

This is the correct outcome per ISA 705: when misstatements are both material and pervasive, and the auditor cannot obtain sufficient evidence, a disclaimer is required.

### Partner Review and EQCR

The completion engine models two layers of review:

- **Partner Review**: the engagement partner's final sign-off, including issues found and overall conclusion
- **EQCR**: Engagement Quality Control Review, performed by an independent reviewer who was not part of the engagement team — required for high-risk engagements

Both reference specific findings and key professional judgments, preserving an audit trail from procedure to opinion.

### Management Representation Letter

The engine generates a standard representation letter covering management's acknowledgments:

```
MANAGEMENT REPRESENTATION LETTER
==================================================

To the Independent Auditor,

We confirm, to the best of our knowledge and belief, the following
representations made to you during your audit:

  - All financial records have been made available to the auditor
  - All revenue transactions are recorded in the correct period
  - No side agreements or undisclosed contract modifications exist
  - Management acknowledges the proposed $215K revenue cutoff adjustment

Signed: CEO Zhang / CFO Liu
Date: 2026-07-30
```

This is not an LLM's output — it's a templated document populated with findings from the audit workflow.

---

## The Full Pipeline

With Phase E complete, the end-to-end audit pipeline now covers:

```text
Excel Import           (Phase A)
    ↓
Canonical Schema       (Phase A)
    ↓
Risk Assessment        (Phase B)
    ↓
Audit Program          (Phase B)
    ↓
Procedure Execution    (Phase B)  — 4 cutoff exceptions
    ↓
Evidence Graph         (Phase C)  — CUTOFF 50%, OCC 33%
    ↓
Misstatement Summary   (Phase D)  — $215K EXCEEDS $50K
    ↓
Audit Completion       (Phase E)
    ├── Partner Review           — APPROVED
    ├── EQCR                     — APPROVED
    ├── Audit Opinion            — DISCLAIMER
    ├── Management Rep Letter    — SIGNED
    └── Archive                  — Archived
```

---

## Lessons Learned

1. **Opinion determination is rule-based, not LLM-based.** The decision tree (misstatement × evidence → opinion type) is a deterministic function. An LLM should not be asked to "reason" about which opinion to issue — it should apply the rules.

2. **Dual review is a real audit requirement.** Partner review and EQCR serve different purposes (engagement responsibility vs. independent quality control). Modeling them separately preserves the audit trail.

3. **Completion aggregates, not re-evaluates.** The Completion Engine does not re-run procedures or re-evaluate evidence. It synthesizes what was already found and applies professional standards. Clean separation from earlier phases prevents double-counting.

4. **The representation letter is a contract, not a formality.** Including specific misstatement acknowledgments (not just boilerplate) makes the letter auditable and defensible.

---

## Next Step

All five Phases (A-E) are now complete. The system goes from Excel import to audit opinion in under 30 seconds for a Revenue Cutoff engagement. Next: expand the Data Hub to support additional ERP exports (Kingdee, Yonyou) and build procedure templates for Inventory, AR, and AP cycles.

---

## Key Takeaways

1. Audit opinions come from rules, not from LLM reasoning
2. Dual review (Partner + EQCR) is not over-engineering — it's audit standard
3. Completion aggregates findings; it does not re-evaluate them
4. A $215K cutoff failure with insufficient evidence → DISCLAIMER, per ISA 705
