## Team Plan & Agent Composition

### Agent: 1 product engineer (manual execution)

Sprint 37 is a refactor sprint — no AI agent execution needed. Single engineer
modifies 3 source files + 1 test file + bulk-edits 37 kanban .md files.

### Execution Order

1. **scanner.py** — add history field + write_history_entry utility (foundation)
2. **app.py** — wire history recording into TUI move flows (depends on #1)
3. **kanban.py** — replace status writes with history appends (depends on #1)
4. **tests** — add TestHistoryParsing, verify all existing tests still pass
5. **kanban cleanup** — strip status: lines from all existing .md files

### Parallelism

Steps 2 and 3 are independent (both depend only on step 1). Steps 4 and 5 are
independent of each other but should run after 2+3 to validate the full change.
