"""Integration tests for kanban sprint/epic lifecycle.

These tests exercise BOTH the KanbanAdapter and the scanner together,
verifying that filesystem state, YAML frontmatter history, state files,
and scanner output all stay consistent through every lifecycle flow.
"""

import json

import pytest
from pathlib import Path

from src.adapters.kanban import KanbanAdapter
from src.workflow.exceptions import InvalidTransitionError
from src.workflow.models import SprintStatus, StepStatus
from kanban_tui.scanner import parse_frontmatter, scan_kanban


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

COLUMNS = [
    "0-backlog", "1-todo", "2-in-progress", "3-review",
    "4-done", "5-blocked", "6-abandoned", "7-archived",
]


@pytest.fixture
def kanban_dir(tmp_path):
    """Create a temporary kanban directory with all columns + .claude."""
    for col in COLUMNS:
        (tmp_path / "kanban" / col).mkdir(parents=True)
    (tmp_path / ".claude").mkdir()
    return tmp_path / "kanban"


@pytest.fixture
def adapter(kanban_dir):
    return KanbanAdapter(kanban_dir)


def _state_file(kanban_dir: Path, sprint_id: str) -> Path:
    num = int(sprint_id.split("-")[1])
    return kanban_dir.parent / ".claude" / f"sprint-{num}-state.json"


def _read_state(kanban_dir: Path, sprint_id: str) -> dict:
    return json.loads(_state_file(kanban_dir, sprint_id).read_text())


def _find_sprint_md(kanban_dir: Path, sprint_id: str) -> Path:
    """Find the sprint .md file across all columns (skipping artifacts)."""
    num = int(sprint_id.split("-")[1])
    pattern = f"**/sprint-{num:02d}_*.md"
    for p in kanban_dir.glob(pattern):
        if not any(s in p.name for s in ["_postmortem", "_quality", "_contracts", "_deferred"]):
            return p
    raise FileNotFoundError(f"Sprint file not found for {sprint_id}")


def _sprint_column(kanban_dir: Path, sprint_id: str) -> str:
    """Return the column directory name a sprint currently lives in."""
    md = _find_sprint_md(kanban_dir, sprint_id)
    for part in md.parts:
        if part in COLUMNS:
            return part
    raise ValueError(f"Cannot determine column for {sprint_id}")


def _scanner_sprint_column(kanban_dir: Path, sprint_id: str) -> str:
    """Use the scanner to find which column a sprint appears in."""
    num = int(sprint_id.split("-")[1])
    columns = scan_kanban(kanban_dir)
    for col in columns:
        for epic in col.epics:
            for sp in epic.sprints:
                if sp.number == num:
                    return col.name
        for sp in col.standalone_sprints:
            if sp.number == num:
                return col.name
    raise ValueError(f"Scanner did not find sprint {sprint_id}")


def _scanner_sprint_status(kanban_dir: Path, sprint_id: str) -> str:
    """Use the scanner to get a sprint's status string."""
    num = int(sprint_id.split("-")[1])
    columns = scan_kanban(kanban_dir)
    for col in columns:
        for epic in col.epics:
            for sp in epic.sprints:
                if sp.number == num:
                    return sp.status
        for sp in col.standalone_sprints:
            if sp.number == num:
                return sp.status
    raise ValueError(f"Scanner did not find sprint {sprint_id}")


def _make_standalone_sprint(kanban_dir, sprint_num=37, title="Solo Sprint", tasks=None):
    """Create a standalone sprint folder in 1-todo (no epic)."""
    slug = title.lower().replace(" ", "-")
    sprint_dir = kanban_dir / "1-todo" / f"sprint-{sprint_num:02d}_{slug}"
    sprint_dir.mkdir(parents=True, exist_ok=True)
    md = sprint_dir / f"sprint-{sprint_num:02d}_{slug}.md"
    task_lines = ""
    if tasks:
        task_lines = "\n".join(f"- [ ] {t['name']}" for t in tasks)
    md.write_text(
        f"---\nsprint: {sprint_num}\ntitle: \"{title}\"\ntype: refactor\n"
        f"epic: null\ncreated: 2026-02-21T00:00:00Z\n"
        "started: null\ncompleted: null\n---\n\n"
        f"# Sprint {sprint_num}: {title}\n\n## Tasks\n\n{task_lines}\n"
    )
    return f"s-{sprint_num}"


async def _create_epic_sprint(adapter, tasks=None):
    """Create an epic with one sprint. Returns (epic, sprint)."""
    epic = await adapter.create_epic("Test Epic", "Integration test epic")
    sprint = await adapter.create_sprint(
        epic.id,
        "Sprint goal",
        tasks=tasks or [{"name": "Design"}, {"name": "Build"}, {"name": "Test"}],
    )
    return epic, sprint


async def _run_all_steps(adapter, sprint_id, num_steps):
    """Advance through all steps of a sprint."""
    for _ in range(num_steps):
        await adapter.advance_step(sprint_id)


# ---------------------------------------------------------------------------
# 1. Epic-nested sprint happy path
# ---------------------------------------------------------------------------
class TestEpicSprintHappyPath:

    async def test_full_lifecycle(self, adapter, kanban_dir):
        """create_epic → create_sprint → start → advance(×3) → review → complete"""
        epic, sprint = await _create_epic_sprint(adapter)

        # After creation: sprint in 1-todo
        assert (await adapter.get_sprint(sprint.id)).status is SprintStatus.TODO
        assert _sprint_column(kanban_dir, sprint.id) == "1-todo"
        assert _scanner_sprint_column(kanban_dir, sprint.id) == "1-todo"

        # Start
        await adapter.start_sprint(sprint.id)
        assert (await adapter.get_sprint(sprint.id)).status is SprintStatus.IN_PROGRESS
        assert _sprint_column(kanban_dir, sprint.id) == "2-in-progress"
        assert _scanner_sprint_column(kanban_dir, sprint.id) == "2-in-progress"

        # State file created with steps
        state = _read_state(kanban_dir, sprint.id)
        assert state["status"] == "in_progress"
        assert len(state["steps"]) == 3
        assert state["steps"][0]["status"] == "in_progress"

        # Advance all 3 steps
        await _run_all_steps(adapter, sprint.id, 3)
        state = _read_state(kanban_dir, sprint.id)
        assert all(s["status"] == "done" for s in state["steps"])

        # Move to review
        await adapter.move_to_review(sprint.id)
        assert (await adapter.get_sprint(sprint.id)).status is SprintStatus.REVIEW
        assert _sprint_column(kanban_dir, sprint.id) == "3-review"
        assert _scanner_sprint_column(kanban_dir, sprint.id) == "3-review"

        # Complete
        await adapter.complete_sprint(sprint.id)
        assert (await adapter.get_sprint(sprint.id)).status is SprintStatus.DONE
        assert _sprint_column(kanban_dir, sprint.id) == "4-done"
        assert _scanner_sprint_column(kanban_dir, sprint.id) == "4-done"

        state = _read_state(kanban_dir, sprint.id)
        assert state["status"] == "done"
        assert "completed_at" in state

    async def test_history_accumulates(self, adapter, kanban_dir):
        """History entries accumulate in YAML frontmatter at each transition."""
        _, sprint = await _create_epic_sprint(adapter, tasks=[{"name": "Work"}])

        await adapter.start_sprint(sprint.id)
        await adapter.advance_step(sprint.id)
        await adapter.move_to_review(sprint.id)
        await adapter.complete_sprint(sprint.id)

        md = _find_sprint_md(kanban_dir, sprint.id)
        fm = parse_frontmatter(md)
        history = fm.get("history", [])
        # start (2-in-progress), review (3-review), complete (4-done)
        assert len(history) >= 3
        columns_visited = [h["column"] for h in history]
        assert "2-in-progress" in columns_visited
        assert "3-review" in columns_visited
        assert "4-done" in columns_visited

    async def test_epic_follows_sprint_column(self, adapter, kanban_dir):
        """Epic dir physically lives in the same column as its sprint."""
        epic, sprint = await _create_epic_sprint(adapter, tasks=[{"name": "A"}])

        await adapter.start_sprint(sprint.id)
        # Epic dir should be in 2-in-progress
        epic_dirs = list((kanban_dir / "2-in-progress").glob("epic-*"))
        assert len(epic_dirs) >= 1

        await adapter.advance_step(sprint.id)
        await adapter.move_to_review(sprint.id)
        epic_dirs = list((kanban_dir / "3-review").glob("epic-*"))
        assert len(epic_dirs) >= 1


# ---------------------------------------------------------------------------
# 2. Standalone sprint happy path
# ---------------------------------------------------------------------------
class TestStandaloneSprintHappyPath:

    async def test_full_lifecycle(self, adapter, kanban_dir):
        """Standalone sprint: start → advance → review → complete."""
        sprint_id = _make_standalone_sprint(kanban_dir, tasks=[{"name": "Build"}])

        assert _sprint_column(kanban_dir, sprint_id) == "1-todo"
        assert _scanner_sprint_column(kanban_dir, sprint_id) == "1-todo"

        await adapter.start_sprint(sprint_id)
        assert _sprint_column(kanban_dir, sprint_id) == "2-in-progress"
        assert _scanner_sprint_column(kanban_dir, sprint_id) == "2-in-progress"

        await adapter.advance_step(sprint_id)
        await adapter.move_to_review(sprint_id)
        assert _sprint_column(kanban_dir, sprint_id) == "3-review"

        await adapter.complete_sprint(sprint_id)
        assert _sprint_column(kanban_dir, sprint_id) == "4-done"
        assert _scanner_sprint_column(kanban_dir, sprint_id) == "4-done"

    async def test_scanner_finds_as_standalone(self, adapter, kanban_dir):
        """Scanner reports standalone sprint as standalone (not under any epic)."""
        sprint_id = _make_standalone_sprint(kanban_dir, tasks=[{"name": "A"}])

        columns = scan_kanban(kanban_dir)
        todo_col = next(c for c in columns if c.name == "1-todo")
        assert any(sp.number == 37 for sp in todo_col.standalone_sprints)
        # Should NOT appear in any epic
        for col in columns:
            for epic in col.epics:
                assert not any(sp.number == 37 for sp in epic.sprints)

    async def test_history_and_state(self, adapter, kanban_dir):
        """History and state file are correct after full lifecycle."""
        sprint_id = _make_standalone_sprint(kanban_dir, tasks=[{"name": "Work"}])

        await adapter.start_sprint(sprint_id)
        await adapter.advance_step(sprint_id)
        await adapter.move_to_review(sprint_id)
        await adapter.complete_sprint(sprint_id)

        # State file
        state = _read_state(kanban_dir, sprint_id)
        assert state["status"] == "done"
        assert "completed_at" in state

        # History
        md = _find_sprint_md(kanban_dir, sprint_id)
        fm = parse_frontmatter(md)
        history = fm.get("history", [])
        assert len(history) >= 3


# ---------------------------------------------------------------------------
# 3. Review → reject → rework → complete
# ---------------------------------------------------------------------------
class TestReviewRejectReworkFlow:

    async def test_reject_and_rework(self, adapter, kanban_dir):
        """start → advance → review → reject → review → complete"""
        _, sprint = await _create_epic_sprint(adapter, tasks=[{"name": "Code"}])

        await adapter.start_sprint(sprint.id)
        await adapter.advance_step(sprint.id)
        await adapter.move_to_review(sprint.id)
        assert _sprint_column(kanban_dir, sprint.id) == "3-review"

        # Reject
        await adapter.reject_sprint(sprint.id, reason="Missing edge cases")
        assert (await adapter.get_sprint(sprint.id)).status is SprintStatus.IN_PROGRESS
        assert _sprint_column(kanban_dir, sprint.id) == "2-in-progress"
        assert _scanner_sprint_column(kanban_dir, sprint.id) == "2-in-progress"

        # State file has rejection
        state = _read_state(kanban_dir, sprint.id)
        assert state["rejection_reason"] == "Missing edge cases"
        assert len(state["rejection_history"]) == 1

        # Re-review (steps already done)
        await adapter.move_to_review(sprint.id)
        assert _sprint_column(kanban_dir, sprint.id) == "3-review"

        # Complete
        await adapter.complete_sprint(sprint.id)
        assert _sprint_column(kanban_dir, sprint.id) == "4-done"

        # History: in-progress, review, in-progress (reject), review, done
        md = _find_sprint_md(kanban_dir, sprint.id)
        fm = parse_frontmatter(md)
        history = fm.get("history", [])
        cols = [h["column"] for h in history]
        assert cols == [
            "2-in-progress", "3-review", "2-in-progress", "3-review", "4-done"
        ]


# ---------------------------------------------------------------------------
# 4. Multiple rejections
# ---------------------------------------------------------------------------
class TestMultipleRejectionsFlow:

    async def test_two_rejections(self, adapter, kanban_dir):
        """start → advance → review → reject → review → reject → review → complete"""
        _, sprint = await _create_epic_sprint(adapter, tasks=[{"name": "Code"}])

        await adapter.start_sprint(sprint.id)
        await adapter.advance_step(sprint.id)

        # First rejection cycle
        await adapter.move_to_review(sprint.id)
        await adapter.reject_sprint(sprint.id, reason="Reason 1")

        # Second rejection cycle
        await adapter.move_to_review(sprint.id)
        await adapter.reject_sprint(sprint.id, reason="Reason 2")

        # Finally complete
        await adapter.move_to_review(sprint.id)
        await adapter.complete_sprint(sprint.id)

        assert _sprint_column(kanban_dir, sprint.id) == "4-done"

        # State file has 2 rejection entries
        state = _read_state(kanban_dir, sprint.id)
        assert len(state["rejection_history"]) == 2
        assert state["rejection_history"][0]["reason"] == "Reason 1"
        assert state["rejection_history"][1]["reason"] == "Reason 2"

        # History: start, review, reject, review, reject, review, done = 7
        md = _find_sprint_md(kanban_dir, sprint.id)
        fm = parse_frontmatter(md)
        history = fm.get("history", [])
        assert len(history) == 7
        assert [h["column"] for h in history] == [
            "2-in-progress",  # start
            "3-review",       # first review
            "2-in-progress",  # reject 1
            "3-review",       # second review
            "2-in-progress",  # reject 2
            "3-review",       # third review
            "4-done",         # complete
        ]


# ---------------------------------------------------------------------------
# 5. Block and resume
# ---------------------------------------------------------------------------
class TestBlockAndResumeFlow:

    async def test_block_resume_complete(self, adapter, kanban_dir):
        """start → block → resume → advance → review → complete"""
        _, sprint = await _create_epic_sprint(adapter, tasks=[{"name": "Work"}])

        await adapter.start_sprint(sprint.id)

        # Block
        await adapter.block_sprint(sprint.id, reason="Waiting on API key")
        assert (await adapter.get_sprint(sprint.id)).status is SprintStatus.BLOCKED
        assert _sprint_column(kanban_dir, sprint.id) == "5-blocked"
        assert _scanner_sprint_column(kanban_dir, sprint.id) == "5-blocked"

        state = _read_state(kanban_dir, sprint.id)
        assert state["blocker"] == "Waiting on API key"

        # Resume via update_sprint
        await adapter.update_sprint(sprint.id, status=SprintStatus.IN_PROGRESS)
        assert (await adapter.get_sprint(sprint.id)).status is SprintStatus.IN_PROGRESS
        assert _sprint_column(kanban_dir, sprint.id) == "2-in-progress"
        assert _scanner_sprint_column(kanban_dir, sprint.id) == "2-in-progress"

        # Advance and complete
        await adapter.advance_step(sprint.id)
        await adapter.move_to_review(sprint.id)
        await adapter.complete_sprint(sprint.id)
        assert _sprint_column(kanban_dir, sprint.id) == "4-done"


# ---------------------------------------------------------------------------
# 6. Complex multi-transition: block → resume → review → reject → complete
# ---------------------------------------------------------------------------
class TestBlockResumeReviewRejectFlow:

    async def test_complex_flow(self, adapter, kanban_dir):
        """start → block → resume → advance → review → reject → review → complete"""
        _, sprint = await _create_epic_sprint(adapter, tasks=[{"name": "Build"}])

        await adapter.start_sprint(sprint.id)
        await adapter.block_sprint(sprint.id, reason="Dep missing")
        await adapter.update_sprint(sprint.id, status=SprintStatus.IN_PROGRESS)
        await adapter.advance_step(sprint.id)
        await adapter.move_to_review(sprint.id)
        await adapter.reject_sprint(sprint.id, reason="Needs polish")
        await adapter.move_to_review(sprint.id)
        await adapter.complete_sprint(sprint.id)

        assert (await adapter.get_sprint(sprint.id)).status is SprintStatus.DONE
        assert _sprint_column(kanban_dir, sprint.id) == "4-done"

        # Verify history captures all transitions
        md = _find_sprint_md(kanban_dir, sprint.id)
        fm = parse_frontmatter(md)
        history = fm.get("history", [])
        cols = [h["column"] for h in history]
        assert "5-blocked" in cols
        assert "2-in-progress" in cols
        assert "3-review" in cols
        assert "4-done" in cols
        assert cols[-1] == "4-done"


# ---------------------------------------------------------------------------
# 7. Invalid transitions
# ---------------------------------------------------------------------------
class TestInvalidTransitions:

    async def test_cannot_start_already_started(self, adapter, kanban_dir):
        _, sprint = await _create_epic_sprint(adapter, tasks=[{"name": "A"}])
        await adapter.start_sprint(sprint.id)
        with pytest.raises(InvalidTransitionError):
            await adapter.start_sprint(sprint.id)
        # Sprint stays in in-progress
        assert _sprint_column(kanban_dir, sprint.id) == "2-in-progress"

    async def test_cannot_complete_with_incomplete_steps(self, adapter, kanban_dir):
        _, sprint = await _create_epic_sprint(adapter)
        await adapter.start_sprint(sprint.id)
        # Only advance 1 of 3 steps
        await adapter.advance_step(sprint.id)
        with pytest.raises(ValueError, match="Not all steps are done"):
            await adapter.complete_sprint(sprint.id)
        assert _sprint_column(kanban_dir, sprint.id) == "2-in-progress"

    async def test_cannot_block_todo_sprint(self, adapter, kanban_dir):
        _, sprint = await _create_epic_sprint(adapter)
        with pytest.raises(InvalidTransitionError):
            await adapter.block_sprint(sprint.id, reason="nope")
        assert _sprint_column(kanban_dir, sprint.id) == "1-todo"

    async def test_cannot_reject_non_review_sprint(self, adapter, kanban_dir):
        _, sprint = await _create_epic_sprint(adapter, tasks=[{"name": "A"}])
        await adapter.start_sprint(sprint.id)
        with pytest.raises(InvalidTransitionError):
            await adapter.reject_sprint(sprint.id, reason="nope")
        assert _sprint_column(kanban_dir, sprint.id) == "2-in-progress"

    async def test_cannot_review_todo_sprint(self, adapter, kanban_dir):
        _, sprint = await _create_epic_sprint(adapter)
        with pytest.raises(InvalidTransitionError):
            await adapter.move_to_review(sprint.id)
        assert _sprint_column(kanban_dir, sprint.id) == "1-todo"


# ---------------------------------------------------------------------------
# 8. State persistence across adapter instances
# ---------------------------------------------------------------------------
class TestStatePersistenceAcrossAdapterInstances:

    async def test_survives_adapter_recreation(self, kanban_dir):
        """Start with adapter1, advance with adapter2, complete with adapter3."""
        adapter1 = KanbanAdapter(kanban_dir)
        epic, sprint = await _create_epic_sprint(adapter1, tasks=[{"name": "A"}])
        await adapter1.start_sprint(sprint.id)

        # New adapter sees in-progress sprint with step
        adapter2 = KanbanAdapter(kanban_dir)
        fetched = await adapter2.get_sprint(sprint.id)
        assert fetched.status is SprintStatus.IN_PROGRESS
        assert len(fetched.steps) == 1
        assert fetched.steps[0].status is StepStatus.IN_PROGRESS

        # Scanner also agrees
        assert _scanner_sprint_column(kanban_dir, sprint.id) == "2-in-progress"

        # Advance with adapter2
        await adapter2.advance_step(sprint.id)

        # Complete with adapter3
        adapter3 = KanbanAdapter(kanban_dir)
        await adapter3.move_to_review(sprint.id)
        await adapter3.complete_sprint(sprint.id)

        assert (await adapter3.get_sprint(sprint.id)).status is SprintStatus.DONE
        assert _sprint_column(kanban_dir, sprint.id) == "4-done"
        assert _scanner_sprint_column(kanban_dir, sprint.id) == "4-done"


# ---------------------------------------------------------------------------
# 9. Multiple sprints in one epic
# ---------------------------------------------------------------------------
class TestMultipleSprintsInEpic:

    async def test_multiple_sprints_tracked(self, adapter, kanban_dir):
        """Create 3 sprints in one epic, start and complete first, start second."""
        epic = await adapter.create_epic("Multi-Sprint Epic", "desc")
        s1 = await adapter.create_sprint(epic.id, "Sprint 1", tasks=[{"name": "A"}])
        s2 = await adapter.create_sprint(epic.id, "Sprint 2", tasks=[{"name": "B"}])
        s3 = await adapter.create_sprint(epic.id, "Sprint 3", tasks=[{"name": "C"}])

        # Start and complete sprint 1
        await adapter.start_sprint(s1.id)
        await adapter.advance_step(s1.id)
        await adapter.move_to_review(s1.id)
        await adapter.complete_sprint(s1.id)

        # Start sprint 2
        await adapter.start_sprint(s2.id)

        # Verify via adapter
        assert (await adapter.get_sprint(s1.id)).status is SprintStatus.DONE
        assert (await adapter.get_sprint(s2.id)).status is SprintStatus.IN_PROGRESS
        assert (await adapter.get_sprint(s3.id)).status is SprintStatus.TODO

        # Verify sprint 3 is still in todo
        # Note: epic-nested sprints all live in the same epic dir,
        # which gets moved as a unit. After completing s1 the epic moved to 4-done,
        # then starting s2 moves it to 2-in-progress. s3 is also in that dir.
        assert _sprint_column(kanban_dir, s2.id) == "2-in-progress"

    async def test_all_sprints_listed_for_epic(self, adapter, kanban_dir):
        """All sprints in an epic are returned by list_sprints(epic_id)."""
        epic = await adapter.create_epic("Multi", "desc")
        s1 = await adapter.create_sprint(epic.id, "S1", tasks=[{"name": "A"}])
        s2 = await adapter.create_sprint(epic.id, "S2", tasks=[{"name": "B"}])

        sprints = await adapter.list_sprints(epic_id=epic.id)
        sprint_ids = {s.id for s in sprints}
        assert s1.id in sprint_ids
        assert s2.id in sprint_ids


# ---------------------------------------------------------------------------
# 10. Scanner ↔ Adapter consistency
# ---------------------------------------------------------------------------
class TestScannerAdapterConsistency:

    async def test_status_matches_through_transitions(self, adapter, kanban_dir):
        """At each transition, adapter status and scanner column agree."""
        _, sprint = await _create_epic_sprint(adapter, tasks=[{"name": "Task"}])

        # Map of SprintStatus → expected scanner status string
        status_to_scanner = {
            SprintStatus.TODO: "todo",
            SprintStatus.IN_PROGRESS: "in-progress",
            SprintStatus.REVIEW: "review",
            SprintStatus.DONE: "done",
            SprintStatus.BLOCKED: "blocked",
        }
        column_to_scanner_status = {
            "1-todo": "todo",
            "2-in-progress": "in-progress",
            "3-review": "review",
            "4-done": "done",
            "5-blocked": "blocked",
        }

        # TODO
        adapter_sprint = await adapter.get_sprint(sprint.id)
        assert adapter_sprint.status is SprintStatus.TODO
        assert _scanner_sprint_status(kanban_dir, sprint.id) == "todo"

        # IN_PROGRESS
        await adapter.start_sprint(sprint.id)
        adapter_sprint = await adapter.get_sprint(sprint.id)
        assert adapter_sprint.status is SprintStatus.IN_PROGRESS
        assert _scanner_sprint_status(kanban_dir, sprint.id) == "in-progress"

        # BLOCKED
        await adapter.block_sprint(sprint.id, reason="blocked")
        adapter_sprint = await adapter.get_sprint(sprint.id)
        assert adapter_sprint.status is SprintStatus.BLOCKED
        assert _scanner_sprint_status(kanban_dir, sprint.id) == "blocked"

        # Resume → IN_PROGRESS
        await adapter.update_sprint(sprint.id, status=SprintStatus.IN_PROGRESS)
        adapter_sprint = await adapter.get_sprint(sprint.id)
        assert adapter_sprint.status is SprintStatus.IN_PROGRESS
        assert _scanner_sprint_status(kanban_dir, sprint.id) == "in-progress"

        # Advance → REVIEW
        await adapter.advance_step(sprint.id)
        await adapter.move_to_review(sprint.id)
        adapter_sprint = await adapter.get_sprint(sprint.id)
        assert adapter_sprint.status is SprintStatus.REVIEW
        assert _scanner_sprint_status(kanban_dir, sprint.id) == "review"

        # DONE
        await adapter.complete_sprint(sprint.id)
        adapter_sprint = await adapter.get_sprint(sprint.id)
        assert adapter_sprint.status is SprintStatus.DONE
        assert _scanner_sprint_status(kanban_dir, sprint.id) == "done"
