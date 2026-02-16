"""TDD tests for pause, resume, cancel, and retry logic."""

from __future__ import annotations

import pytest

from src.adapters.memory import InMemoryAdapter
from src.agents.execution.mocks import MockProductEngineerAgent
from src.agents.execution.registry import AgentRegistry
from src.agents.execution.types import AgentResult
from src.execution.config import RunConfig
from src.execution.resume import (
    cancel_sprint,
    find_resume_point,
    resume_sprint,
    retry_step,
)
from src.workflow.models import SprintStatus, StepStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FailThenSucceedAgent:
    """Fails N times then succeeds."""

    name = "fail_then_succeed"
    description = "Fails N times then succeeds"

    def __init__(self, fail_count: int):
        self._fail_count = fail_count
        self._attempts = 0

    async def execute(self, context):
        self._attempts += 1
        if self._attempts <= self._fail_count:
            return AgentResult(success=False, output=f"Attempt {self._attempts} failed")
        return AgentResult(success=True, output=f"Succeeded on attempt {self._attempts}")


async def _setup_sprint(tasks=None):
    """Create backend with one epic and one sprint, return (backend, sprint_id)."""
    backend = InMemoryAdapter()
    epic = await backend.create_epic("Test Epic", "An epic for testing")
    tasks = tasks or [{"name": "implement"}, {"name": "test"}, {"name": "review"}]
    sprint = await backend.create_sprint(epic.id, "Build feature", tasks=tasks)
    return backend, sprint.id


def _make_registry(mock_agent=None, step_names=None):
    """Create an AgentRegistry with a mock agent registered for given step names."""
    registry = AgentRegistry()
    if mock_agent is not None:
        for name in (step_names or ["implement", "test", "review"]):
            registry.register(name, mock_agent)
    return registry


# ---------------------------------------------------------------------------
# RunConfig (1 test)
# ---------------------------------------------------------------------------

class TestRunConfig:
    def test_config_defaults(self):
        """RunConfig has sensible defaults: max_retries=2, retry_delay_seconds=1.0."""
        config = RunConfig()
        assert config.max_retries == 2
        assert config.retry_delay_seconds == 1.0


# ---------------------------------------------------------------------------
# find_resume_point (2 tests)
# ---------------------------------------------------------------------------

class TestFindResumePoint:
    async def test_finds_first_incomplete_step(self):
        """Sprint with first step DONE, second TODO -> returns 1."""
        backend, sprint_id = await _setup_sprint(
            tasks=[{"name": "implement"}, {"name": "test"}]
        )
        # Start the sprint so steps are created, then mark first step done
        await backend.start_sprint(sprint_id)
        await backend.advance_step(sprint_id, {"output": "done"})

        # Now first step is DONE, second is IN_PROGRESS
        # Block the sprint so it's in a resumable state
        await backend.block_sprint(sprint_id, "test block")

        idx = await find_resume_point(sprint_id, backend)
        assert idx == 1

    async def test_all_steps_done_returns_length(self):
        """All steps DONE -> returns len(steps)."""
        backend, sprint_id = await _setup_sprint(
            tasks=[{"name": "implement"}, {"name": "test"}]
        )
        await backend.start_sprint(sprint_id)
        await backend.advance_step(sprint_id, {"output": "done"})
        await backend.advance_step(sprint_id, {"output": "done"})

        idx = await find_resume_point(sprint_id, backend)
        assert idx == 2


# ---------------------------------------------------------------------------
# resume_sprint (3 tests)
# ---------------------------------------------------------------------------

class TestResumeSprint:
    async def test_resumes_blocked_sprint(self):
        """Block a sprint mid-execution, resume it -> completes successfully."""
        backend, sprint_id = await _setup_sprint(
            tasks=[{"name": "implement"}, {"name": "test"}]
        )
        mock_agent = MockProductEngineerAgent()
        registry = _make_registry(mock_agent, ["implement", "test"])

        # Start sprint, complete first step, then block
        await backend.start_sprint(sprint_id)
        await backend.advance_step(sprint_id, {"output": "step 1 done"})
        await backend.block_sprint(sprint_id, "agent failed")

        result = await resume_sprint(sprint_id, backend, registry)

        assert result.success is True
        assert result.steps_completed == 2
        assert result.steps_total == 2
        sprint = await backend.get_sprint(sprint_id)
        assert sprint.status is SprintStatus.DONE

    async def test_resume_non_blocked_raises(self):
        """Try to resume a TODO sprint -> ValueError."""
        backend, sprint_id = await _setup_sprint()

        registry = _make_registry(MockProductEngineerAgent())

        with pytest.raises(ValueError, match="expected blocked"):
            await resume_sprint(sprint_id, backend, registry)

    async def test_resume_skips_completed_steps(self):
        """Only executes remaining steps (mock call_count matches)."""
        backend, sprint_id = await _setup_sprint(
            tasks=[{"name": "implement"}, {"name": "test"}, {"name": "review"}]
        )
        mock_agent = MockProductEngineerAgent()
        registry = _make_registry(mock_agent, ["implement", "test", "review"])

        # Start, complete first two steps, then block
        await backend.start_sprint(sprint_id)
        await backend.advance_step(sprint_id, {"output": "step 1 done"})
        await backend.advance_step(sprint_id, {"output": "step 2 done"})
        await backend.block_sprint(sprint_id, "agent failed")

        result = await resume_sprint(sprint_id, backend, registry)

        # Only the third step should have been executed
        assert mock_agent.call_count == 1
        assert result.success is True


# ---------------------------------------------------------------------------
# cancel_sprint (2 tests)
# ---------------------------------------------------------------------------

class TestCancelSprint:
    async def test_cancel_in_progress(self):
        """Cancels an IN_PROGRESS sprint by blocking with reason."""
        backend, sprint_id = await _setup_sprint()
        await backend.start_sprint(sprint_id)

        await cancel_sprint(sprint_id, "No longer needed", backend)

        sprint = await backend.get_sprint(sprint_id)
        assert sprint.status is SprintStatus.BLOCKED

    async def test_cancel_todo(self):
        """Cancels a TODO sprint by setting ABANDONED."""
        backend, sprint_id = await _setup_sprint()

        await cancel_sprint(sprint_id, "Cancelled before start", backend)

        sprint = await backend.get_sprint(sprint_id)
        assert sprint.status is SprintStatus.ABANDONED


# ---------------------------------------------------------------------------
# retry_step (2 tests)
# ---------------------------------------------------------------------------

class TestRetryStep:
    async def test_retry_succeeds_on_second_attempt(self):
        """Agent fails first, succeeds second -> returns success."""
        backend, sprint_id = await _setup_sprint(tasks=[{"name": "implement"}])
        agent = FailThenSucceedAgent(fail_count=1)
        registry = AgentRegistry()
        registry.register("implement", agent)

        # Start sprint so steps are created and first step is IN_PROGRESS
        await backend.start_sprint(sprint_id)

        result = await retry_step(sprint_id, backend, registry, max_retries=2)

        assert result.success is True
        assert "attempt 2" in result.output.lower()

    async def test_retry_exhausts_max_retries(self):
        """Agent always fails -> returns failure after max_retries+1 attempts."""
        backend, sprint_id = await _setup_sprint(tasks=[{"name": "implement"}])
        agent = FailThenSucceedAgent(fail_count=999)  # always fails
        registry = AgentRegistry()
        registry.register("implement", agent)

        await backend.start_sprint(sprint_id)

        result = await retry_step(sprint_id, backend, registry, max_retries=2)

        assert result.success is False
        # Should have attempted max_retries + 1 = 3 times
        assert agent._attempts == 3
