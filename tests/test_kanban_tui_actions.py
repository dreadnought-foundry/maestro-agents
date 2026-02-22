"""Tests for kanban TUI actions — ensure board actions stay lightweight.

The key invariant: pressing "s" to start a sprint must ONLY move the card
to in-progress.  It must NOT invoke the execution engine (run_sprint),
which would block the TUI and hang.
"""

from __future__ import annotations

import inspect
import textwrap
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("textual")

from kanban_tui.app import KanbanApp, SprintCard
from kanban_tui.scanner import SprintInfo, scan_kanban


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_kanban(tmp_path: Path) -> Path:
    """Create a minimal kanban directory with one sprint in todo."""
    kanban = tmp_path / "kanban"
    for col in ("0-backlog", "1-todo", "2-in-progress", "3-review", "4-done",
                "5-blocked", "6-abandoned", "7-archived"):
        (kanban / col).mkdir(parents=True)

    sprint_dir = kanban / "1-todo" / "sprint-01_setup"
    sprint_dir.mkdir()
    (sprint_dir / "sprint-01_setup.md").write_text(textwrap.dedent("""\
        ---
        sprint: 1
        title: "Setup"
        type: backend
        epic: null
        status: todo
        created: 2026-01-01T00:00:00Z
        started: null
        completed: null
        hours: null
        ---

        # Sprint 1: Setup
    """))
    return kanban


# ---------------------------------------------------------------------------
# Tests: action_start_sprint does NOT use execution engine
# ---------------------------------------------------------------------------

class TestStartSprintAction:
    """Ensure the TUI start action is a lightweight card move."""

    def test_no_run_sprint_import(self):
        """action_start_sprint must not import or call run_sprint."""
        source = inspect.getsource(KanbanApp.action_start_sprint)
        assert "run_sprint" not in source, (
            "action_start_sprint should NOT call run_sprint — "
            "that blocks the TUI.  Use backend.start_sprint instead."
        )

    def test_no_convenience_import(self):
        """action_start_sprint must not import from execution.convenience."""
        source = inspect.getsource(KanbanApp.action_start_sprint)
        assert "convenience" not in source, (
            "action_start_sprint should NOT import from execution.convenience — "
            "the TUI should only move the card, not run agents."
        )

    def test_uses_backend_start_sprint(self):
        """action_start_sprint should delegate to backend.start_sprint."""
        source = inspect.getsource(KanbanApp.action_start_sprint)
        assert "backend.start_sprint" in source, (
            "action_start_sprint should use backend.start_sprint to move the card."
        )

    def test_sprint_moves_to_in_progress(self, tmp_path):
        """Starting a sprint via the backend should move it to 2-in-progress."""
        kanban = _make_kanban(tmp_path)

        # Verify sprint is in todo
        board = scan_kanban(kanban)
        todo_sprints = []
        for col in board:
            if col.name == "1-todo":
                for epic in col.epics:
                    todo_sprints.extend(epic.sprints)
                todo_sprints.extend(col.standalone_sprints)
        assert len(todo_sprints) == 1
        assert todo_sprints[0].number == 1

        # Simulate the filesystem move (fallback path)
        sprint = todo_sprints[0]
        import shutil
        from kanban_tui.scanner import write_history_entry

        write_history_entry(sprint.path, "2-in-progress")
        src = sprint.movable_path
        target = kanban / "2-in-progress"
        shutil.move(str(src), str(target / src.name))

        # Verify sprint moved to in-progress
        board = scan_kanban(kanban)
        ip_sprints = []
        for col in board:
            if col.name == "2-in-progress":
                for epic in col.epics:
                    ip_sprints.extend(epic.sprints)
                ip_sprints.extend(col.standalone_sprints)
        assert len(ip_sprints) == 1
        assert ip_sprints[0].number == 1

        # Verify todo is now empty
        todo_sprints = []
        for col in board:
            if col.name == "1-todo":
                for epic in col.epics:
                    todo_sprints.extend(epic.sprints)
                todo_sprints.extend(col.standalone_sprints)
        assert len(todo_sprints) == 0


class TestCompleteReviewAction:
    """Ensure the complete action also stays lightweight."""

    def test_no_run_sprint_import(self):
        """action_complete_review must not import or call run_sprint."""
        source = inspect.getsource(KanbanApp.action_complete_review)
        assert "run_sprint" not in source
