"""Tests for kanban_tui.scanner — status-based split rendering."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("textual")

from kanban_tui.scanner import (
    COLUMN_ORDER,
    EpicInfo,
    SprintInfo,
    _find_sprint_md,
    _sprint_display_column,
    _status_from_name,
    parse_frontmatter,
    scan_kanban,
    write_history_entry,
)
from kanban_tui.app import MAIN_COLUMNS


ARTIFACT_SUFFIXES = ("_contracts", "_quality", "_postmortem", "_deferred")
PLANNING_ARTIFACT_NAMES = (
    "_planning_contracts", "_planning_team_plan", "_planning_tdd_strategy",
    "_planning_coding_strategy", "_planning_context_brief",
)


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


def _write_sprint_with_artifacts(
    parent: Path,
    sprint_num: int,
    title: str,
    status: str,
    epic_num: int | None = None,
    suffix: str = "",
) -> Path:
    """Create a sprint folder with spec + all 4 artifact files (realistic shape)."""
    sprint_dir = _write_sprint(parent, sprint_num, title, status, epic_num, suffix)
    slug = title.lower().replace(" ", "-")
    prefix = f"sprint-{sprint_num:02d}"
    for artifact in ARTIFACT_SUFFIXES:
        artifact_name = artifact.lstrip("_").title()
        (sprint_dir / f"{prefix}{artifact}.md").write_text(
            f"# {artifact_name}\n\nGenerated artifact.\n"
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


def _make_columns(tmp_path: Path, *col_names: str) -> None:
    """Create column directories."""
    for name in col_names:
        (tmp_path / name).mkdir(exist_ok=True)


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

    def test_yaml_status_ignored_uses_physical_column(self):
        """YAML status alone does not move sprints — directory is source of truth."""
        sprint = self._make_sprint("done", "sprint-01_test")
        assert _sprint_display_column(sprint, "2-in-progress") == "2-in-progress"

    def test_yaml_in_progress_stays_in_physical_column(self):
        sprint = self._make_sprint("in-progress", "sprint-01_test")
        assert _sprint_display_column(sprint, "1-todo") == "1-todo"

    def test_yaml_review_stays_in_physical_column(self):
        sprint = self._make_sprint("review", "sprint-01_test")
        assert _sprint_display_column(sprint, "2-in-progress") == "2-in-progress"

    def test_done_suffix_overrides_physical_column(self):
        sprint = self._make_sprint("in-progress", "sprint-01_test--done")
        assert _sprint_display_column(sprint, "2-in-progress") == "4-done"

    def test_blocked_suffix_overrides_physical_column(self):
        sprint = self._make_sprint("in-progress", "sprint-01_test--blocked")
        assert _sprint_display_column(sprint, "2-in-progress") == "5-blocked"

    def test_unknown_status_stays_in_physical_column(self):
        sprint = self._make_sprint("unknown", "sprint-01_test")
        assert _sprint_display_column(sprint, "2-in-progress") == "2-in-progress"

    def test_planning_stays_in_physical_column(self):
        sprint = self._make_sprint("planning", "sprint-01_test")
        assert _sprint_display_column(sprint, "2-in-progress") == "2-in-progress"


class TestFindSprintMd:
    """Unit tests for _find_sprint_md — the file picker for sprint folders."""

    def test_single_md_file(self, tmp_path):
        sprint_dir = tmp_path / "sprint-01_alpha"
        sprint_dir.mkdir()
        spec = sprint_dir / "sprint-01_alpha.md"
        spec.write_text("---\nsprint: 1\n---\n")
        assert _find_sprint_md(sprint_dir) == spec

    def test_picks_spec_over_artifacts(self, tmp_path):
        sprint_dir = tmp_path / "sprint-29_kanbanadapter--done"
        sprint_dir.mkdir()
        spec = sprint_dir / "sprint-29_kanbanadapter--done.md"
        spec.write_text("---\nsprint: 29\ntitle: KanbanAdapter\n---\n")
        (sprint_dir / "sprint-29_contracts.md").write_text("# Contracts\n")
        (sprint_dir / "sprint-29_deferred.md").write_text("# Deferred\n")
        (sprint_dir / "sprint-29_postmortem.md").write_text("# Postmortem\n")
        (sprint_dir / "sprint-29_quality.md").write_text("# Quality\n")
        assert _find_sprint_md(sprint_dir) == spec

    def test_picks_spec_without_suffix_when_folder_has_suffix(self, tmp_path):
        """Folder has --done but spec file doesn't — still matches by stripping suffix."""
        sprint_dir = tmp_path / "sprint-05_feature--done"
        sprint_dir.mkdir()
        spec = sprint_dir / "sprint-05_feature.md"
        spec.write_text("---\nsprint: 5\n---\n")
        (sprint_dir / "sprint-05_contracts.md").write_text("# Contracts\n")
        assert _find_sprint_md(sprint_dir) == spec

    def test_falls_back_to_prefix_match_skipping_artifacts(self, tmp_path):
        """When no exact folder-name match, picks by prefix but skips artifact files."""
        sprint_dir = tmp_path / "sprint-10_old-name"
        sprint_dir.mkdir()
        # Spec was renamed but folder wasn't
        spec = sprint_dir / "sprint-10_new-name.md"
        spec.write_text("---\nsprint: 10\n---\n")
        (sprint_dir / "sprint-10_contracts.md").write_text("# Contracts\n")
        (sprint_dir / "sprint-10_quality.md").write_text("# Quality\n")
        assert _find_sprint_md(sprint_dir) == spec

    def test_empty_folder_returns_none(self, tmp_path):
        sprint_dir = tmp_path / "sprint-01_empty"
        sprint_dir.mkdir()
        assert _find_sprint_md(sprint_dir) is None

    def test_skips_planning_artifacts(self, tmp_path):
        """Planning artifact files (sprint-NN_planning_*.md) are skipped in prefix fallback."""
        sprint_dir = tmp_path / "sprint-37_kanban-history"
        sprint_dir.mkdir()
        spec = sprint_dir / "sprint-37_kanban-history.md"
        spec.write_text("---\nsprint: 37\ntitle: Kanban History\n---\n")
        for pname in PLANNING_ARTIFACT_NAMES:
            (sprint_dir / f"sprint-37{pname}.md").write_text(f"# {pname}\n")
        assert _find_sprint_md(sprint_dir) == spec

    def test_only_planning_artifacts_falls_back_to_first(self, tmp_path):
        """If only planning artifact files exist (no spec), returns first as last resort."""
        sprint_dir = tmp_path / "sprint-37_lost"
        sprint_dir.mkdir()
        (sprint_dir / "sprint-37_planning_contracts.md").write_text("# Contracts\n")
        result = _find_sprint_md(sprint_dir)
        assert result is not None

    def test_only_artifact_files_falls_back_to_first(self, tmp_path):
        """If only artifact files exist (no spec), returns first as last resort."""
        sprint_dir = tmp_path / "sprint-01_lost"
        sprint_dir.mkdir()
        (sprint_dir / "sprint-01_contracts.md").write_text("# Contracts\n")
        (sprint_dir / "sprint-01_quality.md").write_text("# Quality\n")
        result = _find_sprint_md(sprint_dir)
        assert result is not None  # returns something rather than None


class TestParseFrontmatter:
    def test_valid_frontmatter(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("---\nsprint: 1\ntitle: Test\n---\n# Body\n")
        fm = parse_frontmatter(f)
        assert fm["sprint"] == 1
        assert fm["title"] == "Test"

    def test_no_frontmatter(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# Just a heading\n\nNo frontmatter here.\n")
        assert parse_frontmatter(f) == {}

    def test_missing_file(self, tmp_path):
        assert parse_frontmatter(tmp_path / "nonexistent.md") == {}

    def test_invalid_yaml(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("---\n: invalid: yaml: [broken\n---\n")
        assert parse_frontmatter(f) == {}


# ---------------------------------------------------------------------------
# Integration tests for scan_kanban
# ---------------------------------------------------------------------------

class TestScanKanban:
    def test_epic_with_mixed_suffixes_appears_in_multiple_columns(self, tmp_path):
        """An epic whose sprints have different path suffixes should appear in each matching column."""
        _make_columns(tmp_path, "2-in-progress", "4-done")
        epic_dir = _write_epic(tmp_path / "2-in-progress", epic_num=7, title="Production")

        _write_sprint(epic_dir, 25, "Executor", status="done", epic_num=7, suffix="--done")
        _write_sprint(epic_dir, 26, "E2E", status="in-progress", epic_num=7)
        _write_sprint(epic_dir, 27, "Lifecycle", status="done", epic_num=7, suffix="--done")

        columns = scan_kanban(tmp_path)
        col_map = {c.name: c for c in columns}

        # E-07 appears in in-progress with S-26 only (no suffix)
        in_prog_epics = {e.number: e for e in col_map["2-in-progress"].epics}
        assert 7 in in_prog_epics
        assert [s.number for s in in_prog_epics[7].sprints] == [26]

        # E-07 appears in done with S-25 and S-27 (--done suffix)
        done_epics = {e.number: e for e in col_map["4-done"].epics}
        assert 7 in done_epics
        assert [s.number for s in done_epics[7].sprints] == [25, 27]

    def test_epic_all_done_suffix_appears_only_in_done_column(self, tmp_path):
        """An epic where all sprints have --done suffix should only appear in the done column."""
        _make_columns(tmp_path, "2-in-progress", "4-done")

        epic_dir = _write_epic(tmp_path / "2-in-progress", epic_num=5, title="Completed Epic")
        _write_sprint(epic_dir, 10, "Alpha", status="done", epic_num=5, suffix="--done")
        _write_sprint(epic_dir, 11, "Beta", status="done", epic_num=5, suffix="--done")

        columns = scan_kanban(tmp_path)
        col_map = {c.name: c for c in columns}

        # Should NOT appear in in-progress (all sprints have --done suffix)
        in_prog_epic_nums = {e.number for e in col_map["2-in-progress"].epics}
        assert 5 not in in_prog_epic_nums

        # Should appear in done with both sprints
        done_epics = {e.number: e for e in col_map["4-done"].epics}
        assert 5 in done_epics
        assert len(done_epics[5].sprints) == 2

    def test_yaml_status_does_not_override_physical_column(self, tmp_path):
        """YAML status is informational — it does not move a sprint to a different column."""
        _make_columns(tmp_path, "1-todo", "4-done")

        # Sprint physically in todo, YAML says done, no --done suffix
        _write_sprint(tmp_path / "1-todo", 1, "Alpha", status="done")

        columns = scan_kanban(tmp_path)
        col_map = {c.name: c for c in columns}

        # Sprint stays in its physical column (todo), not moved to done
        todo_sprint_nums = {s.number for s in col_map["1-todo"].standalone_sprints}
        assert 1 in todo_sprint_nums

        done_sprint_nums = {s.number for s in col_map["4-done"].standalone_sprints}
        assert 1 not in done_sprint_nums

    def test_standalone_sprint_stays_in_physical_column(self, tmp_path):
        """A standalone sprint stays in its physical column regardless of YAML status."""
        _make_columns(tmp_path, "1-todo", "2-in-progress", "4-done")

        # Sprint physically in todo, YAML says done — should stay in todo
        _write_sprint(tmp_path / "1-todo", 1, "Alpha", status="done")

        columns = scan_kanban(tmp_path)
        col_map = {c.name: c for c in columns}

        todo_sprint_nums = {s.number for s in col_map["1-todo"].standalone_sprints}
        assert 1 in todo_sprint_nums

        done_sprint_nums = {s.number for s in col_map["4-done"].standalone_sprints}
        assert 1 not in done_sprint_nums

    def test_standalone_sprint_with_done_suffix_placed_in_done(self, tmp_path):
        """A standalone sprint folder with --done suffix goes to the done column."""
        _make_columns(tmp_path, "2-in-progress", "4-done")

        _write_sprint(tmp_path / "2-in-progress", 3, "Gamma", status="in-progress", suffix="--done")

        columns = scan_kanban(tmp_path)
        col_map = {c.name: c for c in columns}

        done_sprint_nums = {s.number for s in col_map["4-done"].standalone_sprints}
        assert 3 in done_sprint_nums

        in_prog_sprint_nums = {s.number for s in col_map["2-in-progress"].standalone_sprints}
        assert 3 not in in_prog_sprint_nums

    def test_epic_sprint_count_per_column_is_correct(self, tmp_path):
        """Each column's epic card only counts the sprints shown in that column."""
        _make_columns(tmp_path, "2-in-progress", "4-done")

        epic_dir = _write_epic(tmp_path / "2-in-progress", epic_num=3, title="Mixed Epic")
        _write_sprint(epic_dir, 1, "Sprint One", status="done", epic_num=3, suffix="--done")
        _write_sprint(epic_dir, 2, "Sprint Two", status="in-progress", epic_num=3)
        _write_sprint(epic_dir, 3, "Sprint Three", status="done", epic_num=3, suffix="--done")

        columns = scan_kanban(tmp_path)
        col_map = {c.name: c for c in columns}

        in_prog_epics = {e.number: e for e in col_map["2-in-progress"].epics}
        done_epics = {e.number: e for e in col_map["4-done"].epics}

        assert len(in_prog_epics[3].sprints) == 1  # only S-02 (no suffix)
        assert len(done_epics[3].sprints) == 2      # S-01 and S-03 (--done suffix)

    def test_epics_sorted_by_number_within_column(self, tmp_path):
        _make_columns(tmp_path, "2-in-progress")

        for num, title in [(9, "Nine"), (2, "Two"), (5, "Five")]:
            epic_dir = _write_epic(tmp_path / "2-in-progress", epic_num=num, title=title)
            _write_sprint(epic_dir, num * 10, "Sprint", status="in-progress", epic_num=num)

        columns = scan_kanban(tmp_path)
        col_map = {c.name: c for c in columns}

        epic_nums = [e.number for e in col_map["2-in-progress"].epics]
        assert epic_nums == sorted(epic_nums)

    def test_sprints_sorted_by_number_within_epic_column(self, tmp_path):
        _make_columns(tmp_path, "2-in-progress")

        epic_dir = _write_epic(tmp_path / "2-in-progress", epic_num=1, title="One")
        for num in [30, 10, 20]:
            _write_sprint(epic_dir, num, f"Sprint {num}", status="in-progress", epic_num=1)

        columns = scan_kanban(tmp_path)
        col_map = {c.name: c for c in columns}

        sprint_nums = [s.number for s in col_map["2-in-progress"].epics[0].sprints]
        assert sprint_nums == sorted(sprint_nums)

    def test_sprint_with_artifact_files_picks_correct_md(self, tmp_path):
        """When a sprint folder has artifact files alongside the spec, scanner reads the spec."""
        _make_columns(tmp_path, "4-done")

        epic_dir = _write_epic(tmp_path / "4-done", epic_num=7, title="Production")
        sprint_dir = _write_sprint(
            epic_dir, 29, "KanbanAdapter", status="done", epic_num=7, suffix="--done",
        )

        # Add artifact files that sort alphabetically before the spec
        (sprint_dir / "sprint-29_contracts.md").write_text("# Contracts\n")
        (sprint_dir / "sprint-29_deferred.md").write_text("# Deferred\n")
        (sprint_dir / "sprint-29_postmortem.md").write_text("# Postmortem\n")
        (sprint_dir / "sprint-29_quality.md").write_text("# Quality\n")

        columns = scan_kanban(tmp_path)
        col_map = {c.name: c for c in columns}

        done_epics = {e.number: e for e in col_map["4-done"].epics}
        assert 7 in done_epics
        sprint = done_epics[7].sprints[0]
        assert sprint.number == 29
        assert sprint.title == "KanbanAdapter"  # NOT "Contracts" or "Quality"
        assert sprint.status == "done"

    def test_standalone_sprint_with_artifacts_picks_correct_md(self, tmp_path):
        """Standalone sprint folder with artifacts reads the spec, not an artifact."""
        _make_columns(tmp_path, "4-done")

        sprint_dir = _write_sprint(
            tmp_path / "4-done", 10, "My Feature", status="done", suffix="--done",
        )
        (sprint_dir / "sprint-10_contracts.md").write_text("# Contracts\n")
        (sprint_dir / "sprint-10_quality.md").write_text("# Quality\n")

        columns = scan_kanban(tmp_path)
        col_map = {c.name: c for c in columns}

        sprint = col_map["4-done"].standalone_sprints[0]
        assert sprint.number == 10
        assert sprint.title == "My Feature"

    def test_empty_column_has_no_epics_or_sprints(self, tmp_path):
        """An empty column directory produces an empty ColumnInfo."""
        _make_columns(tmp_path, "1-todo", "2-in-progress")

        columns = scan_kanban(tmp_path)
        col_map = {c.name: c for c in columns}

        assert col_map["1-todo"].epics == []
        assert col_map["1-todo"].standalone_sprints == []

    def test_epic_with_no_sprints_appears_in_physical_column(self, tmp_path):
        """An epic directory with _epic.md but no sprint folders still shows up."""
        _make_columns(tmp_path, "0-backlog")

        _write_epic(tmp_path / "0-backlog", epic_num=99, title="Empty Epic")

        columns = scan_kanban(tmp_path)
        col_map = {c.name: c for c in columns}

        epic_nums = {e.number for e in col_map["0-backlog"].epics}
        assert 99 in epic_nums

    def test_all_columns_present_in_result(self, tmp_path):
        """All column directories that exist on disk appear in the result."""
        for col in COLUMN_ORDER:
            (tmp_path / col).mkdir()

        columns = scan_kanban(tmp_path)
        col_names = [c.name for c in columns]
        assert col_names == COLUMN_ORDER

    def test_columns_ordered_canonically(self, tmp_path):
        """Result columns follow COLUMN_ORDER regardless of filesystem order."""
        # Create columns in reverse order
        for col in reversed(COLUMN_ORDER):
            (tmp_path / col).mkdir()

        columns = scan_kanban(tmp_path)
        assert [c.name for c in columns] == COLUMN_ORDER

    def test_dot_files_ignored(self, tmp_path):
        """Hidden files/directories (starting with .) are ignored."""
        _make_columns(tmp_path, "2-in-progress")
        col = tmp_path / "2-in-progress"
        (col / ".DS_Store").write_text("")
        (col / ".hidden-epic").mkdir()

        columns = scan_kanban(tmp_path)
        col_map = {c.name: c for c in columns}
        assert col_map["2-in-progress"].epics == []
        assert col_map["2-in-progress"].standalone_sprints == []

    def test_non_sprint_non_epic_entries_ignored(self, tmp_path):
        """Random files and folders that don't match naming conventions are ignored."""
        _make_columns(tmp_path, "2-in-progress")
        col = tmp_path / "2-in-progress"
        (col / "random-folder").mkdir()
        (col / "notes.md").write_text("# Notes\n")
        (col / "README.md").write_text("# README\n")

        columns = scan_kanban(tmp_path)
        col_map = {c.name: c for c in columns}
        assert col_map["2-in-progress"].epics == []
        assert col_map["2-in-progress"].standalone_sprints == []


# ---------------------------------------------------------------------------
# Realistic data shape tests (mirroring production kanban structure)
# ---------------------------------------------------------------------------

class TestRealisticDataShape:
    """Tests using _write_sprint_with_artifacts to mirror real kanban data."""

    def test_completed_epic_with_full_artifacts(self, tmp_path):
        """A completed epic with all artifact files per sprint scans correctly."""
        _make_columns(tmp_path, "2-in-progress", "4-done")

        epic_dir = _write_epic(
            tmp_path / "2-in-progress", epic_num=8, title="Unified Engine",
        )
        for i, title in enumerate(["Adapter", "Review", "Phases", "Planning"], start=29):
            _write_sprint_with_artifacts(
                epic_dir, i, title, status="done", epic_num=8, suffix="--done",
            )

        columns = scan_kanban(tmp_path)
        col_map = {c.name: c for c in columns}

        # Epic should NOT appear in in-progress (all sprints done)
        assert not col_map["2-in-progress"].epics

        # All 4 sprints in done, correct titles
        done_epics = {e.number: e for e in col_map["4-done"].epics}
        assert 8 in done_epics
        sprints = done_epics[8].sprints
        assert len(sprints) == 4
        assert sprints[0].title == "Adapter"
        assert sprints[1].title == "Review"
        assert sprints[2].title == "Phases"
        assert sprints[3].title == "Planning"
        for s in sprints:
            assert s.status == "done"

    def test_mixed_epic_with_artifacts_splits_correctly(self, tmp_path):
        """Epic with some --done suffix and some without — splits by filesystem only."""
        _make_columns(tmp_path, "2-in-progress", "4-done")

        epic_dir = _write_epic(
            tmp_path / "2-in-progress", epic_num=10, title="Feature Work",
        )

        # 2 done sprints with full artifacts and --done suffix
        _write_sprint_with_artifacts(
            epic_dir, 40, "Auth", status="done", epic_num=10, suffix="--done",
        )
        _write_sprint_with_artifacts(
            epic_dir, 41, "Database", status="done", epic_num=10, suffix="--done",
        )
        # 1 in-progress sprint (no artifacts yet, no suffix)
        _write_sprint(epic_dir, 42, "API", status="in-progress", epic_num=10)
        # 1 in review (no suffix — stays in physical column)
        _write_sprint(epic_dir, 43, "Frontend", status="review", epic_num=10)

        columns = scan_kanban(tmp_path)
        col_map = {c.name: c for c in columns}

        # in-progress: S-42 and S-43 (both without suffix, stay in physical column)
        ip_epics = {e.number: e for e in col_map["2-in-progress"].epics}
        assert [s.number for s in ip_epics[10].sprints] == [42, 43]

        # done: S-40 and S-41 (--done suffix) with correct titles
        done_epics = {e.number: e for e in col_map["4-done"].epics}
        assert [s.number for s in done_epics[10].sprints] == [40, 41]
        assert done_epics[10].sprints[0].title == "Auth"
        assert done_epics[10].sprints[1].title == "Database"

    def test_multiple_epics_across_columns(self, tmp_path):
        """Multiple epics in different physical locations, sprints stay in their columns."""
        _make_columns(tmp_path, "2-in-progress", "4-done", "7-archived")

        # Epic 5 in archived — stays in archived (directory is source of truth)
        epic5 = _write_epic(tmp_path / "7-archived", epic_num=5, title="Old Work")
        _write_sprint_with_artifacts(epic5, 20, "Legacy", status="done", epic_num=5)

        # Epic 8 in in-progress, mixed: one --done suffix, one without
        epic8 = _write_epic(tmp_path / "2-in-progress", epic_num=8, title="Current")
        _write_sprint_with_artifacts(
            epic8, 30, "Done Task", status="done", epic_num=8, suffix="--done",
        )
        _write_sprint(epic8, 31, "Active Task", status="in-progress", epic_num=8)

        columns = scan_kanban(tmp_path)
        col_map = {c.name: c for c in columns}

        # Epic 5: stays in archived (its physical column), not moved to done
        archived_epics = {e.number: e for e in col_map["7-archived"].epics}
        assert 5 in archived_epics
        assert archived_epics[5].sprints[0].title == "Legacy"

        # Epic 8: split between in-progress and done (via --done suffix)
        done_epics = {e.number: e for e in col_map["4-done"].epics}
        assert 8 in done_epics
        assert done_epics[8].sprints[0].title == "Done Task"

        ip_epics = {e.number: e for e in col_map["2-in-progress"].epics}
        assert 8 in ip_epics
        assert ip_epics[8].sprints[0].title == "Active Task"


# ---------------------------------------------------------------------------
# Scan against real kanban directory (smoke test)
# ---------------------------------------------------------------------------

class TestRealKanbanSanity:
    """Smoke tests that run against the actual kanban/ directory if present.

    These catch data/scanner mismatches that synthetic tests miss.
    """

    @pytest.fixture
    def real_kanban_dir(self):
        kanban = Path(__file__).parent.parent / "kanban"
        if not kanban.is_dir():
            pytest.skip("No kanban/ directory found")
        return kanban

    def test_no_sprint_has_artifact_title(self, real_kanban_dir):
        """No sprint should have a title matching an artifact file name."""
        artifact_titles = {"Contracts", "Quality", "Postmortem", "Deferred"}

        columns = scan_kanban(real_kanban_dir)
        bad = []
        for col in columns:
            for epic in col.epics:
                for sprint in epic.sprints:
                    if sprint.title in artifact_titles:
                        bad.append(f"S-{sprint.number:02d} in E-{epic.number:02d} "
                                   f"({col.name}): title={sprint.title!r}")
            for sprint in col.standalone_sprints:
                if sprint.title in artifact_titles:
                    bad.append(f"S-{sprint.number:02d} standalone "
                               f"({col.name}): title={sprint.title!r}")

        assert not bad, f"Sprints with artifact titles found:\n" + "\n".join(bad)

    def test_no_sprint_has_unknown_status_in_done_column(self, real_kanban_dir):
        """Sprints in the done column should have status=done, not unknown."""
        columns = scan_kanban(real_kanban_dir)
        col_map = {c.name: c for c in columns}

        if "4-done" not in col_map:
            pytest.skip("No 4-done column")

        bad = []
        done_col = col_map["4-done"]
        for epic in done_col.epics:
            for sprint in epic.sprints:
                if sprint.status == "unknown":
                    bad.append(f"S-{sprint.number:02d} in E-{epic.number:02d}: status=unknown")
        for sprint in done_col.standalone_sprints:
            if sprint.status == "unknown":
                bad.append(f"S-{sprint.number:02d} standalone: status=unknown")

        assert not bad, f"Done sprints with unknown status:\n" + "\n".join(bad)

    def test_all_sprints_have_valid_number(self, real_kanban_dir):
        """Every sprint parsed should have a positive number."""
        columns = scan_kanban(real_kanban_dir)
        for col in columns:
            for epic in col.epics:
                for sprint in epic.sprints:
                    assert sprint.number > 0, f"Invalid sprint number in {col.name}"
            for sprint in col.standalone_sprints:
                assert sprint.number > 0, f"Invalid sprint number in {col.name}"

    def test_no_duplicate_sprint_numbers_within_epic_in_same_column(self, real_kanban_dir):
        """No two sprints with the same number in the same epic should appear in one column."""
        columns = scan_kanban(real_kanban_dir)
        for col in columns:
            for epic in col.epics:
                seen = set()
                for sprint in epic.sprints:
                    assert sprint.number not in seen, (
                        f"Duplicate S-{sprint.number} in E-{epic.number} ({col.name})"
                    )
                    seen.add(sprint.number)
            standalone_seen = set()
            for sprint in col.standalone_sprints:
                assert sprint.number not in standalone_seen, (
                    f"Duplicate standalone S-{sprint.number} in {col.name}"
                )
                standalone_seen.add(sprint.number)

    def test_columns_present(self, real_kanban_dir):
        """The real kanban dir should have at least the main columns."""
        columns = scan_kanban(real_kanban_dir)
        col_names = {c.name for c in columns}
        for main_col in MAIN_COLUMNS:
            assert main_col in col_names, f"Missing main column: {main_col}"


# ---------------------------------------------------------------------------
# History parsing and write_history_entry
# ---------------------------------------------------------------------------

class TestHistoryParsing:
    def test_history_read_from_yaml(self, tmp_path):
        """History array in YAML frontmatter is read into SprintInfo.history."""
        _make_columns(tmp_path, "2-in-progress")
        col = tmp_path / "2-in-progress"
        sprint_dir = col / "sprint-50_history-test"
        sprint_dir.mkdir()
        md = sprint_dir / "sprint-50_history-test.md"
        md.write_text(
            "---\nsprint: 50\ntitle: History Test\ntype: backend\n"
            "epic: null\ncreated: 2026-01-01T00:00:00Z\n"
            "history:\n"
            "- column: 1-todo\n  timestamp: '2026-01-01T00:00:00Z'\n"
            "- column: 2-in-progress\n  timestamp: '2026-01-02T00:00:00Z'\n"
            "---\n\n# Sprint\n"
        )
        columns = scan_kanban(tmp_path)
        col_map = {c.name: c for c in columns}
        sprint = col_map["2-in-progress"].standalone_sprints[0]
        assert len(sprint.history) == 2
        assert sprint.history[0]["column"] == "1-todo"
        assert sprint.history[1]["column"] == "2-in-progress"

    def test_empty_history_defaults_to_empty_list(self, tmp_path):
        """Sprint without history in YAML gets an empty list."""
        _make_columns(tmp_path, "1-todo")
        _write_sprint(tmp_path / "1-todo", 51, "No History", status="todo")
        columns = scan_kanban(tmp_path)
        col_map = {c.name: c for c in columns}
        sprint = col_map["1-todo"].standalone_sprints[0]
        assert sprint.history == []

    def test_write_history_entry_appends(self, tmp_path):
        """write_history_entry appends a new entry to the YAML history."""
        md = tmp_path / "sprint-52_test.md"
        md.write_text(
            "---\nsprint: 52\ntitle: Test\n---\n\n# Sprint\n"
        )
        write_history_entry(md, "2-in-progress")
        fm = parse_frontmatter(md)
        assert len(fm["history"]) == 1
        assert fm["history"][0]["column"] == "2-in-progress"
        assert "timestamp" in fm["history"][0]

    def test_write_history_entry_appends_multiple(self, tmp_path):
        """Multiple write_history_entry calls accumulate entries."""
        md = tmp_path / "sprint-53_test.md"
        md.write_text(
            "---\nsprint: 53\ntitle: Test\n---\n\n# Sprint\n"
        )
        write_history_entry(md, "1-todo")
        write_history_entry(md, "2-in-progress")
        write_history_entry(md, "3-review")
        fm = parse_frontmatter(md)
        assert len(fm["history"]) == 3
        assert [e["column"] for e in fm["history"]] == [
            "1-todo", "2-in-progress", "3-review",
        ]

    def test_write_history_entry_removes_status_field(self, tmp_path):
        """write_history_entry strips the old status field from YAML."""
        md = tmp_path / "sprint-54_test.md"
        md.write_text(
            "---\nsprint: 54\ntitle: Test\nstatus: in-progress\n---\n\n# Sprint\n"
        )
        write_history_entry(md, "3-review")
        fm = parse_frontmatter(md)
        assert "status" not in fm
        assert len(fm["history"]) == 1

    def test_status_derived_from_done_suffix(self, tmp_path):
        """Sprint with --done suffix gets status='done' regardless of YAML."""
        _make_columns(tmp_path, "2-in-progress", "4-done")
        _write_sprint(
            tmp_path / "2-in-progress", 55, "Done Sprint",
            status="in-progress", suffix="--done",
        )
        columns = scan_kanban(tmp_path)
        col_map = {c.name: c for c in columns}
        sprint = col_map["4-done"].standalone_sprints[0]
        assert sprint.status == "done"

    def test_status_falls_back_to_yaml_without_suffix(self, tmp_path):
        """Sprint without path suffix falls back to YAML status field."""
        _make_columns(tmp_path, "2-in-progress")
        _write_sprint(
            tmp_path / "2-in-progress", 56, "Active Sprint",
            status="in-progress",
        )
        columns = scan_kanban(tmp_path)
        col_map = {c.name: c for c in columns}
        sprint = col_map["2-in-progress"].standalone_sprints[0]
        assert sprint.status == "in-progress"


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
