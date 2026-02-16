# API Contracts — Sprint 22: Kanban TUI Application

## Deliverables
- `kanban_tui/` package at project root
- `__main__.py` entry point (`uv run python -m kanban_tui`)
- `app.py` — KanbanBoard Textual app
- `widgets.py` — Column, EpicCard, SprintCard, DetailPanel
- `scanner.py` — filesystem scanning and frontmatter parsing

## Backend Contracts
### TUI Application
- `KanbanBoard` — main Textual App, reads kanban directory, renders columns
- `Column` — widget representing a kanban folder (e.g. `1-todo`), displays cards
- `EpicCard` — collapsible card showing epic name + nested sprint cards
- `SprintCard` — card showing sprint title, status, type badge
- `DetailPanel` — sidebar showing full markdown content of selected item

### Scanner
- `scan_kanban_dir(path)` — discovers columns, epics, sprints from filesystem
- Handles three layout patterns: epic-grouped folders, standalone flat files, flat files inside epic

### Move Operations
- Card move = `shutil.move()` of folder/file between kanban column directories

## Frontend Contracts
- N/A (this is a TUI application, no web frontend)
