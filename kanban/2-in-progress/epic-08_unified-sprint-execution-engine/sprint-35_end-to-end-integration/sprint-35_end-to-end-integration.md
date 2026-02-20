---
sprint: 35
title: "End-to-End Integration"
type: integration
epic: 8
status: in-progress
created: 2026-02-20T19:59:05Z
started: 2026-02-20T21:40:00Z
completed: null
hours: null
---

# Sprint 35: End-to-End Integration

## Goal

Wire everything together and verify the full lifecycle works end-to-end. The TUI board is the primary interface — no CLI commands or skill templates needed. Delete `sprint_lifecycle.py` and remove obsolete skills/commands.

## User Workflow (Final)

```
Kanban TUI → select sprint in Todo → press 's' to start
  → KanbanAdapter moves sprint to 2-in-progress
  → PLAN phase: PlanningAgent produces artifacts
  → TDD phase: writes failing tests
  → BUILD phase: agents implement (parallel if team plan says so)
  → VALIDATE phase: full test suite + service checks + acceptance criteria
  → Sprint moves to 3-review
  → (user sees it on the board)

Kanban TUI → select sprint in Review → press 'c' to complete (or 'x' to reject)
  → COMPLETE phase: postmortem, quality report, deferred items
  → Sprint moves to 4-done
  (or on reject: moves back to 2-in-progress with feedback)
```

No `/sprint-start`, `/sprint-complete`, or `/sprint-reject` CLI commands needed. Everything happens from the board.

## Tasks

### Phase 1: Cleanup
- [ ] Delete `scripts/sprint_lifecycle.py`
- [ ] Remove all skill templates that call sprint_lifecycle.py
- [ ] Remove CLI subcommands that duplicate the engine (start, complete, reject, block, resume, abort)
- [ ] Update Makefile (remove lifecycle script references)
- [ ] Update any documentation referencing old commands

### Phase 2: Wire TUI → Engine
- [ ] TUI `s` key on Todo sprint → calls `runner.run()` with KanbanAdapter
- [ ] TUI `c` key on Review sprint → calls KanbanAdapter.complete_sprint() + ArtifactGenerator
- [ ] TUI `x` key on Review sprint → prompts for reason, calls KanbanAdapter.reject_sprint()
- [ ] Update `run_sprint()` convenience function with phase-based defaults
- [ ] CLI retains `--mock` flag for InMemoryAdapter (testing only)

### Phase 3: Data Migration
- [ ] Migrate existing kanban data to new column structure (3-review, renumbered columns)
- [ ] Verify split rendering shows sprints in correct columns

### Phase 4: Validation
- [ ] E2E test: full lifecycle with mock agents (fast)
- [ ] E2E test: full lifecycle with real ClaudeCodeExecutor (slow, --run-slow)
- [ ] E2E test: rejection flow — reject → re-execute → complete
- [ ] Verify kanban TUI shows correct state at each phase
- [ ] Verify all existing tests still pass
- [ ] Run a real sprint through the system as final acceptance

## Deliverables

- `scripts/sprint_lifecycle.py` deleted
- Obsolete skill templates removed
- TUI wired to unified engine (start, complete, reject actions)
- E2E integration tests
- Migrated kanban data

## Acceptance Criteria

- [ ] TUI `s` key triggers full automated execution through VALIDATE
- [ ] Sprint appears in Review column when automation completes
- [ ] TUI `c` key generates completion artifacts and moves to Done
- [ ] TUI `x` key moves to In Progress with feedback
- [ ] `sprint_lifecycle.py` is deleted
- [ ] No skill templates reference lifecycle commands
- [ ] All existing tests pass
- [ ] Kanban TUI shows correct state throughout lifecycle
- [ ] A real sprint has been successfully run through the full system

## Dependencies

- Sprints 29–34 (all components must be built)
