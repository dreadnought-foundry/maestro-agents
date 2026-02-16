---
epic: 5
title: "Kanban TUI Board"
status: in-progress
created: 2026-02-15
started: 2026-02-15
completed: null
---

# Epic 05: Kanban TUI Board

## Overview

Build an interactive terminal UI (TUI) using Python Textual that visualizes the kanban folder structure as a board with columns, epic grouping, and the ability to move items between columns.

## Why This Matters

The folder-based kanban system works well as a source of truth but lacks visual overview. A TUI provides at-a-glance project status, interactive card movement, and sprint metadata preview — all without leaving the terminal or introducing external infrastructure.

## Design Principles

- **Folders are the source of truth** — the TUI reads from and writes to `kanban/` directories
- **Zero infrastructure** — no server, no database, just a Python script
- **Works with existing workflow** — `/sprint-*` and `/epic-*` skills still work because the underlying files don't change
- **Keyboard-driven** — arrow keys to navigate, enter to move/inspect

## Sprints

| Sprint | Title | Status |
|--------|-------|--------|
| 22 | Kanban TUI Application | planned |

## Success Criteria

- Board displays all 7 kanban columns with correct contents
- Epics shown as grouped cards, sprints nested within
- Cards can be moved between columns (moves the actual folder)
- Sprint/epic metadata viewable on selection
- Color-coded by epic for visual tracking
- Installable via `uv run` with no additional setup

## Notes

Created: 2026-02-15
