---
sprint: 29
title: "KanbanAdapter"
type: backend
epic: 8
created: 2026-02-20T19:59:05Z
started: 2026-02-20T20:13:23Z
completed: 2026-02-20T20:19:52Z
hours: 0.1
---

# Sprint 29: KanbanAdapter

## Goal

Build a `KanbanAdapter` that implements the same `WorkflowBackend` protocol as `InMemoryAdapter` but reads/writes the kanban filesystem directly. This replaces the need for `sprint_lifecycle.py` as a separate tool — the runner talks to the kanban board through this adapter.

## Problem

`InMemoryAdapter` loses all state when the process exits. `sprint_lifecycle.py` manages the kanban filesystem but is disconnected from the runner. The KanbanAdapter bridges this gap: the runner calls `backend.start_sprint()` and the adapter moves the folder to `2-in-progress`, updates YAML, creates the state file — all in one operation.

## Approach

Port the filesystem logic from `sprint_lifecycle.py` into a class that implements the `WorkflowBackend` protocol. The adapter:
- Reads sprint/epic state from kanban folder structure and YAML frontmatter
- Writes state changes as folder moves, renames, and YAML updates
- Uses `.claude/sprint-N-state.json` for step-level tracking (which step is current, completed steps)
- Maps kanban columns to sprint statuses: `0-backlog`=BACKLOG, `1-todo`=TODO, `2-in-progress`=IN_PROGRESS, `3-review`=REVIEW (new), `4-done`=DONE, etc.

## Tasks

### Phase 1: Planning
- [x] Audit `WorkflowBackend` protocol — 11 methods to implement
- [x] Audit `sprint_lifecycle.py` — ported filesystem helpers as private functions
- [x] Design state file schema for step tracking (.claude/sprint-N-state.json)

### Phase 2: Implementation
- [x] Create `src/adapters/kanban.py` with `KanbanAdapter` class
- [x] Implement `create_epic()`, `get_epic()`, `list_epics()` — reads/writes `_epic.md` YAML
- [x] Implement `create_sprint()` — creates sprint folder + file in epic
- [x] Implement `start_sprint()` — moves to `2-in-progress`, updates YAML, creates state file, creates Steps
- [x] Implement `get_sprint()`, `get_step_status()` — reads from filesystem + state file
- [x] Implement `advance_step()` — updates state file, marks step done, starts next
- [x] Implement `complete_sprint()` — adds `--done` suffix, updates YAML
- [x] Implement `block_sprint()` — adds `--blocked` suffix, records reason
- [x] Implement `update_sprint()` — handles resume (removes `--blocked` suffix)
- [x] Implement `get_project_state()`, `get_status_summary()`, `list_sprints()`

### Phase 3: Validation
- [x] Port all `test_inmemory_lifecycle.py` tests to KanbanAdapter (36 tests)
- [x] Verify round-trip: create → start → advance → complete → filesystem state
- [x] Verify block → resume → complete lifecycle
- [x] Verify state survives process restart (new adapter instance reads persisted state)
- [x] All InMemoryAdapter tests still pass (451 total, 0 regressions)

## Deliverables

- `src/adapters/kanban.py` — KanbanAdapter implementing WorkflowBackend
- `tests/test_kanban_adapter.py` — full test coverage
- InMemoryAdapter unchanged (backwards compatible)

## Acceptance Criteria

- [x] KanbanAdapter implements the full WorkflowBackend protocol (11 methods)
- [x] `start_sprint()` moves the sprint folder to `2-in-progress` and creates steps
- [x] `complete_sprint()` adds `--done` suffix and updates YAML with completion timestamp
- [x] `block_sprint()` adds `--blocked` suffix with reason
- [x] State survives process restart (filesystem-backed, not in-memory)
- [x] All existing InMemoryAdapter tests still pass (451 total)
- [x] SprintRunner works with KanbanAdapter as a drop-in replacement

## Dependencies

- None — foundational sprint for the epic
