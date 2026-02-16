---
sprint: 8
title: "Core Sprint Runner"
type: backend
epic: 3
status: planning
created: 2026-02-15T00:00:00Z
started: null
completed: null
hours: null
---

# Sprint 08: Core Sprint Runner

## Overview

| Field | Value |
|-------|-------|
| Sprint | 8 |
| Title | Core Sprint Runner |
| Type | backend |
| Epic | 3 |
| Status | Planning |
| Created | 2026-02-15 |

## Goal

Build the SprintRunner class that orchestrates end-to-end sprint execution.

## Interface Contract (define first)

```python
class SprintRunner:
    def __init__(self, backend, agent_registry, hooks=None)
    async def run(self, sprint_id, on_progress=None) -> RunResult
    async def resume(self, sprint_id) -> RunResult
    async def cancel(self, sprint_id, reason) -> None

@dataclass
class RunResult:
    sprint_id: str
    success: bool
    steps_completed: int
    steps_total: int
    agent_results: list[AgentResult]
    deferred_items: list[str]
    duration_seconds: float
```

## TDD Plan

1. Write tests for run() with mock agents (happy path)
2. Write tests for step dispatch (correct agent called per step)
3. Write tests for progress callbacks
4. Write tests for failure handling (agent returns success=False)
5. Implement runner

## Tasks

### Phase 1: Planning
- [ ] Review requirements

### Phase 2: Implementation
- [ ] Create SprintRunner in src/execution/runner.py
- [ ] Implement run() — start sprint, iterate steps, dispatch to agents, advance
- [ ] Implement progress callbacks (on_progress called after each step)
- [ ] Aggregate deferred_items from all AgentResults into RunResult
- [ ] Handle agent failures (stop run, set sprint to blocked)

### Phase 3: Validation
- [ ] Write 12 tests using mock agents and InMemoryAdapter
- [ ] Quality review

## Deliverables

- New src/execution/ package
- src/execution/runner.py
- tests/test_sprint_runner.py (12 tests)

## Acceptance Criteria

- [ ] Runs a sprint from start to completion with mock agents
- [ ] Correct agent dispatched per step type
- [ ] Deferred items aggregated in RunResult
- [ ] Failed step blocks the sprint
- [ ] 12 new tests passing

## Dependencies

- **Sprints**: Sprint 3 (InMemory lifecycle), Sprint 4 (agent infrastructure)
- **External**: None

## Deferred Items

- Parallel step execution → future optimization
- Cost tracking (API tokens per run) → analytics
- Real-time progress streaming → UI integration
