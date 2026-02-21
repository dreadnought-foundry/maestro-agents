## Context Brief & Domain Knowledge

### Background

Sprint 36 established the filesystem directory as the source of truth for sprint
column placement. The `_sprint_display_column()` function ignores YAML `status:`
and uses only the physical column directory + `--done`/`--blocked` path suffixes.

This makes the YAML `status:` field redundant — it can drift out of sync with
the filesystem and provides no value. Replacing it with a `history` array gives
us an append-only audit trail of column transitions without the drift risk.

### Existing Patterns to Follow

- `parse_frontmatter()` uses `yaml.safe_load` — safe for reading complex structures
- `_status_from_name()` handles `--done` and `--blocked` suffixes
- `_update_yaml()` uses regex for simple key-value updates — NOT suitable for lists
- The scanner test file has helpers `_write_sprint()`, `_write_epic()`, `_make_columns()`

### Gotchas from Prior Sprints

- Sprint 36: YAML status was already being ignored for column placement — but tests
  still checked `sprint.status` from YAML. Those tests still pass because the test
  helper writes `status:` in YAML and the fallback reads it when no path suffix exists.
- The `_update_yaml` helper does regex replacement — it cannot serialize lists/dicts.
  Use `yaml.dump` for the history array.
- `kanban.py` adapter imports from `kanban_tui.scanner` — be careful of circular imports.
  Use a lazy import wrapper.

### Kanban Numbering

Columns: `0-backlog`, `1-todo`, `2-in-progress`, `3-review`, `4-done`, `5-blocked`,
`6-abandoned`, `7-archived`.
