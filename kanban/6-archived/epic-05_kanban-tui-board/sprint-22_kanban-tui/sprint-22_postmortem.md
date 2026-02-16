# Postmortem — Sprint 22: Kanban TUI Application

**Result**: Success | 10/10 tasks | tooling sprint
**Date**: 2026-02-15

## What Was Built
- Rich/Textual-based terminal UI for visualizing the kanban board
- `kanban_tui/app.py` — main KanbanBoard Textual app
- `kanban_tui/board.py` — board layout and column rendering
- `kanban_tui/cli.py` — CLI entry point
- `kanban_tui/scanner.py` — filesystem scanning and frontmatter parsing
- `kanban_tui/widgets.py` — Column, EpicCard, SprintCard, DetailPanel widgets
- Supports all three sprint layout patterns (epic-grouped folders, standalone flat files, flat files inside epic)
- Arrow key navigation and card move operations via shutil.move()

## Lessons Learned
- Scanning three different filesystem conventions requires careful pattern matching; testing with real kanban contents is essential
- Textual widget hierarchy design should be planned upfront to avoid refactoring mid-sprint
- Standalone sprints need explicit handling to avoid being swallowed by epic grouping logic

## Deferred Items
- Filtering by epic or status
- Search functionality
- Sprint creation from within the TUI
- Watch mode for external changes
