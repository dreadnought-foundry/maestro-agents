---
epic: 1
title: "Sprint Lifecycle Operations"
status: done
created: 2026-02-15
started: null
completed: null
---

# Epic 01: Sprint Lifecycle Operations

## Overview

Extend the WorkflowBackend protocol and models to support sprint execution with state-machine operations and step-level progress tracking.

## Why This Matters

Phase 1 can create and read sprints. This epic adds the ability to *run* them — start, advance through steps, block on issues, and complete. This is the foundation everything in Phase 2 depends on.

## Interface Contract

New protocol methods on `WorkflowBackend`:
```python
async def start_sprint(self, sprint_id: str) -> Sprint
async def advance_step(self, sprint_id: str, step_output: dict | None = None) -> Sprint
async def complete_sprint(self, sprint_id: str) -> Sprint
async def block_sprint(self, sprint_id: str, reason: str) -> Sprint
async def get_step_status(self, sprint_id: str) -> dict
```

New models:
- `StepStatus` enum: PENDING, IN_PROGRESS, COMPLETED, FAILED, SKIPPED
- `Step` dataclass: id, name, status, agent, output, started_at, completed_at
- `SprintTransition`: from_status, to_status, timestamp, reason (audit trail)

## Sprints

| Sprint | Title | Status |
|--------|-------|--------|
| 09 | Step Models and Status Tracking | planned |
| 10 | Lifecycle Protocol Methods | planned |
| 11 | InMemory Lifecycle Implementation | planned |

## Success Criteria

- All state transitions validated (can't complete a sprint that hasn't started)
- Step advancement tracks output and timing
- `InvalidTransitionError` raised on illegal state changes
- 52 new tests passing

## Deferred Items

- MaestroAdapter lifecycle implementation → could be Sprint 22+ or done alongside s-11
- Step-level timing analytics → feeds into a future analytics epic
- Transition audit log querying → future reporting enhancement

## Notes

Created: 2026-02-15
