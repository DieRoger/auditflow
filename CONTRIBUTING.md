# Contributing

## Development Workflow

1. Pick an Issue from [ISSUES.md](ISSUES.md)
2. Create a branch: `epic/issue-id-description`
3. Implement with tests
4. Run `make lint && make test`
5. Submit PR

## Code Standards

- Python 3.11+ with type hints
- Ruff lint + format
- MyPy strict mode
- Pytest coverage >= 80%
- Docstrings for all public APIs

## Agent Development

All Agents must:
1. Extend BaseAgent
2. Declare input_schema and output_schema
3. Include prompt.md + tools.py + tests.py
4. Pass Evaluation benchmarks

## Contract Changes

Architecture Baseline v1.0 is frozen. Contract changes require:
- ADR decision record
- Version bump (v1 -> v2)
- Migration plan
