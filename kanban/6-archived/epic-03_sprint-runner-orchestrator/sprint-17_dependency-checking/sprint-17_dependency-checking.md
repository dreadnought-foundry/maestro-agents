---
sprint: 17
title: "Dependency Checking and Step Ordering"
type: backend
epic: 3
status: done
created: 2026-02-15T00:00:00Z
started: null
completed: null
hours: null
---

# Sprint 17: Dependency Checking and Step Ordering

## Overview

| Field | Value |
|-------|-------|
| Sprint | 17 |
| Title | Dependency Checking and Step Ordering |
| Type | backend |
| Epic | 3 |
| Status | Planning |
| Created | 2026-02-15 |

## Goal

Ensure sprints and steps execute in the correct order by validating dependencies before execution.

## Interface Contract

```python
class DependencyNotMetError(Exception):
    def __init__(self, sprint_id, unmet_dependencies: list[str])

async def validate_sprint_dependencies(sprint_id, backend) -> list[str]
# Returns list of unmet dependency sprint IDs, empty if all met

async def validate_step_order(sprint, current_step) -> bool
# Returns True if step can execute given completed steps
```

## TDD Plan

1. Write tests for sprint with no dependencies (always valid)
2. Write tests for sprint with met dependencies
3. Write tests for sprint with unmet dependencies
4. Write tests for step ordering within a sprint
5. Implement validation functions
6. Integrate into SprintRunner.run()

## Tasks

### Phase 1: Planning
- [ ] Review requirements

### Phase 2: Implementation
- [ ] Create DependencyNotMetError in src/workflow/exceptions.py
- [ ] Create dependency validation in src/execution/dependencies.py
- [ ] Integrate into runner — check before starting sprint
- [ ] Add step-level dependency support

### Phase 3: Validation
- [ ] Write 10 tests
- [ ] Quality review

## Deliverables

- src/execution/dependencies.py
- Updated src/execution/runner.py
- tests/test_dependencies.py (10 tests)

## Acceptance Criteria

- [ ] Runner refuses to start sprint with unmet dependencies
- [ ] DependencyNotMetError lists which dependencies are missing
- [ ] Step ordering enforced within sprint
- [ ] 10 new tests passing

## Dependencies

- **Sprints**: Sprint 16 (core runner)
- **External**: None

## Deferred Items

- Circular dependency detection → future validation
- Auto-resolution of dependencies (run dependent sprint first) → future
