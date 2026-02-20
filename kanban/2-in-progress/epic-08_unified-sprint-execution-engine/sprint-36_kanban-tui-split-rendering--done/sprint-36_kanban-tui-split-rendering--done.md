---
sprint: 36
title: "Kanban TUI Split Rendering"
type: frontend
epic: 8
status: done
created: 2026-02-20T20:29:16Z
started: 2026-02-20T20:41:17Z
completed: 2026-02-20T21:24:27Z
hours: 0.7
---

# Sprint 36: Kanban TUI Split Rendering

## Goal

Render sprints in the correct kanban column based on their actual status, not their filesystem location. An epic's sprints appear across multiple columns so you can immediately see which are done, in progress, in review, or blocked — even though they all live in the same epic folder on disk.

## Problem

Currently, all sprints in an epic appear in whatever column the epic folder is in. Epic-07 is in `2-in-progress`, so sprints 25, 27, 28 (all done) still show up in "In Progress." The `--done` suffix is the only hint. This makes it impossible to see sprint progress at a glance.

## Before / After

**Before** (current):
```
│ In Progress              │ Done │
│ ▸ E-07 Production (4)    │      │
│   S-25 Executor    --done│      │
│   S-26 E2E         [todo]│      │
│   S-27 Lifecycle   --done│      │
│   S-28 Grooming    --done│      │
```

**After** (split rendering):
```
│ Todo │ In Progress        │ Review │ Done               │
│      │ ▸ E-07 Production  │        │ ▸ E-07 Production  │
│      │   S-26 E2E         │        │   S-25 Executor    │
│      │                    │        │   S-27 Lifecycle   │
│      │                    │        │   S-28 Grooming    │
```

The epic card appears in every column that has at least one sprint with that status. Each column only shows the sprints belonging to that status.

## How It Works

1. **Scanner** reads all sprints and determines their actual status from YAML frontmatter / `--done` / `--blocked` suffixes
2. **Scanner** groups sprints by status, mapping status → column:
   - `planning` → `1-todo`
   - `in-progress` → `2-in-progress`
   - `review` → `3-review`
   - `done` → `4-done`
   - `blocked` → `5-blocked`
   - `aborted` → `6-abandoned`
3. **TUI** receives per-column data where an epic may appear in multiple columns
4. **Epic card** shows sprint count for that column only: `E-07 Production (1)` in In Progress, `E-07 Production (3)` in Done
5. **Standalone sprints** (not in an epic) also placed by status

## Default Visible Columns

Update `MAIN_COLUMNS` to include Review:

```python
MAIN_COLUMNS = {"1-todo", "2-in-progress", "3-review", "4-done"}
```

## Tasks

### Phase 1: Planning
- [ ] Audit `kanban_tui/scanner.py` — understand current grouping logic
- [ ] Audit `kanban_tui/app.py` — understand how columns are populated from scanner data
- [ ] Design new scanner return format (epics split across columns)

### Phase 2: Implementation — Scanner
- [ ] Update `kanban_tui/scanner.py` to determine sprint status from YAML + suffix + column
- [ ] Map sprint status to target display column
- [ ] Return `ColumnInfo` where each column contains only the sprints that belong to that status
- [ ] Epic appears in a column's `EpicInfo` only if it has sprints with that status
- [ ] Epic sprint count reflects only the sprints shown in that column
- [ ] Update column definitions for new structure (add `3-review`, renumber `4-done` through `7-archived`)

### Phase 3: Implementation — TUI
- [ ] Update `MAIN_COLUMNS` to `{"1-todo", "2-in-progress", "3-review", "4-done"}`
- [ ] Handle epic cards appearing in multiple columns (same epic, different sprint subsets)
- [ ] Epic expand/collapse state should be shared across columns (expand E-07 in one column, expands everywhere)
- [ ] Ensure card selection and navigation still work with split epics
- [ ] Update detail panel to show correct sprint info regardless of column

### Phase 4: Validation
- [ ] Test: epic with mixed sprint statuses appears in multiple columns
- [ ] Test: epic with all sprints done only appears in Done column
- [ ] Test: standalone sprints (no epic) placed by status
- [ ] Test: expanding epic in one column expands in all columns
- [ ] Test: move action still works (updates YAML status, board refreshes)
- [ ] Test: MAIN_COLUMNS shows todo, in-progress, review, done by default
- [ ] Visual verification: run TUI against current kanban data

## Deliverables

- Updated `kanban_tui/scanner.py` — status-based sprint placement
- Updated `kanban_tui/app.py` — split epic rendering + new MAIN_COLUMNS
- Tests for split rendering logic

## Acceptance Criteria

- [ ] Sprints appear in the column matching their actual status, not their folder location
- [ ] Epic cards appear in multiple columns when their sprints have different statuses
- [ ] Each column's epic card shows only the sprints belonging to that status
- [ ] Review column is visible by default (in MAIN_COLUMNS)
- [ ] Expanding an epic in one column expands it across all columns
- [ ] Existing card actions (move, detail, expand) still work
- [ ] Current kanban data renders correctly with the new logic

## Dependencies

- Sprint 30 (Review Column — needs the `3-review` column to exist)
