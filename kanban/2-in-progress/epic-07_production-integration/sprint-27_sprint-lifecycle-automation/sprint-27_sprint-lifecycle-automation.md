---
sprint: 27
title: "Sprint Lifecycle Automation"
type: infrastructure
epic: 7
status: planning
created: 2026-02-15T00:00:00Z
started: null
completed: null
hours: null
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
- [ ] Create `scripts/sprint_lifecycle.py` with argparse CLI
- [ ] Implement `find_sprint()` — locate a sprint by number across all columns
- [ ] Implement `find_epic()` — locate an epic by number across all columns
- [ ] Implement YAML frontmatter read/update helpers
- [ ] Implement folder move helper (handles epic-grouped sprints)

### Phase 2: Sprint Commands
- [ ] `create-sprint <num> <title> [--type TYPE] [--epic NUM]` — create sprint file/folder
- [ ] `start-sprint <num>` — move to 2-in-progress, update YAML, create state file
- [ ] `complete-sprint <num>` — move to 3-done with `--done` suffix, update YAML
- [ ] `block-sprint <num> <reason>` — move to 4-blocked with `--blocked` suffix
- [ ] `resume-sprint <num>` — move back to 2-in-progress, remove `--blocked` suffix
- [ ] `abort-sprint <num> [reason]` — move to 5-abandoned with `--aborted` suffix

### Phase 3: Epic Commands
- [ ] `create-epic <num> <title>` — create epic folder with `_epic.md`
- [ ] `start-epic <num>` — move epic to 2-in-progress, update YAML
- [ ] `complete-epic <num>` — move to 3-done (only if all sprints are done)
- [ ] `archive-epic <num>` — move to 6-archived

### Phase 4: Validation
- [ ] Test each command against the real kanban directory
- [ ] Verify all workflow skills work end-to-end via the script
- [ ] Verify state files are created/updated correctly
- [ ] Verify edge cases: standalone sprints, nested sprints, already-moved items

## Deliverables

- `scripts/sprint_lifecycle.py` — full CLI with all commands
- All workflow skills (`/sprint-start`, `/epic-new`, etc.) work without manual intervention

## Acceptance Criteria

- [ ] `python3 scripts/sprint_lifecycle.py start-sprint 25` works
- [ ] `python3 scripts/sprint_lifecycle.py create-epic 8 "New Epic"` works
- [ ] All commands handle the `kanban/` folder structure correctly
- [ ] State files (`.claude/sprint-N-state.json`) created on start
- [ ] YAML frontmatter updated on every state transition
- [ ] Epic-grouped sprints move with their epic folder
- [ ] Clear error messages for invalid operations (sprint not found, already started, etc.)
- [ ] Existing kanban TUI scanner still works after moves

## Dependencies

- **Sprints**: None — standalone infrastructure
- **Reference**: `docs/reference/maestro-v1/sprint_lifecycle.py`
