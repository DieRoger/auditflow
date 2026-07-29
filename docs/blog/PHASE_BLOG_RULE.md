# Phase Completion Blog Rule

## Purpose

Every completed development phase **MUST** produce an engineering blog article. Blog writing is not optional — it is part of the definition of "done."

## Trigger

This rule applies whenever a developer or AI agent completes one of the following:

- A new Phase (A, B, C, D, E) in the AuditFlow roadmap
- A major module addition (new domain entity, new engine, new pipeline)
- An architecture pivot (data flow redesign, new input channel)
- A system milestone (MVP ready, first real-data test, evaluation pass)

## Requirements

### 1. Follow blog_rules.md Structure

Every blog must contain:

- **Background** — the problem that was being solved
- **Initial Design** — what was first attempted
- **Problems Encountered** — real issues (not hypothetical)
- **Alternative Solutions** — with trade-offs
- **Final Design** — with architecture/flow diagram
- **Implementation Notes** — key engineering decisions
- **Lessons Learned** — 4-5 actionable insights
- **Future Improvements** — honest about what's still imperfect

### 2. Include Evidence

- Benchmark numbers or metrics
- Logs or example output
- Before/after comparisons where applicable
- Links to relevant commits/PRs (if available)

### 3. Follow Content Strategy

- Target audience: AI Engineers, Backend Engineers, Graduate Students
- Tone: Professional, honest, evidence-driven
- Personal voice: first-hand experience, not generic AI phrasing
- Reading time: 10-25 minutes (1,500-4,000 words)
- Frontmatter must include: title, description, date, tags, categories, slug, author, readingTime, difficulty

### 4. Always Relate to One of the Four Pillars

- Evidence
- Evaluation
- Observability
- Human Control

## File Location

```
docs/blog/<slug>.md
```

## Checklist

Before closing a phase, verify:

- [ ] Blog file exists at `docs/blog/<slug>.md`
- [ ] Frontmatter is complete (title, description, date, tags, etc.)
- [ ] Contains at least 4 sections from the required structure
- [ ] Includes numerical evidence (metrics, benchmarks, logs)
- [ ] Relates to at least one of the four pillars
- [ ] Reading time is estimated and below 30 minutes
- [ ] No marketing language, no clickbait, no empty claims

## Examples

| Phase | Blog |
|-------|------|
| System Bring-up | `docs/blog/building-auditflow.md` |
| Phase A/B/C pivot | `docs/blog/from-document-ai-to-audit-execution.md` |
| Phase D | `docs/blog/misstatement-engine.md` |
