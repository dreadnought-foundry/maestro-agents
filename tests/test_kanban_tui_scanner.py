"""Tests for kanban_tui.scanner — status-based split rendering."""

from __future__ import annotations

from pathlib import Path

import pytest

from kanban_tui.scanner import (
    COLUMN_ORDER,
    EpicInfo,
    SprintInfo,
    _sprint_display_column,
    _status_from_name,
    scan_kanban,
)
from kanban_tui.app import MAIN_COLUMNS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_sprint(
    parent: Path,
    sprint_num: int,
    title: str,
    status: str,
    epic_num: int | None = None,
    suffix: str = "",
) -> Path:
    """Create a sprint folder with a .md file inside it."""
    slug = title.lower().replace(" ", "-")
    folder_name = f"sprint-{sprint_num:02d}_{slug}{suffix}"
    sprint_dir = parent / folder_name
    sprint_dir.mkdir(parents=True, exist_ok=True)
    md = sprint_dir / f"sprint-{sprint_num:02d}_{slug}.md"
    epic_line = f"epic: {epic_num}" if epic_num is not None else "epic: null"
    md.write_text(
        f"---\nsprint: {sprint_num}\ntitle: \"{title}\"\ntype: backend\n"
        f"{epic_line}\nstatus: {status}\ncreated: 2026-01-01T00:00:00Z\n"
        "started: null\ncompleted: null\nhours: null\n---\n\n# Sprint\n"
    )
    return sprint_dir


def _write_epic(col_dir: Path, epic_num: int, title: str, status: str = "in-progress") -> Path:
    """Create an epic directory with _epic.md."""
    slug = title.lower().replace(" ", "-")
    epic_dir = col_dir / f"epic-{epic_num:02d}_{slug}"
    epic_dir.mkdir(parents=True, exist_ok=True)
    (epic_dir / "_epic.md").write_text(
        f"---\nepic: {epic_num}\ntitle: \"{title}\"\nstatus: {status}\n"
        "created: 2026-01-01\n---\n\n# Epic\n"
    )
    return epic_dir


# ---------------------------------------------------------------------------
# Unit tests for helpers
# ---------------------------------------------------------------------------

class TestStatusFromName:
    def test_done_suffix(self):
        assert _status_from_name("sprint-01_foo--done") == "done"

    def test_blocked_suffix(self):
        assert _status_from_name("sprint-01_foo--blocked") == "blocked"

    def test_no_suffix(self):
        assert _status_from_name("sprint-01_foo") is None

    def test_done_in_middle_ignored(self):
        # --done must be an explicit suffix token
        assert _status_from_name("sprint-01_done-stuff--done") == "done"


class TestSprintDisplayColumn:
    def _make_sprint(self, status: str, movable_name: str) -> SprintInfo:
        p = Path(f"/fake/{movable_name}")
        return SprintInfo(
            number=1,
            title="Test",
            status=status,
            sprint_type="backend",
            epic_number=None,
            path=p / "sprint-01_test.md",
            movable_path=p,
            is_folder=True,
        )

    def test_yaml_done_maps_to_done_column(self):
        sprint = self._make_sprint("done", "sprint-01_test")
        assert _sprint_display_column(sprint, "2-in-progress") == "4-done"

    def test_yaml_in_progress_maps_to_in_progress_column(self):
        sprint = self._make_sprint("in-progress", "sprint-01_test")
        assert _sprint_display_column(sprint, "1-todo") == "2-in-progress"

    def test_yaml_review_maps_to_review_column(self):
        sprint = self._make_sprint("review", "sprint-01_test")
        assert _sprint_display_column(sprint, "2-in-progress") == "3-review"

    def test_done_suffix_overrides_yaml_status(self):
        sprint = self._make_sprint("in-progress", "sprint-01_test--done")
        assert _sprint_display_column(sprint, "2-in-progress") == "4-done"

    def test_blocked_suffix_overrides_yaml_status(self):
        sprint = self._make_sprint("in-progress", "sprint-01_test--blocked")
        assert _sprint_display_column(sprint, "2-in-progress") == "5-blocked"

    def test_unknown_status_falls_back_to_physical_col(self):
        sprint = self._make_sprint("unknown", "sprint-01_test")
        assert _sprint_display_column(sprint, "2-in-progress") == "2-in-progress"

    def test_planning_maps_to_todo(self):
        sprint = self._make_sprint("planning", "sprint-01_test")
        assert _sprint_display_column(sprint, "2-in-progress") == "1-todo"


# ---------------------------------------------------------------------------
# Integration tests for scan_kanban
# ---------------------------------------------------------------------------

class TestScanKanban:
    def test_epic_with_mixed_statuses_appears_in_multiple_columns(self, tmp_path):
        """An epic whose sprints have different statuses should appear in each matching column."""
        in_progress_col = tmp_path / "2-in-progress"
        in_progress_col.mkdir()
        epic_dir = _write_epic(in_progress_col, epic_num=7, title="Production")

        _write_sprint(epic_dir, 25, "Executor", status="done", epic_num=7)
        _write_sprint(epic_dir, 26, "E2E", status="in-progress", epic_num=7)
        _write_sprint(epic_dir, 27, "Lifecycle", status="done", epic_num=7)

        (tmp_path / "4-done").mkdir()

        columns = scan_kanban(tmp_path)
        col_map = {c.name: c for c in columns}

        assert "2-in-progress" in col_map
        assert "4-done" in col_map

        # E-07 appears in in-progress with S-26 only
        in_prog_epics = {e.number: e for e in col_map["2-in-progress"].epics}
        assert 7 in in_prog_epics
        assert [s.number for s in in_prog_epics[7].sprints] == [26]

        # E-07 appears in done with S-25 and S-27
        done_epics = {e.number: e for e in col_map["4-done"].epics}
        assert 7 in done_epics
        assert [s.number for s in done_epics[7].sprints] == [25, 27]

    def test_epic_all_done_appears_only_in_done_column(self, tmp_path):
        """An epic where all sprints are done should only appear in the done column."""
        in_progress_col = tmp_path / "2-in-progress"
        in_progress_col.mkdir()
        (tmp_path / "4-done").mkdir()

        epic_dir = _write_epic(in_progress_col, epic_num=5, title="Completed Epic")
        _write_sprint(epic_dir, 10, "Alpha", status="done", epic_num=5)
        _write_sprint(epic_dir, 11, "Beta", status="done", epic_num=5)

        columns = scan_kanban(tmp_path)
        col_map = {c.name: c for c in columns}

        # Should NOT appear in in-progress
        in_prog_epic_nums = {e.number for e in col_map.get("2-in-progress", type("_", (), {"epics": []})()).epics}
        assert 5 not in in_prog_epic_nums

        # Should appear in done with both sprints
        done_epics = {e.number: e for e in col_map["4-done"].epics}
        assert 5 in done_epics
        assert len(done_epics[5].sprints) == 2

    def test_standalone_sprint_placed_by_status(self, tmp_path):
        """A standalone sprint is placed in the column matching its YAML status."""
        (tmp_path / "1-todo").mkdir()
        (tmp_path / "2-in-progress").mkdir()
        (tmp_path / "4-done").mkdir()

        # Sprint physically in todo but status=done
        todo_dir = tmp_path / "1-todo"
        _write_sprint(todo_dir, 1, "Alpha", status="done")

        columns = scan_kanban(tmp_path)
        col_map = {c.name: c for c in columns}

        # Should appear in done, not todo
        todo_sprint_nums = {s.number for s in col_map.get("1-todo", type("_", (), {"standalone_sprints": []})()).standalone_sprints}
        assert 1 not in todo_sprint_nums

        done_sprint_nums = {s.number for s in col_map["4-done"].standalone_sprints}
        assert 1 in done_sprint_nums

    def test_standalone_sprint_with_done_suffix_placed_in_done(self, tmp_path):
        """A standalone sprint folder with --done suffix goes to the done column."""
        in_progress_col = tmp_path / "2-in-progress"
        in_progress_col.mkdir()
        (tmp_path / "4-done").mkdir()

        _write_sprint(in_progress_col, 3, "Gamma", status="in-progress", suffix="--done")

        columns = scan_kanban(tmp_path)
        col_map = {c.name: c for c in columns}

        done_sprint_nums = {s.number for s in col_map["4-done"].standalone_sprints}
        assert 3 in done_sprint_nums

        in_prog_sprint_nums = {s.number for s in col_map["2-in-progress"].standalone_sprints}
        assert 3 not in in_prog_sprint_nums

    def test_epic_sprint_count_per_column_is_correct(self, tmp_path):
        """Each column's epic card only counts the sprints shown in that column."""
        in_progress_col = tmp_path / "2-in-progress"
        in_progress_col.mkdir()
        (tmp_path / "4-done").mkdir()

        epic_dir = _write_epic(in_progress_col, epic_num=3, title="Mixed Epic")
        _write_sprint(epic_dir, 1, "Sprint One", status="done", epic_num=3)
        _write_sprint(epic_dir, 2, "Sprint Two", status="in-progress", epic_num=3)
        _write_sprint(epic_dir, 3, "Sprint Three", status="done", epic_num=3)

        columns = scan_kanban(tmp_path)
        col_map = {c.name: c for c in columns}

        in_prog_epics = {e.number: e for e in col_map["2-in-progress"].epics}
        done_epics = {e.number: e for e in col_map["4-done"].epics}

        assert len(in_prog_epics[3].sprints) == 1  # only S-02
        assert len(done_epics[3].sprints) == 2      # S-01 and S-03

    def test_epics_sorted_by_number_within_column(self, tmp_path):
        in_progress_col = tmp_path / "2-in-progress"
        in_progress_col.mkdir()

        for num, title in [(9, "Nine"), (2, "Two"), (5, "Five")]:
            epic_dir = _write_epic(in_progress_col, epic_num=num, title=title)
            _write_sprint(epic_dir, num * 10, "Sprint", status="in-progress", epic_num=num)

        columns = scan_kanban(tmp_path)
        col_map = {c.name: c for c in columns}

        epic_nums = [e.number for e in col_map["2-in-progress"].epics]
        assert epic_nums == sorted(epic_nums)

    def test_sprints_sorted_by_number_within_epic_column(self, tmp_path):
        in_progress_col = tmp_path / "2-in-progress"
        in_progress_col.mkdir()

        epic_dir = _write_epic(in_progress_col, epic_num=1, title="One")
        for num in [30, 10, 20]:
            _write_sprint(epic_dir, num, f"Sprint {num}", status="in-progress", epic_num=1)

        columns = scan_kanban(tmp_path)
        col_map = {c.name: c for c in columns}

        sprint_nums = [s.number for s in col_map["2-in-progress"].epics[0].sprints]
        assert sprint_nums == sorted(sprint_nums)


# ---------------------------------------------------------------------------
# MAIN_COLUMNS constant
# ---------------------------------------------------------------------------

class TestMainColumns:
    def test_includes_todo(self):
        assert "1-todo" in MAIN_COLUMNS

    def test_includes_in_progress(self):
        assert "2-in-progress" in MAIN_COLUMNS

    def test_includes_review(self):
        assert "3-review" in MAIN_COLUMNS

    def test_includes_done(self):
        assert "4-done" in MAIN_COLUMNS

    def test_does_not_include_backlog_or_archived(self):
        assert "0-backlog" not in MAIN_COLUMNS
        assert "7-archived" not in MAIN_COLUMNS
