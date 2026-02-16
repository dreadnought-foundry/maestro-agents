# API Contracts — Sprint 18: Pause, Resume, and Retry Logic

## Deliverables
- Updated src/execution/runner.py
- tests/test_pause_resume.py (10 tests)

## Backend Contracts
### SprintRunner Methods
- `async resume(self, sprint_id) -> RunResult` — finds last completed step, continues execution from next step
- `async cancel(self, sprint_id, reason) -> None` — sets sprint to blocked, records reason, preserves state

### Configuration
- `RunConfig` — max_retries: int = 2, retry_delay_seconds: float = 1.0

### Behavior
- Failed steps retry up to max_retries before blocking the sprint
- Resume identifies the correct restart point from step statuses
- Cancel is non-destructive and allows future resume

## Frontend Contracts
- N/A
