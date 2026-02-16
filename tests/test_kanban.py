"""Tests for the kanban board scanner and handlers."""

import pytest
import pytest_asyncio
from pathlib import Path

from src.kanban.scanner import scan_board, parse_yaml_frontmatter
from src.kanban.models import BoardState, SprintEntry, EpicEntry
from src.kanban import handlers


def _create_epic(kanban_dir: Path, status: str, epic_num: int, title: str):
    """Helper to create an epic folder with _epic.md."""
    epic_slug = title.lower().replace(" ", "-")
    epic_dir = kanban_dir / status / f"epic-{epic_num:02d}_{epic_slug}"
    epic_dir.mkdir(parents=True)
    epic_file = epic_dir / "_epic.md"
    epic_file.write_text(f"""---
epic: {epic_num}
title: "{title}"
status: planning
created: 2026-02-15
started: null
completed: null
---

# Epic {epic_num:02d}: {title}
""")
    return epic_dir


def _create_sprint(epic_dir: Path, sprint_num: int, title: str, epic_num: int):
    """Helper to create a sprint folder with spec."""
    sprint_slug = title.lower().replace(" ", "-")
    sprint_dir = epic_dir / f"sprint-{sprint_num:02d}_{sprint_slug}"
    sprint_dir.mkdir(parents=True)
    spec_file = sprint_dir / f"sprint-{sprint_num:02d}_{sprint_slug}.md"
    spec_file.write_text(f"""---
sprint: {sprint_num}
title: "{title}"
type: backend
epic: {epic_num}
status: planning
created: 2026-02-15T00:00:00Z
started: null
completed: null
hours: null
---

# Sprint {sprint_num:02d}: {title}

## Goal

Test sprint goal.
""")
    return sprint_dir


@pytest.fixture
def kanban_dir(tmp_path):
    """Create a kanban directory with status folders."""
    for folder in ["0-backlog", "1-todo", "2-in-progress", "3-done",
                    "4-blocked", "5-abandoned", "6-archived"]:
        (tmp_path / folder).mkdir()
    return tmp_path


@pytest.fixture
def populated_board(kanban_dir):
    """Create a board with 2 epics and 5 sprints."""
    epic1 = _create_epic(kanban_dir, "1-todo", 1, "First Epic")
    _create_sprint(epic1, 1, "Step Models", 1)
    _create_sprint(epic1, 2, "Protocol", 1)

    epic2 = _create_epic(kanban_dir, "2-in-progress", 2, "Second Epic")
    _create_sprint(epic2, 3, "Agent Base", 2)
    _create_sprint(epic2, 4, "Test Runner", 2)

    # A done epic
    epic3 = _create_epic(kanban_dir, "3-done", 3, "Done Epic")
    _create_sprint(epic3, 5, "Completed Work", 3)

    return kanban_dir


class TestParseYamlFrontmatter:
    def test_parses_valid_frontmatter(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text('---\ntitle: "Hello"\nstatus: todo\n---\n# Content')
        result = parse_yaml_frontmatter(f)
        assert result["title"] == "Hello"
        assert result["status"] == "todo"

    def test_returns_empty_for_no_frontmatter(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# Just a heading")
        assert parse_yaml_frontmatter(f) == {}

    def test_null_values_become_none(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("---\nstarted: null\n---\n")
        result = parse_yaml_frontmatter(f)
        assert result["started"] is None

    def test_missing_file_returns_empty(self, tmp_path):
        assert parse_yaml_frontmatter(tmp_path / "nope.md") == {}


class TestScanBoard:
    def test_empty_board(self, kanban_dir):
        state = scan_board(kanban_dir)
        assert state.epics == {}
        assert state.sprints == {}

    def test_finds_epics(self, populated_board):
        state = scan_board(populated_board)
        assert len(state.epics) == 3
        assert 1 in state.epics
        assert 2 in state.epics
        assert 3 in state.epics

    def test_epic_status_from_folder(self, populated_board):
        state = scan_board(populated_board)
        assert state.epics[1].status == "todo"
        assert state.epics[2].status == "in-progress"
        assert state.epics[3].status == "done"

    def test_finds_sprints(self, populated_board):
        state = scan_board(populated_board)
        assert len(state.sprints) == 5

    def test_sprint_epic_linkage(self, populated_board):
        state = scan_board(populated_board)
        assert state.sprints[1].epic == 1
        assert state.sprints[3].epic == 2

    def test_sprint_inherits_folder_status(self, populated_board):
        state = scan_board(populated_board)
        assert state.sprints[1].status == "todo"
        assert state.sprints[3].status == "in-progress"
        assert state.sprints[5].status == "done"

    def test_epic_sprint_counts(self, populated_board):
        state = scan_board(populated_board)
        assert state.epics[1].total_sprints == 2
        assert state.epics[1].completed_sprints == 0
        assert state.epics[3].total_sprints == 1
        assert state.epics[3].completed_sprints == 1

    def test_next_counters(self, populated_board):
        state = scan_board(populated_board)
        assert state.next_epic == 4
        assert state.next_sprint == 6

    def test_epic_sprint_numbers(self, populated_board):
        state = scan_board(populated_board)
        assert state.epics[1].sprint_numbers == [1, 2]
        assert state.epics[2].sprint_numbers == [3, 4]


class TestHandlers:
    async def test_get_board_status(self, populated_board):
        result = await handlers.get_board_status_handler({}, populated_board)
        text = result["content"][0]["text"]
        import json
        data = json.loads(text)
        assert data["sprint_count"] == 5
        assert "1" in data["epics"]
        assert data["next_sprint"] == 6

    async def test_get_board_epic(self, populated_board):
        result = await handlers.get_board_epic_handler({"epic_number": "1"}, populated_board)
        import json
        data = json.loads(result["content"][0]["text"])
        assert data["epic"]["title"] == "First Epic"
        assert len(data["sprints"]) == 2

    async def test_get_board_epic_not_found(self, populated_board):
        result = await handlers.get_board_epic_handler({"epic_number": "99"}, populated_board)
        assert "not found" in result["content"][0]["text"]

    async def test_get_board_sprint(self, populated_board):
        result = await handlers.get_board_sprint_handler({"sprint_number": "1"}, populated_board)
        import json
        data = json.loads(result["content"][0]["text"])
        assert data["sprint"]["title"] == "Step Models"
        assert "Goal" in data["spec"]

    async def test_get_board_sprint_not_found(self, populated_board):
        result = await handlers.get_board_sprint_handler({"sprint_number": "99"}, populated_board)
        assert "not found" in result["content"][0]["text"]

    async def test_list_board_sprints_all(self, populated_board):
        result = await handlers.list_board_sprints_handler({}, populated_board)
        import json
        data = json.loads(result["content"][0]["text"])
        assert len(data) == 5

    async def test_list_board_sprints_by_status(self, populated_board):
        result = await handlers.list_board_sprints_handler({"status": "todo"}, populated_board)
        import json
        data = json.loads(result["content"][0]["text"])
        assert len(data) == 2
        assert all(s["status"] == "todo" for s in data)

    async def test_list_board_sprints_by_epic(self, populated_board):
        result = await handlers.list_board_sprints_handler({"epic_number": "2"}, populated_board)
        import json
        data = json.loads(result["content"][0]["text"])
        assert len(data) == 2
        assert all(s["epic"] == 2 for s in data)
