---
sprint: 30
title: "Review Column and Rejection Flow"
type: infrastructure
epic: 8
status: done
created: 2026-02-20T19:59:05Z
started: 2026-02-20T20:20:45Z
completed: 2026-02-20T20:39:05Z
hours: 0.3
---

# Sprint 30: Review Column & Rejection Flow

## Goal

Add a `3-review` column to the kanban board for human sign-off. When automated phases complete successfully, the sprint moves to Review instead of Done. The user reviews from the kanban TUI — complete or reject directly from the board. No CLI commands needed.

## Problem

Currently there's no human checkpoint between "agents finished" and "sprint done." The user has no visible indicator that work is ready for review, and no structured way to reject and send work back with feedback.

## Column Restructure

```
Current:          New:
0-backlog         0-backlog
1-todo            1-todo
2-in-progress     2-in-progress
3-done            3-review        ← NEW
4-blocked         4-done          (was 3)
5-abandoned       5-blocked       (was 4)
6-archived        6-abandoned     (was 5)
                  7-archived      (was 6)
```

## Kanban TUI Actions

When a sprint is in the **Review** column, the TUI shows context-aware actions:

```
┌─────────────────────────────────────────┐
│  3-review                               │
│  ┌───────────────────────────────────┐  │
│  │ S-29 KanbanAdapter          [BE]  │  │
│  │                                   │  │
│  │  [c] Complete   [x] Reject        │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

| Key | Action | What Happens |
|-----|--------|-------------|
| **c** | Complete | Runs completion flow (generate artifacts, move to Done) |
| **x** | Reject | Opens input modal for rejection reason, moves back to In Progress |
| **d** | Detail | Shows draft quality report + planning artifacts for review |

These actions are **only available in the Review column**. In other columns, the existing move/detail actions apply.

## Rejection Flow

```
User presses [x] on a sprint in Review column
  → Modal: "Rejection reason: _______________"
  → Sprint moves from 3-review back to 2-in-progress
  → Rejection reason stored in YAML frontmatter and state file
  → On next run, agents see rejection feedback as context
  → Runner re-executes from the appropriate phase
```

## Tasks

### Phase 1: Planning
- [x] Audit all code referencing column names/numbers (kanban_tui/, src/kanban/, sprint_lifecycle.py)
- [x] Design rejection state model (YAML fields, state file fields)
- [x] Design how rejection feedback flows into agent context
- [x] Design TUI action bindings for Review column

### Phase 2: Implementation — Column & Backend
- [x] Rename kanban columns on disk: `3-done` → `4-done`, `4-blocked` → `5-blocked`, `5-abandoned` → `6-abandoned`, `6-archived` → `7-archived`
- [x] Create `3-review` column directory
- [x] Update `KanbanAdapter` column constants and mapping
- [x] Update `src/kanban/scanner.py` for new column structure
- [x] Add `REVIEW` to `SprintStatus` enum in workflow models
- [x] Add `move_to_review()` method on KanbanAdapter
- [x] Add `reject_sprint(sprint_id, reason)` method on KanbanAdapter and InMemoryAdapter
- [x] Implement rejection: moves from review to in-progress, stores feedback
- [x] Update SprintRunner: after successful validation, call `move_to_review()` instead of `complete_sprint()`
- [x] Generate draft quality report when entering Review

### Phase 3: Implementation — TUI Actions
- [x] Update `kanban_tui/scanner.py` column definitions for new structure
- [x] Add `c` key binding: Complete — only active when selected card is in Review column
- [x] Add `x` key binding: Reject — only active when selected card is in Review column
- [x] Create `RejectModal` screen — text input for rejection reason
- [x] Complete action: calls KanbanAdapter.complete_sprint() + ArtifactGenerator
- [x] Reject action: calls KanbanAdapter.reject_sprint() with reason from modal
- [x] Show Review column in default view (alongside todo, in-progress, done)
- [x] Detail panel (`d`) shows draft quality report for Review cards
- [x] Refresh board after complete/reject actions

### Phase 4: Validation
- [x] Test column rename doesn't break existing archived sprints
- [x] Test review → complete flow (from TUI action)
- [x] Test review → reject → re-execute → review flow
- [x] Test rejection feedback appears in agent StepContext
- [x] Kanban TUI displays Review column correctly
- [x] TUI actions only appear for sprints in Review column
- [x] `/sprint-complete` and `/sprint-reject` CLI skills still work as fallback

## Deliverables

- Restructured kanban columns (3-review added)
- `reject_sprint()` on both adapters
- Updated SprintRunner with review checkpoint
- Kanban TUI with Complete/Reject actions in Review column
- `/sprint-reject` skill (CLI fallback)
- Draft artifact generation on review entry

## Acceptance Criteria

- [ ] `3-review` column exists and is visible in kanban TUI
- [ ] Successful sprint execution moves sprint to Review, not Done
- [ ] User can press `c` on a Review card to complete (generates artifacts, moves to Done)
- [ ] User can press `x` on a Review card to reject (prompts for reason, moves back to In Progress)
- [ ] Complete/reject actions are only available in the Review column
- [ ] Rejection feedback is available to agents on re-execution
- [ ] Detail panel shows draft quality report for Review cards
- [ ] `/sprint-complete` and `/sprint-reject` CLI commands still work as alternatives
- [ ] All existing archived sprints remain accessible after column renumber

## Dependencies

- Sprint 29 (KanbanAdapter)
