# API Contracts — Sprint 11: InMemory Lifecycle Implementation

## Deliverables
- Updated src/adapters/memory.py
- tests/test_inmemory_lifecycle.py (25 tests)

## Backend Contracts
### InMemoryAdapter Methods
- `start_sprint(sprint_id) -> Sprint` — creates steps, sets status to IN_PROGRESS
- `advance_step(sprint_id, step_output=None) -> Sprint` — marks current step complete, sets next to IN_PROGRESS, captures output
- `complete_sprint(sprint_id) -> Sprint` — validates all steps done, transitions to DONE
- `block_sprint(sprint_id, reason) -> Sprint` — sets BLOCKED status, records reason in transition
- `get_step_status(sprint_id) -> dict` — returns current step, progress percentage, step details

## Frontend Contracts
- N/A
