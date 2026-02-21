## TDD Strategy

### Test Structure

All tests in `tests/test_kanban_tui_scanner.py` under a new `TestHistoryParsing` class.

### Tests to Write

1. **test_history_read_from_yaml** — Sprint with `history:` array in YAML frontmatter → `SprintInfo.history` populated with correct entries
2. **test_empty_history_defaults_to_empty_list** — Sprint without `history:` in YAML → `sprint.history == []`
3. **test_write_history_entry_appends** — Single call appends one entry with column + timestamp
4. **test_write_history_entry_appends_multiple** — Three calls accumulate three entries in order
5. **test_write_history_entry_removes_status_field** — Calling write_history_entry on a file with `status:` removes it
6. **test_status_derived_from_done_suffix** — Sprint with `--done` suffix → `status == "done"` regardless of YAML
7. **test_status_falls_back_to_yaml_without_suffix** — Sprint without suffix → status from YAML `status:` field

### Fixtures

- Use `tmp_path` for all tests (standard pytest)
- Reuse existing `_write_sprint` and `_make_columns` helpers

### Coverage Targets

- `write_history_entry`: append, accumulate, status removal
- `_parse_sprint_md`: path derivation, YAML fallback, history read
- `SprintInfo.history`: field default, population from YAML

### Edge Cases

- File with no frontmatter → `write_history_entry` is a no-op (returns without crash)
- File with `status:` but no `history:` → status removed, history created
