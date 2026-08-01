# Evaluation Report — Assessment & Procedure & Workflow Layers

**Generated:** 2026-08-01 14:29
**Cases:** 6 (rule-based golden, no LLM dependency)

| Layer | Metric | Score |
|-------|--------|-------|
| 2. Assessment | Risk Agreement | 100.0% |
| 2. Assessment | Policy Coverage | 100.0% |
| 2. Assessment | False Escalation | 0.0% |
| 3. Procedure | Procedure Coverage | 100.0% |
| 3. Procedure | Assertion Match | 100.0% |
| 4. Workflow | End-to-end Success | 100.0% |
| 4. Workflow | Exceptions Found | 4 (Opinion: MODIFIED) |

## Per-Case Details

### G001: HIGH finding + HIGH narrative → HIGH
- Risk Agreement: 100%
- Procedure Coverage: 100%
- Planned Assertions: ['CUTOFF', 'OCCURRENCE', 'OCCURRENCE']

### G002: LOW narrative + no findings → LOW
- Risk Agreement: 100%
- Procedure Coverage: 100%
- Planned Assertions: ['OCCURRENCE']

### G003: HIGH narrative only, no findings → MEDIUM (Rule 3 downgrade)
- Risk Agreement: 100%
- Procedure Coverage: 100%
- Planned Assertions: ['OCCURRENCE']

### G004: HIGH finding but amount < materiality → LOW (Rule 8)
- Risk Agreement: 100%
- Procedure Coverage: 100%
- Planned Assertions: ['OCCURRENCE']

### G005: 10+ LOW findings → MEDIUM (Rule 2)
- Risk Agreement: 100%
- Procedure Coverage: 100%
- Planned Assertions: ['OCCURRENCE']

### G006: Low confidence HIGH findings → capped (Rule 7)
- Risk Agreement: 100%
- Procedure Coverage: 100%
- Planned Assertions: ['OCCURRENCE']
