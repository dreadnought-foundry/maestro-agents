# API Contracts — Sprint 09: Step Models and Status Tracking

## Deliverables
- Updated src/workflow/models.py
- tests/test_step_models.py (12 tests)

## Backend Contracts
### Enums
- `StepStatus` — TODO, IN_PROGRESS, DONE, FAILED, SKIPPED

### Dataclasses
- `Step` — id, name, status, agent (str), output (dict|None), started_at, completed_at, metadata
- `SprintTransition` — from_status, to_status, timestamp, reason
- `Sprint` (updated) — added steps: list[Step] and transitions: list[SprintTransition] fields

## Frontend Contracts
- N/A
