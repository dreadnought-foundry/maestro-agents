"""Tests for KanbanAdapter — filesystem-backed WorkflowBackend.

Mirrors test_inmemory_lifecycle.py assertions but runs against the real
kanban filesystem in a temp directory.
"""

import pytest
from pathlib import Path

from src.adapters.kanban import KanbanAdapter
from src.workflow.exceptions import InvalidTransitionError
from src.workflow.models import SprintStatus, StepStatus


@pytest.fixture
def kanban_dir(tmp_path):
    """Create a temporary kanban directory structure."""
    for col in [
        "0-backlog", "1-todo", "2-in-progress", "3-review",
        "4-done", "5-blocked", "6-abandoned", "7-archived",
    ]:
        (tmp_path / "kanban" / col).mkdir(parents=True)
    # Also create .claude dir for state files
    (tmp_path / ".claude").mkdir()
    return tmp_path / "kanban"


@pytest.fixture
def adapter(kanban_dir):
    return KanbanAdapter(kanban_dir)


async def _make_sprint(adapter, tasks=None):
    """Helper: create an epic + sprint, optionally with tasks."""
    epic = await adapter.create_epic("Epic", "desc")
    sprint = await adapter.create_sprint(
        epic.id,
        "Sprint goal",
        tasks=tasks or [{"name": "Design"}, {"name": "Build"}, {"name": "Test"}],
    )
    return sprint


# ---------------------------------------------------------------------------
# create_epic / create_sprint
# ---------------------------------------------------------------------------
class TestCreateOperations:
    async def test_create_epic(self, adapter):
        epic = await adapter.create_epic("My Epic", "A test epic")
        assert epic.title == "My Epic"
        assert epic.description == "A test epic"
        assert epic.id.startswith("e-")

    async def test_get_epic_after_create(self, adapter):
        epic = await adapter.create_epic("My Epic", "desc")
        fetched = await adapter.get_epic(epic.id)
        assert fetched.title == "My Epic"

    async def test_create_sprint_in_epic(self, adapter):
        epic = await adapter.create_epic("Epic", "desc")
        sprint = await adapter.create_sprint(epic.id, "Do stuff", tasks=[{"name": "A"}])
        assert sprint.id.startswith("s-")
        assert sprint.goal == "Do stuff"
        assert sprint.status is SprintStatus.TODO
        assert sprint.epic_id == epic.id

    async def test_create_sprint_epic_not_found(self, adapter):
        with pytest.raises(KeyError):
            await adapter.create_sprint("e-999", "goal")

    async def test_get_sprint_after_create(self, adapter):
        sprint = await _make_sprint(adapter)
        fetched = await adapter.get_sprint(sprint.id)
        assert fetched.goal == "Sprint goal"

    async def test_list_sprints(self, adapter):
        sprint = await _make_sprint(adapter)
        sprints = await adapter.list_sprints()
        assert any(s.id == sprint.id for s in sprints)

    async def test_list_epics(self, adapter):
        await adapter.create_epic("A", "a")
        await adapter.create_epic("B", "b")
        epics = await adapter.list_epics()
        assert len(epics) >= 2


# ---------------------------------------------------------------------------
# start_sprint
# ---------------------------------------------------------------------------
class TestStartSprint:
    async def test_starts_todo_sprint(self, adapter):
        sprint = await _make_sprint(adapter)
        result = await adapter.start_sprint(sprint.id)
        assert result.status is SprintStatus.IN_PROGRESS

    async def test_creates_steps_from_tasks(self, adapter):
        sprint = await _make_sprint(adapter, tasks=[{"name": "A"}, {"name": "B"}])
        result = await adapter.start_sprint(sprint.id)
        assert len(result.steps) == 2
        assert result.steps[0].name == "A"
        assert result.steps[1].name == "B"
        assert result.steps[0].id == "step-1"
        assert result.steps[1].id == "step-2"

    async def test_first_step_becomes_in_progress(self, adapter):
        sprint = await _make_sprint(adapter)
        result = await adapter.start_sprint(sprint.id)
        assert result.steps[0].status is StepStatus.IN_PROGRESS
        assert result.steps[0].started_at is not None
        for step in result.steps[1:]:
            assert step.status is StepStatus.TODO

    async def test_records_transition(self, adapter):
        sprint = await _make_sprint(adapter)
        result = await adapter.start_sprint(sprint.id)
        assert len(result.transitions) == 1
        t = result.transitions[0]
        assert t.from_status is SprintStatus.TODO
        assert t.to_status is SprintStatus.IN_PROGRESS

    async def test_raises_for_non_todo_sprint(self, adapter):
        sprint = await _make_sprint(adapter)
        await adapter.start_sprint(sprint.id)
        with pytest.raises(InvalidTransitionError):
            await adapter.start_sprint(sprint.id)

    async def test_sprint_not_found_raises(self, adapter):
        with pytest.raises(KeyError):
            await adapter.start_sprint("s-999")

    async def test_persists_to_filesystem(self, adapter, kanban_dir):
        sprint = await _make_sprint(adapter)
        await adapter.start_sprint(sprint.id)
        # Sprint should be findable in 2-in-progress
        matches = list(kanban_dir.glob("2-in-progress/**/sprint-*.md"))
        assert len(matches) >= 1


# ---------------------------------------------------------------------------
# advance_step
# ---------------------------------------------------------------------------
class TestAdvanceStep:
    async def test_advances_to_next_step(self, adapter):
        sprint = await _make_sprint(adapter)
        await adapter.start_sprint(sprint.id)
        result = await adapter.advance_step(sprint.id)
        assert result.steps[0].status is StepStatus.DONE
        assert result.steps[1].status is StepStatus.IN_PROGRESS

    async def test_stores_output(self, adapter):
        sprint = await _make_sprint(adapter)
        await adapter.start_sprint(sprint.id)
        output = {"result": "success", "artifact": "file.txt"}
        result = await adapter.advance_step(sprint.id, step_output=output)
        assert result.steps[0].output == output

    async def test_sets_timestamps(self, adapter):
        sprint = await _make_sprint(adapter)
        await adapter.start_sprint(sprint.id)
        result = await adapter.advance_step(sprint.id)
        assert result.steps[0].completed_at is not None
        assert result.steps[1].started_at is not None

    async def test_raises_when_no_step_in_progress(self, adapter):
        sprint = await _make_sprint(adapter)
        await adapter.start_sprint(sprint.id)
        await adapter.advance_step(sprint.id)
        await adapter.advance_step(sprint.id)
        await adapter.advance_step(sprint.id)
        with pytest.raises(ValueError, match="No step currently in progress"):
            await adapter.advance_step(sprint.id)

    async def test_handles_last_step(self, adapter):
        sprint = await _make_sprint(adapter, tasks=[{"name": "Only"}])
        await adapter.start_sprint(sprint.id)
        result = await adapter.advance_step(sprint.id)
        assert result.steps[0].status is StepStatus.DONE

    async def test_sprint_not_found_raises(self, adapter):
        with pytest.raises(KeyError):
            await adapter.advance_step("s-999")


# ---------------------------------------------------------------------------
# complete_sprint
# ---------------------------------------------------------------------------
class TestCompleteSprint:
    async def test_completes_when_all_steps_done(self, adapter):
        sprint = await _make_sprint(adapter, tasks=[{"name": "A"}])
        await adapter.start_sprint(sprint.id)
        await adapter.advance_step(sprint.id)
        result = await adapter.complete_sprint(sprint.id)
        assert result.status is SprintStatus.DONE

    async def test_raises_when_steps_not_all_done(self, adapter):
        sprint = await _make_sprint(adapter)
        await adapter.start_sprint(sprint.id)
        with pytest.raises(ValueError, match="Not all steps are done"):
            await adapter.complete_sprint(sprint.id)

    async def test_raises_for_non_in_progress_sprint(self, adapter):
        sprint = await _make_sprint(adapter)
        with pytest.raises(InvalidTransitionError):
            await adapter.complete_sprint(sprint.id)

    async def test_records_transition(self, adapter):
        sprint = await _make_sprint(adapter, tasks=[{"name": "A"}])
        await adapter.start_sprint(sprint.id)
        await adapter.advance_step(sprint.id)
        result = await adapter.complete_sprint(sprint.id)
        done_t = result.transitions[-1]
        assert done_t.from_status is SprintStatus.IN_PROGRESS
        assert done_t.to_status is SprintStatus.DONE

    async def test_adds_done_suffix(self, adapter, kanban_dir):
        sprint = await _make_sprint(adapter, tasks=[{"name": "A"}])
        await adapter.start_sprint(sprint.id)
        await adapter.advance_step(sprint.id)
        await adapter.complete_sprint(sprint.id)
        # Should have --done suffix on filesystem
        done_files = list(kanban_dir.glob("**/*--done*"))
        assert len(done_files) >= 1


# ---------------------------------------------------------------------------
# block_sprint
# ---------------------------------------------------------------------------
class TestBlockSprint:
    async def test_blocks_in_progress_sprint(self, adapter):
        sprint = await _make_sprint(adapter)
        await adapter.start_sprint(sprint.id)
        result = await adapter.block_sprint(sprint.id, reason="Waiting on API key")
        assert result.status is SprintStatus.BLOCKED

    async def test_stores_reason_in_transition(self, adapter):
        sprint = await _make_sprint(adapter)
        await adapter.start_sprint(sprint.id)
        result = await adapter.block_sprint(sprint.id, reason="Dependency failed")
        t = result.transitions[-1]
        assert t.reason == "Dependency failed"

    async def test_raises_for_non_in_progress_sprint(self, adapter):
        sprint = await _make_sprint(adapter)
        with pytest.raises(InvalidTransitionError):
            await adapter.block_sprint(sprint.id, reason="nope")


# ---------------------------------------------------------------------------
# get_step_status
# ---------------------------------------------------------------------------
class TestGetStepStatus:
    async def test_returns_correct_progress(self, adapter):
        sprint = await _make_sprint(adapter)
        await adapter.start_sprint(sprint.id)
        status = await adapter.get_step_status(sprint.id)
        assert status["current_step"] == "Design"
        assert status["total_steps"] == 3
        assert status["completed_steps"] == 0
        assert status["progress_pct"] == 0.0
        assert len(status["steps"]) == 3

    async def test_handles_empty_steps(self, adapter):
        sprint = await _make_sprint(adapter, tasks=[])
        status = await adapter.get_step_status(sprint.id)
        assert status["current_step"] is None
        assert status["total_steps"] == 0

    async def test_handles_all_done(self, adapter):
        sprint = await _make_sprint(adapter, tasks=[{"name": "A"}])
        await adapter.start_sprint(sprint.id)
        await adapter.advance_step(sprint.id)
        status = await adapter.get_step_status(sprint.id)
        assert status["current_step"] is None
        assert status["completed_steps"] == 1
        assert status["progress_pct"] == 100.0


# ---------------------------------------------------------------------------
# get_project_state / get_status_summary
# ---------------------------------------------------------------------------
class TestProjectState:
    async def test_get_project_state(self, adapter):
        await _make_sprint(adapter)
        state = await adapter.get_project_state()
        assert len(state.epics) >= 1
        assert len(state.sprints) >= 1

    async def test_get_status_summary(self, adapter):
        sprint = await _make_sprint(adapter, tasks=[{"name": "A"}])
        await adapter.start_sprint(sprint.id)
        summary = await adapter.get_status_summary()
        assert summary["sprints_in_progress"] >= 1
        assert summary["total_sprints"] >= 1


# ---------------------------------------------------------------------------
# move_to_review
# ---------------------------------------------------------------------------
class TestMoveToReview:
    async def test_moves_to_review_when_steps_done(self, adapter):
        sprint = await _make_sprint(adapter, tasks=[{"name": "A"}])
        await adapter.start_sprint(sprint.id)
        await adapter.advance_step(sprint.id)
        result = await adapter.move_to_review(sprint.id)
        assert result.status is SprintStatus.REVIEW

    async def test_raises_when_steps_not_done(self, adapter):
        sprint = await _make_sprint(adapter)
        await adapter.start_sprint(sprint.id)
        with pytest.raises(ValueError, match="Not all steps are done"):
            await adapter.move_to_review(sprint.id)

    async def test_raises_for_non_in_progress(self, adapter):
        sprint = await _make_sprint(adapter)
        with pytest.raises(InvalidTransitionError):
            await adapter.move_to_review(sprint.id)

    async def test_moves_to_review_column(self, adapter, kanban_dir):
        sprint = await _make_sprint(adapter, tasks=[{"name": "A"}])
        await adapter.start_sprint(sprint.id)
        await adapter.advance_step(sprint.id)
        await adapter.move_to_review(sprint.id)
        review_files = list(kanban_dir.glob("3-review/**/sprint-*.md"))
        assert len(review_files) >= 1

    async def test_records_transition(self, adapter):
        sprint = await _make_sprint(adapter, tasks=[{"name": "A"}])
        await adapter.start_sprint(sprint.id)
        await adapter.advance_step(sprint.id)
        result = await adapter.move_to_review(sprint.id)
        t = result.transitions[-1]
        assert t.from_status is SprintStatus.IN_PROGRESS
        assert t.to_status is SprintStatus.REVIEW


# ---------------------------------------------------------------------------
# reject_sprint
# ---------------------------------------------------------------------------
class TestRejectSprint:
    async def test_rejects_review_sprint(self, adapter):
        sprint = await _make_sprint(adapter, tasks=[{"name": "A"}])
        await adapter.start_sprint(sprint.id)
        await adapter.advance_step(sprint.id)
        await adapter.move_to_review(sprint.id)
        result = await adapter.reject_sprint(sprint.id, reason="Needs more tests")
        assert result.status is SprintStatus.IN_PROGRESS

    async def test_stores_rejection_reason(self, adapter, kanban_dir):
        sprint = await _make_sprint(adapter, tasks=[{"name": "A"}])
        await adapter.start_sprint(sprint.id)
        await adapter.advance_step(sprint.id)
        await adapter.move_to_review(sprint.id)
        await adapter.reject_sprint(sprint.id, reason="Missing edge cases")
        # Check state file has rejection reason
        import json
        state_file = kanban_dir.parent / ".claude" / f"sprint-{sprint.id.split('-')[1]}-state.json"
        state = json.loads(state_file.read_text())
        assert state["rejection_reason"] == "Missing edge cases"
        assert len(state["rejection_history"]) == 1

    async def test_moves_back_to_in_progress(self, adapter, kanban_dir):
        sprint = await _make_sprint(adapter, tasks=[{"name": "A"}])
        await adapter.start_sprint(sprint.id)
        await adapter.advance_step(sprint.id)
        await adapter.move_to_review(sprint.id)
        await adapter.reject_sprint(sprint.id, reason="Fix bugs")
        in_progress_files = list(kanban_dir.glob("2-in-progress/**/sprint-*.md"))
        assert len(in_progress_files) >= 1

    async def test_raises_for_non_review_sprint(self, adapter):
        sprint = await _make_sprint(adapter)
        await adapter.start_sprint(sprint.id)
        with pytest.raises(InvalidTransitionError):
            await adapter.reject_sprint(sprint.id, reason="nope")


# ---------------------------------------------------------------------------
# Full lifecycle
# ---------------------------------------------------------------------------
class TestFullLifecycle:
    async def test_start_advance_complete(self, adapter):
        sprint = await _make_sprint(
            adapter, tasks=[{"name": "Plan"}, {"name": "Code"}, {"name": "Review"}]
        )

        sprint = await adapter.start_sprint(sprint.id)
        assert sprint.status is SprintStatus.IN_PROGRESS

        sprint = await adapter.advance_step(sprint.id, step_output={"plan": "done"})
        sprint = await adapter.advance_step(sprint.id, step_output={"code": "done"})
        sprint = await adapter.advance_step(sprint.id, step_output={"review": "done"})

        assert all(s.status is StepStatus.DONE for s in sprint.steps)

        sprint = await adapter.complete_sprint(sprint.id)
        assert sprint.status is SprintStatus.DONE
        # Note: transitions don't persist across filesystem reads (by design)
        # Each lifecycle call returns transitions from that call only
        assert len(sprint.transitions) >= 1

    async def test_start_block_resume_complete(self, adapter):
        sprint = await _make_sprint(adapter, tasks=[{"name": "Work"}])

        sprint = await adapter.start_sprint(sprint.id)
        sprint = await adapter.block_sprint(sprint.id, reason="Waiting")
        assert sprint.status is SprintStatus.BLOCKED

        # Resume via update_sprint
        from src.workflow.transitions import validate_transition
        validate_transition(sprint.id, SprintStatus.BLOCKED, SprintStatus.IN_PROGRESS)
        sprint = await adapter.update_sprint(sprint.id, status=SprintStatus.IN_PROGRESS)

        # Advance and complete
        sprint = await adapter.advance_step(sprint.id)
        sprint = await adapter.complete_sprint(sprint.id)
        assert sprint.status is SprintStatus.DONE

    async def test_start_advance_review_complete(self, adapter):
        """Full flow through review: start → advance → review → complete."""
        sprint = await _make_sprint(adapter, tasks=[{"name": "Work"}])
        sprint = await adapter.start_sprint(sprint.id)
        sprint = await adapter.advance_step(sprint.id)
        sprint = await adapter.move_to_review(sprint.id)
        assert sprint.status is SprintStatus.REVIEW
        sprint = await adapter.complete_sprint(sprint.id)
        assert sprint.status is SprintStatus.DONE

    async def test_review_reject_rework_review_complete(self, adapter):
        """Full rejection flow: review → reject → re-review → complete."""
        sprint = await _make_sprint(adapter, tasks=[{"name": "Code"}])
        sprint = await adapter.start_sprint(sprint.id)
        sprint = await adapter.advance_step(sprint.id)
        sprint = await adapter.move_to_review(sprint.id)
        assert sprint.status is SprintStatus.REVIEW

        sprint = await adapter.reject_sprint(sprint.id, reason="Needs tests")
        assert sprint.status is SprintStatus.IN_PROGRESS

        # Re-review (steps already done from before)
        sprint = await adapter.move_to_review(sprint.id)
        assert sprint.status is SprintStatus.REVIEW

        sprint = await adapter.complete_sprint(sprint.id)
        assert sprint.status is SprintStatus.DONE

    async def test_state_survives_new_adapter(self, kanban_dir):
        """State persists across adapter instances (filesystem-backed)."""
        adapter1 = KanbanAdapter(kanban_dir)
        sprint = await _make_sprint(adapter1, tasks=[{"name": "A"}])
        await adapter1.start_sprint(sprint.id)

        # Create a new adapter instance — state should survive
        adapter2 = KanbanAdapter(kanban_dir)
        fetched = await adapter2.get_sprint(sprint.id)
        assert fetched.status is SprintStatus.IN_PROGRESS
        assert len(fetched.steps) == 1
        assert fetched.steps[0].status is StepStatus.IN_PROGRESS
