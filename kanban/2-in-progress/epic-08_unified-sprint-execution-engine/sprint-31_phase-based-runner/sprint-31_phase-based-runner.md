---
sprint: 31
title: "Phase-Based Runner"
type: backend
epic: 8
status: in-progress
created: 2026-02-20T19:59:05Z
started: 2026-02-20T20:20:54Z
completed: null
hours: null
---

# Sprint 31: Phase-Based Runner

## Goal

Refactor SprintRunner from a flat sequential step loop into a phase-based execution model with 6 distinct phases. Each phase has its own entry/exit gates, agent types, and artifact outputs.

## Problem

The current runner treats all steps the same: iterate through a list, dispatch to an agent, check result. There's no concept of "plan first, then test, then build." This means no planning phase, no TDD phase, no validation distinct from test-running, no review checkpoint, and no structured completion.

## Phases

```
PLAN → TDD → BUILD → VALIDATE → REVIEW → COMPLETE
```

| Phase | Agent | Output | Gate |
|-------|-------|--------|------|
| PLAN | PlanningAgent | Contracts, team plan, TDD strategy, coding strategy, context brief | All artifacts present and non-empty |
| TDD | ProductEngineer (test mode) | Failing test files | Tests exist and all fail |
| BUILD | ProductEngineer(s) | Implementation code | All TDD tests pass |
| VALIDATE | TestRunner + ValidationAgent | Validation report | Passes threshold |
| REVIEW | None (human) | — | Human runs `/sprint-complete` or `/sprint-reject` |
| COMPLETE | System | Postmortem, quality report, deferred items | Artifacts written |

## Tasks

### Phase 1: Planning
- [ ] Design Phase enum and PhaseConfig dataclass
- [ ] Design PhaseResult (success, artifacts_produced, gate_passed)
- [ ] Map current RunResult fields to phase-aware equivalents

### Phase 2: Implementation
- [ ] Create `src/execution/phases.py` — Phase enum, PhaseConfig, PhaseResult
- [ ] Refactor `SprintRunner.run()` to iterate over phases instead of flat steps
- [ ] Each phase gets its own `_execute_phase()` method
- [ ] Implement phase gates — conditions that must be met before advancing
- [ ] Implement phase-specific artifact generation (planning artifacts after PLAN, completion artifacts after COMPLETE)
- [ ] Preserve backwards compatibility: if no phases configured, run as flat steps (existing behavior)
- [ ] Add phase tracking to state file (current_phase, phase_results)
- [ ] Add phase-aware progress callbacks
- [ ] Runner stops after VALIDATE and moves sprint to Review (doesn't auto-complete)

### Phase 3: Validation
- [ ] Test phase progression: PLAN → TDD → BUILD → VALIDATE stops at REVIEW
- [ ] Test phase gate failure blocks advancement
- [ ] Test backwards compatibility: old-style sprints still work
- [ ] Test phase-aware progress callbacks report correct phase
- [ ] Test resume from failed phase (re-enter at the failed phase, not from scratch)

## Deliverables

- `src/execution/phases.py` — Phase definitions and configuration
- Refactored `src/execution/runner.py` — phase-based execution loop
- Updated state file schema with phase tracking
- All existing tests still pass (backwards compatible)

## Acceptance Criteria

- [ ] Runner executes phases in order: PLAN → TDD → BUILD → VALIDATE
- [ ] After VALIDATE, sprint moves to Review column (stops, doesn't auto-complete)
- [ ] Each phase has entry/exit gates that must pass before advancing
- [ ] Phase failure blocks the sprint at the failed phase
- [ ] Old-style sprints (no phases configured) still work as before
- [ ] Phase tracking persists in state file for resume capability

## Dependencies

- Sprint 29 (KanbanAdapter — for review column transition)
