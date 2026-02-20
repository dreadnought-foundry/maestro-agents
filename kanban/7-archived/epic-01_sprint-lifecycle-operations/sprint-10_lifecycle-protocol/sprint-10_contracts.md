# API Contracts — Sprint 10: Lifecycle Protocol Methods

## Deliverables
- Updated src/workflow/interface.py
- New src/workflow/exceptions.py
- tests/test_lifecycle_protocol.py (15 tests)

## Backend Contracts
### Protocol Methods (WorkflowBackend)
- `start_sprint(sprint_id) -> Sprint` — transitions TODO to IN_PROGRESS, creates initial steps
- `advance_step(sprint_id, step_output=None) -> Sprint` — marks current step complete, advances to next
- `complete_sprint(sprint_id) -> Sprint` — transitions IN_PROGRESS to DONE (all steps must be done)
- `block_sprint(sprint_id, reason) -> Sprint` — transitions IN_PROGRESS to BLOCKED
- `get_step_status(sprint_id) -> dict` — returns current step, progress, step details

### Exceptions
- `InvalidTransitionError` — raised on illegal state changes, includes from/to states

### State Transitions
- TODO -> IN_PROGRESS (start)
- IN_PROGRESS -> DONE (complete, all steps done)
- IN_PROGRESS -> BLOCKED (block)
- BLOCKED -> IN_PROGRESS (resume)

## Frontend Contracts
- N/A
