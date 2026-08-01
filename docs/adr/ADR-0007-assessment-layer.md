# ADR-0007: Assessment Layer — Application, not Domain

**Status:** Accepted
**Date:** 2026-08-01
**Author:** Code Review + Architecture Freeze session
**Supersedes:** Grill Session Design (assessment in `domain/audit/entities/`)
**Affects:** ADR-001 (Agent Contract), Architecture v0.4 → v0.5

---

## Context

The Grill Session (2026-07-31) designed an `Assessment` object to merge two risk sources:

- **Risk Agent (LLM)**: narrative risk analysis ("why there is risk")
- **Anomaly Detection (Rule)**: quantitative findings ("what was detected")

The initial design placed `Assessment` in `domain/audit/entities/`, treating it as an audit domain
object. During Code Review, this was challenged: Assessment is not a real audit concept in ISA.
It is an application-level orchestration artifact that merges outputs from multiple sources before
passing them to procedure planning.

## Decision

**Move Assessment to `application/assessment/`:**

```
application/
  assessment/
    assessment.py          — Assessment value object
    assessment_policy.py   — 8 explicit rules (frozen at ≤10)
    assessment_service.py  — merges RiskFindingArtifact + FindingArtifact
```

Dependency direction:

```
Risk Agent (agents/)         AnomalyDetectionAgent (agents/)
       │                              │
       │  RiskFindingArtifact         │  FindingArtifact
       │  (domain/artifacts.py)       │  (domain/artifacts.py)
       │                              │
       └──────────┬───────────────────┘
                  ▼
      AssessmentService (application/assessment/)
                  │
                  ▼
      ProcedurePlanningService (application/audit/)
                  │
                  ▼
      CutoffProcedureExecutor (application/audit/)
```

**Key architectural constraints:**

1. Assessment is NOT a domain entity. It has no persistence, no repository, no lifecycle.
2. AssessmentPolicy rules are frozen at ≤10. Adding more requires splitting into independent
   Policy classes (e.g., RevenueAssessmentPolicy).
3. Evidence dominates narrative: Rule-based findings override LLM judgments (Rules 1, 4).
4. Materiality acts as a safety valve: insignificant amounts don't escalate (Rule 8).

## Alternatives Considered

### Option A: Keep Assessment in `domain/audit/entities/`

- **Pros:** Follows existing DDD pattern; Assessment near Procedure entities
- **Cons:** Assessment is an orchestration artifact, not a business entity. ISA has no "Assessment"
  concept. Would pollute domain layer with application concerns.
- **Decision:** Rejected

### Option B: Make Assessment a Workflow context field (inline dict)

- **Pros:** Zero new modules, simplest possible
- **Cons:** No type safety, no testability, no reusability. Violates Clean Architecture
  principle that orchestration logic should be explicit.
- **Decision:** Rejected

## Consequences

### Positive

- Clear separation: Domain owns business rules (RiskScoringEngine, AuditProcedure),
  Application owns orchestration (Assessment, ProcedurePlanning)
- AssessmentPolicy is independently testable (8 rules, 0 LLM calls)
- Adding new risk sources (Benford, IsolationForest, ERP API) only requires
  extending AssessmentService, not changing domain

### Negative

- Introduces a new `application/assessment/` module (increases module count by 1)
- Assessment and RiskFindingArtifact share overlapping fields (severity, probability) —
  potential for confusion if naming drifts

### Neutral

- Finding's `recommended_procedures` field remains (recognized as architectural debt,
  not a bug — fixing it would touch too many downstream consumers)

## DetectionFacade — Additional Decision

AnomalyDetectionAgent now delegates to `DetectionFacade` (application/detection/) instead of
calling `RiskScoringEngine.scan_all()` directly. This allows future detection algorithms
(Benford, IsolationForest, LOF) to be registered without changing the Agent.

```
Workflow → AnomalyDetectionAgent → DetectionFacade → RiskScoringEngine
                                                 → (future: BenfordDetector)
                                                 → (future: IsolationForestDetector)
```

## Architecture Freeze v0.5

This ADR marks **Architecture Freeze v0.5** for the Revenue Vertical Slice. The following
structural decisions are now frozen:

| Element | Location | Status |
|---------|----------|--------|
| Assessment + Policy + Service | `application/assessment/` | FROZEN |
| DetectionFacade | `application/detection/` | FROZEN |
| ProcedurePlanningService | `application/audit/` | FROZEN |
| AnomalyDetectionAgent | `agents/anomaly_detection/` | FROZEN |
| FindingArtifact | `domain/artifacts.py` | FROZEN |
| AssessmentPolicy | ≤10 rules | FROZEN |

Subsequent changes should extend within these boundaries, not restructure them.

## Related

- ADR-001: Agent Contract
- Grill Session transcripts (2026-07-31, Rounds 1-4)
- Code Review (2026-08-01)
