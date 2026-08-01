# System Verification Review — AuditFlow v0.5.0

**Created:** 2026-08-01
**Architecture Freeze:** v0.5
**Purpose:** Release gate — every item below Architecture must be checked before v0.5.0 tag.

---

## Architecture (FROZEN — no new PRs against this section)

- [x] DDD Layer Dependency (Presentation → Application → Domain → Infrastructure)
- [x] Canonical Audit Schema (Transaction / Document / Party)
- [x] Workflow Engine (DAG + HITL + Trace + Checkpoint)
- [x] Assessment Layer (`application/assessment/`)
- [x] Evidence Graph (Assertion → Evidence → Sufficiency)
- [x] DetectionFacade (`application/detection/`)
- [x] Agent Contract (AgentRequest / AgentResponse / Citation)
- [x] ADR-0007 (Assessment in Application, not Domain)

---

## Engineering (VERIFY — PRs target these items only)

- [ ] **Benchmark ≥ 60% F1**
  - Precision ≥ 50%
  - Recall ≥ 80%
  - F1 ≥ 60%
  - Runtime < 30s
  - Random seed fixed, 100% reproducible
  - Evidence: `benchmark/` report JSON

- [x] **Workflow DAG Integration**
  - AnomalyDetectionAgent registered in Workflow Engine (bringup.py)
  - DAG: Planner → Knowledge → AnomalyDetection → Risk → Evidence → Reviewer
  - Risk Agent consumes upstream anomaly findings (ISA 240/315)
  - Evidence: integration test passing

- [x] **ISA 520 Analytical Procedures**
  - RatioEngine (7 ratios) + TrendEngine + AccountAnalyzer → RiskContext
  - Risk Agent receives structured ratios/trends/significant accounts
  - Evidence: demo Phase 1 shows ratio/trend injection

- [x] **Review Queue (HITL — ISA 500)**
  - ReviewQueue: ACCEPT / DISMISS / NEED_MORE_EVIDENCE
  - Assessment → Review Queue → Procedure (human gate)
  - Evidence: demo Phase 2.5 shows MEDIUM + incomplete evidence → NEED_MORE_EVIDENCE

- [x] **Evidence Coverage (ISA 500)**
  - Evidence Presence: 100% demo (4/4 findings have ≥1 evidence)
  - Evidence Completeness: 0% demo (missing DELIVERY → drives HITL)
  - Overall Coverage: 42% (CUTOFF 50%, OCCURRENCE 33%)

- [x] **Evaluation Complete**
  - Layer 1: Detection — F1 60.1%, Precision 67.4%, Recall 54.2%, Review Reduction 89%
  - Layer 2: Assessment — Risk Agreement 100%, Policy Coverage 100%, False Escalation 0%
  - Layer 3: Procedure — Coverage 100%, Assertion Match 100%, Evidence Presence 100%
  - Layer 4: Workflow — Success Rate 100% (9/9 stages), 4 exceptions → MODIFIED
  - Evidence: `docs/engineering/EVALUATION_REPORT.md` + `EVALUATION_MATRIX.md`

- [x] **Frontend API Connected**
  - Dashboard (Live): agents / workflows create+start / documents — 真实 API
  - Evidence Search (Live): /knowledge/search 检索 — 真实 API
  - Trace (Live): /workflows/{id}/trace — 真实 API
  - Backend fixes: CORS middleware, WorkflowEngine singleton (was per-request), AnomalyDetectionAgent registered in API
  - Evidence: vite build passes, backend /agents returns 6 agents, anomaly_detection execute SUCCESS

- [ ] **README Updated**
  - Evidence Chain diagram (Transaction → Finding → Assessment → Procedure → Evidence → Opinion)
  - Benchmark Report embedded
  - GIF/screenshot of working pipeline

---

## Release Gate

- [ ] **v0.5.0 tagged**
  - All Engineering items above checked
  - CHANGELOG updated
  - `git tag v0.5.0`

---

## Commit Policy (post-Freeze)

**ALLOWED:**
- `fix:` — bug fixes
- `perf:` — performance improvements
- `benchmark:` — benchmark results and reports
- `evaluation:` — evaluation metrics and tools
- `integration:` — integration tests and wiring
- `docs:` — documentation updates
- `frontend:` — frontend API connection
- `test:` — new tests

**REJECTED:**
- `refactor:` (architectural)
- `redesign:`
- `restructure:`
- Any commit that changes module boundaries, layer dependencies, or DDD structure

If architecture MUST change, file an ACP (Architecture Change Proposal) in `docs/adr/`.
