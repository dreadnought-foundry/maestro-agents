# Postmortem — Sprint 17: Dependency Checking and Step Ordering

**Result**: Success | 3/3 steps | ~20m
**Date**: 2026-02-15

## What Was Built
- `DependencyNotMetError` exception listing unmet dependency sprint IDs
- `validate_sprint_dependencies()` function checking all dependent sprints are completed
- `validate_step_order()` function ensuring steps execute in correct sequence
- Integration into SprintRunner.run() — checks dependencies before starting
- 10 tests covering no dependencies, met dependencies, unmet dependencies, and step ordering

## Lessons Learned
- Dependency validation as a separate module keeps the runner clean
- Listing specific unmet dependencies in the error message aids debugging
- Step ordering validation prevents subtle bugs from out-of-order execution

## Deferred Items
- Circular dependency detection
- Auto-resolution of dependencies
