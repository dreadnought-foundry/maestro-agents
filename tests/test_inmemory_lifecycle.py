"""Unit tests for InMemoryAdapter lifecycle methods (Sprint 11)."""

import pytest

from src.adapters.memory import InMemoryAdapter
from src.workflow.exceptions import InvalidTransitionError
from src.workflow.models import SprintStatus, StepStatus


@pytest.fixture
def adapter():
    return InMemoryAdapter(project_name="test-project")


async def _make_sprint(adapter, tasks=None, steps=None):
    """Helper: create an epic + sprint, optionally with tasks/steps."""
    epic = await adapter.create_epic("Epic", "desc")
    sprint = await adapter.create_sprint(
        epic.id,
        "Sprint goal",
        tasks=tasks or [{"name": "Design"}, {"name": "Build"}, {"name": "Test"}],
    )
    if steps is not None:
        sprint.steps = steps
    return sprint


# ---------------------------------------------------------------------------
# start_sprint
# ---------------------------------------------------------------------------
class TestStartSprint:
    @pytest.mark.asyncio
    async def test_starts_todo_sprint(self, adapter):
        sprint = await _make_sprint(adapter)
        result = await adapter.start_sprint(sprint.id)
        assert result.status is SprintStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_creates_steps_from_tasks(self, adapter):
        sprint = await _make_sprint(adapter, tasks=[{"name": "A"}, {"name": "B"}])
        result = await adapter.start_sprint(sprint.id)
        assert len(result.steps) == 2
        assert result.steps[0].name == "A"
        assert result.steps[1].name == "B"
        assert result.steps[0].id == "step-1"
        assert result.steps[1].id == "step-2"

    @pytest.mark.asyncio
    async def test_first_step_becomes_in_progress(self, adapter):
        sprint = await _make_sprint(adapter)
        result = await adapter.start_sprint(sprint.id)
        assert result.steps[0].status is StepStatus.IN_PROGRESS
        assert result.steps[0].started_at is not None
        # remaining steps stay TODO
        for step in result.steps[1:]:
            assert step.status is StepStatus.TODO

    @pytest.mark.asyncio
    async def test_records_transition(self, adapter):
        sprint = await _make_sprint(adapter)
        result = await adapter.start_sprint(sprint.id)
        assert len(result.transitions) == 1
        t = result.transitions[0]
        assert t.from_status is SprintStatus.TODO
        assert t.to_status is SprintStatus.IN_PROGRESS
        assert t.timestamp is not None

    @pytest.mark.asyncio
    async def test_raises_for_non_todo_sprint(self, adapter):
        sprint = await _make_sprint(adapter)
        await adapter.start_sprint(sprint.id)
        with pytest.raises(InvalidTransitionError):
            await adapter.start_sprint(sprint.id)

    @pytest.mark.asyncio
    async def test_preserves_existing_steps(self, adapter):
        """If sprint already has steps, don't recreate from tasks."""
        from src.workflow.models import Step

        sprint = await _make_sprint(adapter, tasks=[{"name": "A"}])
        existing_steps = [
            Step(id="custom-1", name="Custom Step"),
            Step(id="custom-2", name="Custom Step 2"),
        ]
        sprint.steps = existing_steps
        result = await adapter.start_sprint(sprint.id)
        assert len(result.steps) == 2
        assert result.steps[0].id == "custom-1"

    @pytest.mark.asyncio
    async def test_sprint_not_found_raises(self, adapter):
        with pytest.raises(KeyError):
            await adapter.start_sprint("s-999")


# ---------------------------------------------------------------------------
# advance_step
# ---------------------------------------------------------------------------
class TestAdvanceStep:
    @pytest.mark.asyncio
    async def test_advances_to_next_step(self, adapter):
        sprint = await _make_sprint(adapter)
        await adapter.start_sprint(sprint.id)
        result = await adapter.advance_step(sprint.id)
        assert result.steps[0].status is StepStatus.DONE
        assert result.steps[1].status is StepStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_stores_output(self, adapter):
        sprint = await _make_sprint(adapter)
        await adapter.start_sprint(sprint.id)
        output = {"result": "success", "artifact": "file.txt"}
        result = await adapter.advance_step(sprint.id, step_output=output)
        assert result.steps[0].output == output

    @pytest.mark.asyncio
    async def test_sets_timestamps(self, adapter):
        sprint = await _make_sprint(adapter)
        await adapter.start_sprint(sprint.id)
        result = await adapter.advance_step(sprint.id)
        assert result.steps[0].completed_at is not None
        assert result.steps[1].started_at is not None

    @pytest.mark.asyncio
    async def test_raises_when_no_step_in_progress(self, adapter):
        sprint = await _make_sprint(adapter)
        await adapter.start_sprint(sprint.id)
        # Advance all three steps
        await adapter.advance_step(sprint.id)
        await adapter.advance_step(sprint.id)
        await adapter.advance_step(sprint.id)  # last step done, no next
        with pytest.raises(ValueError, match="No step currently in progress"):
            await adapter.advance_step(sprint.id)

    @pytest.mark.asyncio
    async def test_handles_last_step(self, adapter):
        sprint = await _make_sprint(adapter, tasks=[{"name": "Only"}])
        await adapter.start_sprint(sprint.id)
        result = await adapter.advance_step(sprint.id)
        assert result.steps[0].status is StepStatus.DONE
        # No next step, no error

    @pytest.mark.asyncio
    async def test_sprint_not_found_raises(self, adapter):
        with pytest.raises(KeyError):
            await adapter.advance_step("s-999")


# ---------------------------------------------------------------------------
# complete_sprint
# ---------------------------------------------------------------------------
class TestCompleteSprint:
    @pytest.mark.asyncio
    async def test_completes_when_all_steps_done(self, adapter):
        sprint = await _make_sprint(adapter, tasks=[{"name": "A"}])
        await adapter.start_sprint(sprint.id)
        await adapter.advance_step(sprint.id)
        result = await adapter.complete_sprint(sprint.id)
        assert result.status is SprintStatus.DONE

    @pytest.mark.asyncio
    async def test_raises_when_steps_not_all_done(self, adapter):
        sprint = await _make_sprint(adapter)
        await adapter.start_sprint(sprint.id)
        with pytest.raises(ValueError, match="Not all steps are done"):
            await adapter.complete_sprint(sprint.id)

    @pytest.mark.asyncio
    async def test_raises_for_non_in_progress_sprint(self, adapter):
        sprint = await _make_sprint(adapter)
        with pytest.raises(InvalidTransitionError):
            await adapter.complete_sprint(sprint.id)

    @pytest.mark.asyncio
    async def test_records_transition(self, adapter):
        sprint = await _make_sprint(adapter, tasks=[{"name": "A"}])
        await adapter.start_sprint(sprint.id)
        await adapter.advance_step(sprint.id)
        result = await adapter.complete_sprint(sprint.id)
        done_transition = result.transitions[-1]
        assert done_transition.from_status is SprintStatus.IN_PROGRESS
        assert done_transition.to_status is SprintStatus.DONE

    @pytest.mark.asyncio
    async def test_accepts_skipped_steps(self, adapter):
        """SKIPPED steps count as complete for completion check."""
        sprint = await _make_sprint(adapter, tasks=[{"name": "A"}, {"name": "B"}])
        await adapter.start_sprint(sprint.id)
        await adapter.advance_step(sprint.id)
        # Manually skip the second step
        sprint.steps[1].status = StepStatus.SKIPPED
        result = await adapter.complete_sprint(sprint.id)
        assert result.status is SprintStatus.DONE


# ---------------------------------------------------------------------------
# block_sprint
# ---------------------------------------------------------------------------
class TestBlockSprint:
    @pytest.mark.asyncio
    async def test_blocks_in_progress_sprint(self, adapter):
        sprint = await _make_sprint(adapter)
        await adapter.start_sprint(sprint.id)
        result = await adapter.block_sprint(sprint.id, reason="Waiting on API key")
        assert result.status is SprintStatus.BLOCKED

    @pytest.mark.asyncio
    async def test_stores_reason_in_transition(self, adapter):
        sprint = await _make_sprint(adapter)
        await adapter.start_sprint(sprint.id)
        result = await adapter.block_sprint(sprint.id, reason="Dependency failed")
        t = result.transitions[-1]
        assert t.reason == "Dependency failed"
        assert t.from_status is SprintStatus.IN_PROGRESS
        assert t.to_status is SprintStatus.BLOCKED

    @pytest.mark.asyncio
    async def test_raises_for_non_in_progress_sprint(self, adapter):
        sprint = await _make_sprint(adapter)
        with pytest.raises(InvalidTransitionError):
            await adapter.block_sprint(sprint.id, reason="nope")


# ---------------------------------------------------------------------------
# get_step_status
# ---------------------------------------------------------------------------
class TestGetStepStatus:
    @pytest.mark.asyncio
    async def test_returns_correct_progress(self, adapter):
        sprint = await _make_sprint(adapter)
        await adapter.start_sprint(sprint.id)
        status = await adapter.get_step_status(sprint.id)
        assert status["current_step"] == "Design"
        assert status["total_steps"] == 3
        assert status["completed_steps"] == 0
        assert status["progress_pct"] == 0.0
        assert len(status["steps"]) == 3

    @pytest.mark.asyncio
    async def test_handles_empty_steps(self, adapter):
        sprint = await _make_sprint(adapter, tasks=[])
        status = await adapter.get_step_status(sprint.id)
        assert status["current_step"] is None
        assert status["total_steps"] == 0
        assert status["completed_steps"] == 0
        assert status["progress_pct"] == 0.0

    @pytest.mark.asyncio
    async def test_handles_all_done(self, adapter):
        sprint = await _make_sprint(adapter, tasks=[{"name": "A"}])
        await adapter.start_sprint(sprint.id)
        await adapter.advance_step(sprint.id)
        status = await adapter.get_step_status(sprint.id)
        assert status["current_step"] is None
        assert status["completed_steps"] == 1
        assert status["progress_pct"] == 100.0

    @pytest.mark.asyncio
    async def test_step_dicts_have_correct_keys(self, adapter):
        sprint = await _make_sprint(adapter, tasks=[{"name": "X"}])
        await adapter.start_sprint(sprint.id)
        status = await adapter.get_step_status(sprint.id)
        step_dict = status["steps"][0]
        assert "id" in step_dict
        assert "name" in step_dict
        assert "status" in step_dict


# ---------------------------------------------------------------------------
# Full lifecycle
# ---------------------------------------------------------------------------
class TestFullLifecycle:
    @pytest.mark.asyncio
    async def test_start_advance_complete(self, adapter):
        """End-to-end: start -> advance through all steps -> complete."""
        sprint = await _make_sprint(
            adapter, tasks=[{"name": "Plan"}, {"name": "Code"}, {"name": "Review"}]
        )

        # Start
        sprint = await adapter.start_sprint(sprint.id)
        assert sprint.status is SprintStatus.IN_PROGRESS

        # Advance through all steps
        sprint = await adapter.advance_step(sprint.id, step_output={"plan": "done"})
        sprint = await adapter.advance_step(sprint.id, step_output={"code": "done"})
        sprint = await adapter.advance_step(sprint.id, step_output={"review": "done"})

        # All steps should be done
        assert all(s.status is StepStatus.DONE for s in sprint.steps)

        # Complete
        sprint = await adapter.complete_sprint(sprint.id)
        assert sprint.status is SprintStatus.DONE
        assert len(sprint.transitions) == 2  # start + complete

    @pytest.mark.asyncio
    async def test_start_block_resume_complete(self, adapter):
        """Start -> block -> resume -> advance -> complete."""
        sprint = await _make_sprint(adapter, tasks=[{"name": "Work"}])

        sprint = await adapter.start_sprint(sprint.id)
        sprint = await adapter.block_sprint(sprint.id, reason="Waiting")
        assert sprint.status is SprintStatus.BLOCKED

        # Resume (unblock) - use update_sprint to move BLOCKED -> IN_PROGRESS
        # which is a valid transition
        from src.workflow.transitions import validate_transition

        validate_transition(sprint.id, SprintStatus.BLOCKED, SprintStatus.IN_PROGRESS)
        sprint = await adapter.update_sprint(
            sprint.id, status=SprintStatus.IN_PROGRESS
        )

        # Advance and complete
        sprint = await adapter.advance_step(sprint.id)
        sprint = await adapter.complete_sprint(sprint.id)
        assert sprint.status is SprintStatus.DONE
