---
sprint: 29
title: "KanbanAdapter"
type: backend
epic: 8
status: planning
created: 2026-02-20T19:59:05Z
started: null
completed: null
hours: null
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
- [ ] Audit `WorkflowBackend` protocol — list every method that must be implemented
- [ ] Audit `sprint_lifecycle.py` — map each filesystem operation to a protocol method
- [ ] Design state file schema for step tracking

### Phase 2: Implementation
- [ ] Create `src/adapters/kanban.py` with `KanbanAdapter` class
- [ ] Implement `create_epic()`, `get_epic()` — reads/writes `_epic.md` YAML
- [ ] Implement `create_sprint()` — creates sprint folder + file in epic or backlog
- [ ] Implement `start_sprint()` — moves to `2-in-progress`, updates YAML, creates state file, creates Step objects
- [ ] Implement `get_sprint()`, `get_step_status()` — reads from filesystem + state file
- [ ] Implement `advance_step()` — updates state file, marks step done
- [ ] Implement `complete_sprint()` — adds `--done` suffix, updates YAML with timestamp/hours
- [ ] Implement `block_sprint()` — adds `--blocked` suffix, records reason
- [ ] Implement `resume_sprint()` — removes `--blocked`, resumes from last step
- [ ] Implement sprint-to-review transition (new: moves to `3-review` column)

### Phase 3: Validation
- [ ] Port all `test_inmemory_lifecycle.py` tests to run against KanbanAdapter (same assertions, different backend)
- [ ] Verify round-trip: create → start → advance steps → complete → verify filesystem state
- [ ] Verify kanban TUI scanner still works after adapter operations
- [ ] Keep InMemoryAdapter working unchanged (used for fast unit tests)

## Deliverables

- `src/adapters/kanban.py` — KanbanAdapter implementing WorkflowBackend
- `tests/test_kanban_adapter.py` — full test coverage
- InMemoryAdapter unchanged (backwards compatible)

## Acceptance Criteria

- [ ] KanbanAdapter implements the full WorkflowBackend protocol
- [ ] `start_sprint()` moves the sprint folder to `2-in-progress` and creates steps
- [ ] `complete_sprint()` adds `--done` suffix and updates YAML with completion timestamp
- [ ] `block_sprint()` adds `--blocked` suffix with reason
- [ ] State survives process restart (filesystem-backed, not in-memory)
- [ ] All existing InMemoryAdapter tests still pass
- [ ] SprintRunner works with KanbanAdapter as a drop-in replacement

## Dependencies

- None — foundational sprint for the epic
