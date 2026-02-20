---
sprint: 33
title: "Parallel Execution and Step Dependencies"
type: backend
epic: 8
status: planning
created: 2026-02-20T19:59:05Z
started: null
completed: null
hours: null
---

# Sprint 33: Parallel Execution & Step Dependencies

## Goal

Enable the runner to execute multiple agents concurrently within a phase. Steps declare dependencies on other steps, forming a DAG. The runner schedules steps whose dependencies are met and runs them in parallel.

## Problem

The current runner is strictly sequential. If a sprint has "build backend" and "build frontend" as separate steps, they run one after the other even though they're independent. This doubles execution time unnecessarily.

## Approach

### Step Dependencies

Add `depends_on` to Step model:

```python
@dataclass
class Step:
    id: str
    name: str
    depends_on: list[str] = field(default_factory=list)  # Step IDs
```

### Execution DAG

```
build_backend ──┐
                ├──→ run_tests ──→ review
build_frontend ─┘
```

Steps with no unmet dependencies run concurrently via `asyncio.gather()`.

### Team Plan Drives Composition

The team plan artifact (from Sprint 32) specifies parallelism per phase:
- PLAN: sequential (one PlanningAgent)
- TDD: parallel (backend tests + frontend tests)
- BUILD: parallel (backend + frontend engineers)
- VALIDATE: configurable
- REVIEW: N/A (human)
- COMPLETE: sequential

## Tasks

### Phase 1: Planning
- [ ] Design `depends_on` field on Step model
- [ ] Design DAG scheduler (topological sort + concurrent execution)
- [ ] Determine how team plan translates to step dependencies

### Phase 2: Implementation
- [ ] Add `depends_on: list[str]` to Step dataclass
- [ ] Create `src/execution/scheduler.py` — DAG-based step scheduler
- [ ] Implement `Scheduler.get_ready_steps()` — returns steps with all deps met
- [ ] Implement `Scheduler.mark_complete(step_id)` — updates dependency tracking
- [ ] Implement concurrent execution: `asyncio.gather(*[execute(step) for step in ready_steps])`
- [ ] Handle partial failure: if one parallel step fails, wait for others, then block
- [ ] Update both adapters to support concurrent step advancement
- [ ] Team plan → step dependencies: parse PlanningAgent output into Step.depends_on

### Phase 3: Validation
- [ ] Test DAG with no dependencies (all steps run in parallel)
- [ ] Test DAG with linear dependencies (sequential, same as today)
- [ ] Test diamond: A→C, B→C (A and B parallel, C waits for both)
- [ ] Test partial failure in parallel steps
- [ ] Test backwards compatibility: steps without `depends_on` run sequentially
- [ ] Benchmark: parallel faster than sequential for independent steps

## Deliverables

- `src/execution/scheduler.py` — DAG scheduler
- Updated Step model with `depends_on`
- Updated SprintRunner with concurrent step execution
- `tests/test_scheduler.py` — DAG logic tests

## Acceptance Criteria

- [ ] Independent steps within a phase run concurrently
- [ ] Dependent steps wait for their dependencies to complete
- [ ] Partial failure blocks the sprint correctly
- [ ] Team plan artifact drives step dependency configuration
- [ ] Steps without `depends_on` default to sequential (backwards compatible)

## Dependencies

- Sprint 31 (Phase-Based Runner — phases provide the grouping)
