---
sprint: 10
title: "Lifecycle Protocol Methods"
type: backend
epic: 1
status: done
created: 2026-02-15T00:00:00Z
started: null
completed: null
hours: null
---

# Sprint 10: Lifecycle Protocol Methods

## Overview

| Field | Value |
|-------|-------|
| Sprint | 10 |
| Title | Lifecycle Protocol Methods |
| Type | backend |
| Epic | 1 |
| Status | Planning |
| Created | 2026-02-15 |

## Goal

Extend WorkflowBackend protocol with sprint execution operations and state-machine validation.

## Interface Contract (define first)

New protocol methods:
- `start_sprint(sprint_id) -> Sprint` — TODO → IN_PROGRESS, creates initial steps
- `advance_step(sprint_id, step_output=None) -> Sprint` — marks current step complete, advances to next
- `complete_sprint(sprint_id) -> Sprint` — IN_PROGRESS → DONE (only if all steps done)
- `block_sprint(sprint_id, reason) -> Sprint` — IN_PROGRESS → BLOCKED
- `get_step_status(sprint_id) -> dict` — returns current step, progress, step details

New exception:
- `InvalidTransitionError` — raised on illegal state changes

Valid transitions:
```
TODO → IN_PROGRESS (start)
IN_PROGRESS → DONE (complete, all steps done)
IN_PROGRESS → BLOCKED (block)
BLOCKED → IN_PROGRESS (resume)
```

## TDD Plan

1. Write tests for valid transitions (start, advance, complete, block)
2. Write tests for invalid transitions (complete before start, etc.)
3. Write tests for InvalidTransitionError
4. Implement protocol additions

## Tasks

### Phase 1: Planning
- [ ] Review requirements
- [ ] Design state machine

### Phase 2: Implementation
- [ ] Add 5 new methods to WorkflowBackend protocol in interface.py
- [ ] Define InvalidTransitionError in src/workflow/exceptions.py
- [ ] Define valid state transitions as data

### Phase 3: Validation
- [ ] Write 15 tests for transition validation
- [ ] Quality review

## Deliverables

- Updated src/workflow/interface.py
- New src/workflow/exceptions.py
- tests/test_lifecycle_protocol.py (15 tests)

## Acceptance Criteria

- [ ] Protocol defines all 5 new methods with correct signatures
- [ ] InvalidTransitionError is descriptive (includes from/to states)
- [ ] Transition rules are defined as data, not hardcoded logic
- [ ] 15 new tests passing

## Dependencies

- **Sprints**: Sprint 09 (Step model)
- **External**: None

## Deferred Items

- Unblock/resume operation → could be explicit method or reuse start_sprint
- Sprint rollback (undo last step) → future enhancement
