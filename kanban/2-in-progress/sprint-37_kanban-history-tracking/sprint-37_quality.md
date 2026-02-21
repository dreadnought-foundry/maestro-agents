# Quality Report — Sprint 37: Kanban History Tracking

## Test Results
- 589 tests passing, 0 failures, 2 skipped
- 7 new tests in `TestHistoryParsing` class (all passing)
- All real kanban sanity tests pass against live data

## Coverage
- `write_history_entry()`: append, multi-append, status removal
- `_parse_sprint_md()`: path suffix derivation, YAML fallback, history read
- `SprintInfo.history`: populated from YAML, defaults to empty list
- Existing scanner tests: all 50 unchanged tests still pass

## Files Changed
### Created
- None (all modifications to existing files)

### Modified
- `kanban_tui/scanner.py` (added history field, write_history_entry, path-based status)
- `kanban_tui/app.py` (added write_history_entry import and calls)
- `src/adapters/kanban.py` (replaced status= writes with _write_history calls)
- `tests/test_kanban_tui_scanner.py` (added 7 history tests)
- 37 kanban .md files (stripped status: lines)
