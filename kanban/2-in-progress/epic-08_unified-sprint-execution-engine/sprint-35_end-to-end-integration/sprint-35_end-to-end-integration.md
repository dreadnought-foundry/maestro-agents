---
sprint: 35
title: "End-to-End Integration"
type: integration
epic: 8
status: planning
created: 2026-02-20T19:59:05Z
started: null
completed: null
hours: null
---

# Sprint 35: End-to-End Integration

## Goal

Wire everything together and verify the full lifecycle works end-to-end. Update all user-facing skills to use the unified engine. Delete `sprint_lifecycle.py`.

## User Workflow (Final)

```
/sprint-start 36
  → KanbanAdapter moves sprint to 2-in-progress
  → PLAN phase: PlanningAgent produces artifacts
  → TDD phase: writes failing tests
  → BUILD phase: agents implement (parallel if team plan says so)
  → VALIDATE phase: full test suite + service checks + acceptance criteria
  → Sprint moves to 3-review
  → (user sees it on the board)

/sprint-complete 36  (or /sprint-reject 36 "reason")
  → COMPLETE phase: postmortem, quality report, deferred items
  → Sprint moves to 4-done
```

## Tasks

### Phase 1: Planning
- [ ] Audit all skill templates referencing sprint_lifecycle.py
- [ ] Plan migration path for existing kanban data (column renumbering)

### Phase 2: Implementation
- [ ] Update `/sprint-start` skill to call runner.run() with KanbanAdapter
- [ ] Update `/sprint-complete` skill to call KanbanAdapter.complete_sprint()
- [ ] Create `/sprint-reject` skill
- [ ] Update CLI to use KanbanAdapter by default, InMemoryAdapter with `--mock`
- [ ] Update `run_sprint()` convenience function with phase-based defaults
- [ ] Delete `scripts/sprint_lifecycle.py`
- [ ] Update Makefile (remove lifecycle script references)
- [ ] Migrate existing kanban data to new column structure

### Phase 3: Validation
- [ ] E2E test: full lifecycle with mock agents (fast)
- [ ] E2E test: full lifecycle with real ClaudeCodeExecutor (slow, --run-slow)
- [ ] E2E test: rejection flow — reject → re-execute → complete
- [ ] Verify kanban TUI shows correct state at each phase
- [ ] Verify all existing tests still pass
- [ ] Run a real sprint through the system as final acceptance

## Deliverables

- Updated skill templates (sprint-start, sprint-complete, sprint-reject)
- Updated CLI with KanbanAdapter default
- `scripts/sprint_lifecycle.py` deleted
- E2E integration tests
- Migrated kanban data

## Acceptance Criteria

- [ ] `/sprint-start` triggers full automated execution through VALIDATE
- [ ] Sprint appears in Review column when automation completes
- [ ] `/sprint-complete` generates completion artifacts and moves to Done
- [ ] `/sprint-reject` moves to In Progress with feedback
- [ ] `sprint_lifecycle.py` is deleted
- [ ] All existing tests pass
- [ ] Kanban TUI shows correct state throughout lifecycle
- [ ] A real sprint has been successfully run through the full system

## Dependencies

- Sprints 29–34 (all components must be built)
