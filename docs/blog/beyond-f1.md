# Beyond F1: How We Evaluated an AI Audit Copilot

> AuditFlow 工程博客 · 第 7 篇
> 关键词: evaluation, ground truth, audit AI, review reduction

---

## Part 1 — Why Accuracy Is Meaningless Here

An audit copilot doesn't answer one question. It answers a chain of them:

- Did this transaction look abnormal?
- How risky is this area?
- What procedures should we run?
- Is the evidence sufficient?

Each layer has a different ground truth. Collapsing all of them into a single
"accuracy" number is not just lossy — it's misleading.

We learned this the hard way. Our first "end-to-end evaluation" reported 0%
accuracy on the Risk Agent, even though every manual demo looked fine. The
problem wasn't the agent. It was the metric: we were comparing a structured
risk report against free-form text expectations.

**Lesson: define what "correct" means *before* building the system, per layer,**
**not after.**

---

## Part 2 — Why Workflow Has No Accuracy

You cannot score a workflow engine the way you score a classifier. A workflow
is infrastructure: it either runs to completion, recovers from failure, and
produces traces — or it doesn't.

We explicitly removed "Workflow Accuracy" from our evaluation matrix. Instead,
we report:

| Metric | Result |
|--------|--------|
| Success Rate (9/9 stages) | 100% |
| Exception Detection | 4 cutoff exceptions |
| Failed Stages | none |

Claiming "workflow accuracy" would be like claiming your operating system has
97% accuracy. It's the wrong frame.

---

## Part 3 — The Four-Layer Evaluation

We evaluate AuditFlow as a **layered system**, each layer with its own
ground truth, dataset, and metric:

| Layer | Dataset | Metric | Ground Truth |
|-------|---------|--------|--------------|
| Detection | Kaggle #1 | Precision / Recall / F1 | Abnormal_Label |
| Assessment | Kaggle #1 | Risk Accuracy (Balanced) | Risk_Class |
| Procedure | Kaggle #1 | Mapping Coverage | Rule Mapping |
| Evidence | Kaggle #1 | Reference Completeness | Required Fields |
| Workflow | Synthetic | Success Rate | Expected Pipeline |

This table is what makes the project *reproducible*. Anyone can re-run the
scripts and get the same numbers. That matters more than any single metric.

---

## Part 4 — Review Reduction Beats F1

Here is the number that actually matters to an auditor:

```
Review Reduction: 89%
```

Out of 7,000 transactions, AuditFlow flags **769** for human review — a
91% reduction in what a human would otherwise read. An auditor does not need
to know that F1 = 60.1%. They need to know: *how much of my workload does this
remove, and can I trust what's left?*

F1 optimizes the classifier. Review Reduction optimizes the **human**.

---

## Part 5 — Error Analysis: Where We're Wrong

Every evaluation should end with an honest autopsy. Ours shows:

- **False positives** come mostly from business-common signals (night/weekend
  transactions, cross-province flows) being scored as anomalies.
- **False negatives** cluster in anomaly types our signal set doesn't cover:
  `High_Risk_Vendor` (134 missed), `Round_Trip_Transfer` (107), `Split_Transaction` (48).
- **MEDIUM risk** is systematically over-predicted as HIGH — a calibration gap
  between our score→level mapping and Kaggle's `Risk_Class` granularity.

We publish these limitations deliberately. A copilot that claims to never be
wrong is a liability; one that documents where it fails is trustworthy.

---

## Conclusion

AuditFlow does not attempt to replace auditors. It reduces review workload,
organizes evidence, and supports professional judgment through evidence-driven
AI assistance. The evaluation framework — four layers, explicit ground truth,
balanced metrics, and honest error analysis — is the real contribution.
