---
sprint: 27
title: "Sprint Lifecycle Automation"
type: infrastructure
epic: 7
status: done
created: 2026-02-15T00:00:00Z
started: 2026-02-20T19:27:53Z
completed: 2026-02-20T19:28:01Z
hours: 0.0
---

# Sprint 27: Sprint Lifecycle Automation

## Overview

| Field | Value |
|-------|-------|
| Sprint | 27 |
| Title | Sprint Lifecycle Automation |
| Type | infrastructure |
| Epic | 7 |
| Status | Planning |
| Created | 2026-02-15 |

## Goal

Build `scripts/sprint_lifecycle.py` — the CLI that backs all workflow skills (`/sprint-start`, `/sprint-complete`, `/epic-new`, `/epic-start`, etc.). Every skill currently references this script but it doesn't exist, so all lifecycle operations are done manually. This sprint closes that gap.

## Problem

The project has ~20 workflow skills defined as prompt templates (in user settings). Each skill expands into instructions like:

```bash
python3 scripts/sprint_lifecycle.py start-sprint 25
```

But `scripts/sprint_lifecycle.py` doesn't exist. There's no `scripts/` directory at all. A reference implementation exists at `docs/reference/maestro-v1/sprint_lifecycle.py` but it targets `docs/sprints/` paths — this project uses `kanban/` as its board root.

## Approach

Adapt the reference implementation to work with this project's `kanban/` folder structure:

- **Board root**: `kanban/` (not `docs/sprints/`)
- **Columns**: `0-backlog`, `1-todo`, `2-in-progress`, `3-done`, `4-blocked`, `5-abandoned`, `6-archived`
- **Epic folders**: `epic-{NN}_{slug}/` containing `_epic.md` and sprint subfolders
- **Sprint folders**: `sprint-{NN}_{slug}/` containing `sprint-{NN}_{slug}.md`
- **Standalone sprints**: flat `.md` files directly in a column (no subfolder)
- **State files**: `.claude/sprint-{N}-state.json`

## Tasks

### Phase 1: Core CLI Framework
- [x] Create `scripts/sprint_lifecycle.py` with argparse CLI
- [x] Implement `find_sprint()` — locate a sprint by number across all columns
- [x] Implement `find_epic()` — locate an epic by number across all columns
- [x] Implement YAML frontmatter read/update helpers
- [x] Implement folder move helper (handles epic-grouped sprints)

### Phase 2: Sprint Commands
- [x] `create-sprint <num> <title> [--type TYPE] [--epic NUM]` — create sprint file/folder
- [x] `start-sprint <num>` — move to 2-in-progress, update YAML, create state file
- [x] `complete-sprint <num>` — move to 3-done with `--done` suffix, update YAML
- [x] `block-sprint <num> <reason>` — add `--blocked` suffix, update YAML
- [x] `resume-sprint <num>` — remove `--blocked` suffix, resume in-progress
- [x] `abort-sprint <num> [reason]` — add `--aborted` suffix, update YAML

### Phase 3: Epic Commands
- [x] `create-epic <num> <title>` — create epic folder with `_epic.md`
- [x] `start-epic <num>` — move epic to 2-in-progress, update YAML
- [x] `complete-epic <num>` — move to 3-done (only if all sprints are done/aborted)
- [x] `archive-epic <num>` — move to 6-archived

### Phase 4: Validation
- [x] Test each command against the real kanban directory
- [x] Verify state files are created/updated correctly
- [x] Verify edge cases: standalone sprints, nested sprints, epic-nested starts
- [x] Verify state guards: block/complete/resume/abort invalid transitions
- [x] Verify kanban TUI scanner still works after moves

## Deliverables

- `scripts/sprint_lifecycle.py` — full CLI with all commands
- All workflow skills (`/sprint-start`, `/epic-new`, etc.) work without manual intervention

## Acceptance Criteria

- [x] `python3 scripts/sprint_lifecycle.py start-sprint 25` works
- [x] `python3 scripts/sprint_lifecycle.py create-epic 8 "New Epic"` works
- [x] All commands handle the `kanban/` folder structure correctly
- [x] State files (`.claude/sprint-N-state.json`) created on start
- [x] YAML frontmatter updated on every state transition
- [x] Epic-grouped sprints move with their epic folder
- [x] Clear error messages for invalid operations (sprint not found, already started, etc.)
- [x] Existing kanban TUI scanner still works after moves

## Dependencies

- **Sprints**: None — standalone infrastructure
- **Reference**: `docs/reference/maestro-v1/sprint_lifecycle.py`
