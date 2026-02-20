# API Contracts — Sprint 16: Core Sprint Runner

## Deliverables
- New src/execution/ package
- src/execution/runner.py
- tests/test_sprint_runner.py (12 tests)

## Backend Contracts
### SprintRunner
- `__init__(self, backend, agent_registry, hooks=None)` — constructor with backend adapter, agent registry, optional hooks
- `async run(self, sprint_id, on_progress=None) -> RunResult` — orchestrates full sprint execution
- `async resume(self, sprint_id) -> RunResult` — resumes from last completed step
- `async cancel(self, sprint_id, reason) -> None` — graceful cancellation

### Dataclasses
- `RunResult` — sprint_id, success, steps_completed, steps_total, agent_results, deferred_items, duration_seconds

## Frontend Contracts
- N/A
