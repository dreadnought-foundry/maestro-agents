---
sprint: 22
title: "Kanban TUI Application"
type: tooling
epic: 5
status: in-progress
created: 2026-02-15T00:00:00Z
started: 2026-02-15T00:00:00Z
completed: null
hours: null
---

# Sprint 22: Kanban TUI Application

## Overview

| Field | Value |
|-------|-------|
| Sprint | 22 |
| Title | Kanban TUI Application |
| Type | tooling |
| Epic | 5 |
| Status | Planning |
| Created | 2026-02-15 |

## Goal

Build an interactive terminal UI using Python Textual that reads the `kanban/` folder structure and renders it as a visual board with columns, cards, navigation, and the ability to move items between columns.

## Filesystem Conventions

The scanner must handle two sprint layouts found in the kanban directory:

1. **Epic-grouped sprints** (folders) — `kanban/<column>/epic-NN_slug/sprint-NN_slug/sprint-NN.md`
   - Epic has `_epic.md` at its root
   - Sprints are subfolders containing a `.md` file
2. **Standalone sprints** (flat files) — `kanban/<column>/sprint-NN_slug.md`
   - Sprint `.md` lives directly in a column folder, not inside an epic
3. **Completed epic sprints** (flat files inside epic) — `kanban/<column>/epic-NN_slug/sprint-NN.md`
   - Sprint `.md` is a flat file inside the epic folder (no subfolder)

The scanner must detect all three patterns. Standalone sprints render as top-level cards in the column (not nested under any epic). Move operations must preserve the item's structure (folder or flat file).

## Interface Contract (define first)

- `KanbanBoard` — main Textual App, reads kanban directory, renders columns
- `Column` widget — represents a kanban folder (e.g. `1-todo`), displays cards
- `EpicCard` widget — collapsible card showing epic name + nested sprint cards
- `SprintCard` widget — card showing sprint title, status, type badge; used for both epic-nested and standalone sprints
- `DetailPanel` widget — sidebar showing full markdown content of selected item
- Moving a card = `shutil.move()` of the folder/file between kanban column directories

## Tech Stack

- **Python 3.12+**
- **Textual** — TUI framework (pip: `textual`)
- **PyYAML** or frontmatter lib — parse sprint/epic markdown frontmatter
- **uv** — for running (`uv run kanban_tui.py`)

## Tasks

### Phase 1: Planning
- [ ] Review kanban directory structure and conventions
- [ ] Design widget hierarchy and keybindings

### Phase 2: Implementation
- [ ] Set up `kanban_tui/` package with `__main__.py` entry point
- [ ] Implement folder scanning — discover columns, epics, sprints
- [ ] Implement frontmatter parsing for `_epic.md` and sprint `.md` files
- [ ] Build `Column` widget rendering cards vertically
- [ ] Build `EpicCard` with collapsible sprint list
- [ ] Build `SprintCard` with color-coding by epic
- [ ] Build `DetailPanel` for viewing selected item metadata
- [ ] Implement move action — arrow keys to move card between columns
- [ ] Add keybinding help footer
- [ ] Add `pyproject.toml` with textual dependency

### Phase 3: Validation
- [ ] Manual test with current kanban contents
- [ ] Verify move operation actually relocates folders
- [ ] Verify board refreshes after move
- [ ] Test with empty columns
- [ ] Test standalone sprints (flat .md files in column root) render correctly
- [ ] Test moving standalone sprints preserves flat-file structure

## Deliverables

- `kanban_tui/` package at project root
  - `__main__.py` — entry point
  - `app.py` — KanbanBoard Textual app
  - `widgets.py` — Column, EpicCard, SprintCard, DetailPanel
  - `scanner.py` — filesystem scanning and frontmatter parsing
- `pyproject.toml` updates (or standalone) with textual dependency

## Acceptance Criteria

- [ ] `uv run python -m kanban_tui` launches the board
- [ ] All 7 columns displayed with correct headers
- [ ] Epics grouped with their sprints within each column
- [ ] Standalone sprints (not in an epic) render as top-level cards in the column
- [ ] Cards color-coded by epic (standalone sprints get a neutral color)
- [ ] Arrow keys navigate between cards and columns
- [ ] Enter/move action relocates folder and refreshes board
- [ ] Selected card shows metadata in detail panel
- [ ] Works with current kanban contents (5 epics, 21 sprints)

## Dependencies

- **Sprints**: None — standalone tooling
- **External**: `textual` Python package

## Deferred Items

- Filtering by epic or status
- Search functionality
- Drag-and-drop (not available in TUI)
- Sprint creation from within the TUI
- Watch mode for external changes
