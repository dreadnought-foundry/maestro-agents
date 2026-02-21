---
sprint: 37
title: Kanban History Tracking
type: refactor
epic: null
created: 2026-02-21 00:00:00+00:00
started: 2026-02-21 19:57:38+00:00
completed: null
history:
- column: 2-in-progress
  timestamp: '2026-02-21T19:57:38Z'
---

# Sprint 37: Kanban History Tracking

## Overview

| Field | Value |
|-------|-------|
| Sprint | 37 |
| Title | Kanban History Tracking |
| Type | refactor |
| Epic | standalone |
| Created | 2026-02-21 |

## Goal

Replace the redundant YAML `status` field with a `history` array that logs every column transition with a timestamp — useful for cycle time, lead time, and retrospectives. The filesystem directory is already the source of truth for sprint status; this sprint removes the drifting YAML `status` field and replaces it with an append-only audit trail.

## Implementation Notes

The `status` field in YAML frontmatter was redundant since sprint 36 established the filesystem directory as the source of truth for column placement. This sprint removes `status` entirely and adds a `history` array that records every column transition with an ISO timestamp. The `write_history_entry()` utility is placed in `scanner.py` so both the TUI and the backend adapter can use it without circular imports.

## Tasks

### Phase 1: Planning
- [x] Review existing scanner.py, app.py, and kanban adapter status handling
- [x] Design `write_history_entry()` API and placement

### Phase 2: Implementation
- [x] Add `history: list[dict]` field to `SprintInfo` dataclass
- [x] Add `write_history_entry()` utility to `scanner.py`
- [x] Update `_parse_sprint_md()` to derive status from path suffix, read history from YAML
- [x] Import and call `write_history_entry()` in `app.py` move/complete/reject flows
- [x] Replace `_update_yaml(path, status=...)` calls in `kanban.py` adapter with `write_history_entry()`
- [x] Strip `status:` lines from all 37 existing kanban .md files

### Phase 3: Validation
- [x] Run scanner tests — 57 passed (7 new history tests)
- [x] Run full test suite — 589 passed, 2 skipped
- [x] Verify real kanban sanity tests pass against live kanban directory

## Deliverables

- Modified `kanban_tui/scanner.py` — `history` field on `SprintInfo`, `write_history_entry()`, path-based status derivation
- Modified `kanban_tui/app.py` — history recording in MoveScreen, complete, reject flows
- Modified `src/adapters/kanban.py` — replaced 5 `status=` writes with `_write_history()` calls
- Modified `tests/test_kanban_tui_scanner.py` — 7 new tests in `TestHistoryParsing`
- Modified `kanban/**/*.md` — stripped `status:` from 37 files

## Acceptance Criteria

- [x] `SprintInfo.history` is populated from YAML frontmatter
- [x] `write_history_entry()` appends timestamped column transitions and strips `status` field
- [x] Status derived from path suffix (`--done`, `--blocked`) with YAML fallback
- [x] TUI move/complete/reject operations record history entries
- [x] Kanban adapter lifecycle methods use history instead of status writes
- [x] No `status:` lines remain in existing kanban .md files
- [x] All 589 tests pass

## Dependencies

- **Sprints**: Sprint 36 (kanban TUI split rendering — established filesystem as source of truth)
- **External**: None
