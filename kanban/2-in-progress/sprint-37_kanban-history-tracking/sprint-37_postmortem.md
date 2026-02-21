# Postmortem — Sprint 37: Kanban History Tracking

**Result**: Success | All tasks complete | 589 tests passing
**Date**: 2026-02-21

## What Was Built
- `write_history_entry()` utility in `scanner.py` — appends timestamped column transitions to YAML frontmatter and strips the legacy `status` field
- `SprintInfo.history` field — populated from YAML frontmatter on scan
- Path-based status derivation in `_parse_sprint_md()` — uses `--done`/`--blocked` suffix first, YAML fallback for backward compatibility
- History recording in TUI `app.py` — MoveScreen, complete, and reject flows all append history entries
- Replaced all 5 `_update_yaml(path, status=...)` calls in `kanban.py` adapter with `_write_history()` calls
- Stripped `status:` from all 37 existing kanban .md files

## Key Decisions
- Placed `write_history_entry()` in `scanner.py` rather than a separate module — both the TUI and adapter already import from scanner, avoiding circular deps
- Used lazy import wrapper `_write_history()` in `kanban.py` to avoid circular import at module level
- `write_history_entry()` actively removes the `status` field when it writes — ensures clean migration rather than leaving both fields
- Used `yaml.safe_load` / `yaml.dump` for history writes (already a project dependency) rather than the regex-based `_update_yaml` helper — history is a nested structure that needs proper YAML serialization

## Lessons Learned
- Sprint process compliance matters as much as code correctness — initially skipped the standard lifecycle (folder structure, artifact files, `/sprint-start`) and had to retroactively fix
- Standalone sprints (no epic) cannot use the execution engine's `run` command — the runner unconditionally calls `get_epic(sprint.epic_id)` which fails for standalone sprints. This should be fixed in a future sprint.
- The hook system caught the sprint folder move correctly and recorded a history entry automatically

## Deferred Items
- Execution engine support for standalone sprints (runner.py line 158 assumes epic exists)
- Cycle time / lead time calculations from the history array
- History-based retrospective reports
