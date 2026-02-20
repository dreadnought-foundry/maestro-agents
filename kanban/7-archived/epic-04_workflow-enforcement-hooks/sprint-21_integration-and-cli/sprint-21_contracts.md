# API Contracts — Sprint 21: End-to-End Integration and CLI

## Deliverables
- src/execution/__init__.py (convenience functions)
- src/execution/cli.py (CLI entry point)
- tests/test_e2e_integration.py (integration tests)
- Updated Makefile
- Updated docs

## Backend Contracts
### Convenience Functions
- `run_sprint(sprint_id, **kwargs) -> RunResult` — wires backend, agents, hooks, and runner; executes sprint

### CLI
- `python -m src.execution run <sprint_id>` — runs a sprint end-to-end from command line

### Makefile
- `make run-sprint SPRINT=<id>` — convenience target for sprint execution

### Integration Tests
- Full lifecycle: create epic -> create sprint -> run sprint -> verify completion
- Hook enforcement: coverage gate blocks undercovered sprint
- Resilience: resume after failure

## Frontend Contracts
- N/A
