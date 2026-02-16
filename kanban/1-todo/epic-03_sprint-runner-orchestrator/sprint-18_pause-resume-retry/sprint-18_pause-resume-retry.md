---
sprint: 18
title: "Pause, Resume, and Retry Logic"
type: backend
epic: 3
status: planning
created: 2026-02-15T00:00:00Z
started: null
completed: null
hours: null
---

# Sprint 18: Pause, Resume, and Retry Logic

## Overview

| Field | Value |
|-------|-------|
| Sprint | 18 |
| Title | Pause, Resume, and Retry Logic |
| Type | backend |
| Epic | 3 |
| Status | Planning |
| Created | 2026-02-15 |

## Goal

Make sprint execution resilient: resume from checkpoints after interruption, retry failed steps, and cancel gracefully.

## Interface Contract

```python
# On SprintRunner:
async def resume(self, sprint_id) -> RunResult
    # Finds last completed step, continues from next

async def cancel(self, sprint_id, reason) -> None
    # Sets sprint to blocked, records reason

# Configuration:
@dataclass
class RunConfig:
    max_retries: int = 2
    retry_delay_seconds: float = 1.0
```

## TDD Plan

1. Write tests for resume (starts from correct step)
2. Write tests for retry on transient failure
3. Write tests for max retries exceeded
4. Write tests for cancel during execution
5. Implement all

## Tasks

### Phase 1: Planning
- [ ] Review requirements

### Phase 2: Implementation
- [ ] Add resume() to SprintRunner — find last completed step, continue
- [ ] Add retry logic — configurable max_retries per step
- [ ] Add cancel() — graceful stop, block sprint with reason
- [ ] Add RunConfig for execution parameters

### Phase 3: Validation
- [ ] Write 10 tests
- [ ] Quality review

## Deliverables

- Updated src/execution/runner.py
- tests/test_pause_resume.py (10 tests)

## Acceptance Criteria

- [ ] Resume picks up from the correct step
- [ ] Retry works for transient failures
- [ ] Stops after max_retries
- [ ] Cancel preserves state (no data loss)
- [ ] 10 new tests passing

## Dependencies

- **Sprints**: Sprint 16 (core runner)
- **External**: None

## Deferred Items

- Exponential backoff on retries → future
- Checkpoint to disk for crash recovery → future
- Notification on pause/failure → integration
