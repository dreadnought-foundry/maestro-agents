"""TDD tests for SprintRunner — the core sprint execution orchestrator."""

from __future__ import annotations

import pytest

from src.adapters.memory import InMemoryAdapter
from src.agents.execution.mocks import MockProductEngineerAgent, MockTestRunnerAgent
from src.agents.execution.registry import AgentRegistry
from src.agents.execution.types import AgentResult
from src.execution.runner import RunResult, SprintRunner
from src.workflow.models import SprintStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _setup_single_step(tasks=None):
    """Create backend with one epic and one sprint, return (backend, sprint_id)."""
    backend = InMemoryAdapter()
    epic = await backend.create_epic("Test Epic", "An epic for testing")
    tasks = tasks or [{"name": "implement"}]
    sprint = await backend.create_sprint(epic.id, "Build feature", tasks=tasks)
    return backend, sprint.id


def _make_runner(backend, registry=None, mock_agent=None):
    """Create a SprintRunner with a registry that has a default mock agent."""
    if registry is None:
        registry = AgentRegistry()
    if mock_agent is not None:
        # Register for common step names
        for name in ("implement", "test", "review", "write_code", "run_tests"):
            registry.register(name, mock_agent)
    return SprintRunner(backend=backend, agent_registry=registry)


# ---------------------------------------------------------------------------
# Happy path (4 tests)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_single_step_sprint():
    """Single-task sprint completes successfully with 1 step."""
    backend, sprint_id = await _setup_single_step(tasks=[{"name": "implement"}])
    mock = MockProductEngineerAgent()
    runner = _make_runner(backend, mock_agent=mock)

    result = await runner.run(sprint_id)

    assert result.success is True
    assert result.steps_completed == 1
    assert result.steps_total == 1
    assert mock.call_count == 1


@pytest.mark.asyncio
async def test_run_multi_step_sprint():
    """Sprint with 3 tasks completes all steps and collects all agent results."""
    tasks = [{"name": "implement"}, {"name": "test"}, {"name": "review"}]
    backend, sprint_id = await _setup_single_step(tasks=tasks)
    mock = MockProductEngineerAgent()
    runner = _make_runner(backend, mock_agent=mock)

    result = await runner.run(sprint_id)

    assert result.success is True
    assert result.steps_completed == 3
    assert result.steps_total == 3
    assert len(result.agent_results) == 3


@pytest.mark.asyncio
async def test_run_result_has_duration():
    """RunResult duration_seconds is a positive number."""
    backend, sprint_id = await _setup_single_step()
    runner = _make_runner(backend, mock_agent=MockProductEngineerAgent())

    result = await runner.run(sprint_id)

    assert result.duration_seconds > 0


@pytest.mark.asyncio
async def test_run_returns_run_result():
    """RunResult has all expected fields populated correctly."""
    backend, sprint_id = await _setup_single_step()
    runner = _make_runner(backend, mock_agent=MockProductEngineerAgent())

    result = await runner.run(sprint_id)

    assert isinstance(result, RunResult)
    assert result.sprint_id == sprint_id
    assert result.success is True
    assert isinstance(result.agent_results, list)
    assert isinstance(result.deferred_items, list)
    assert isinstance(result.duration_seconds, float)


# ---------------------------------------------------------------------------
# Agent dispatch (2 tests)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_correct_agent_called():
    """Different step types dispatch to different registered agents."""
    tasks = [{"name": "write_code"}, {"name": "run_tests"}]
    backend, sprint_id = await _setup_single_step(tasks=tasks)

    code_agent = MockProductEngineerAgent()
    test_agent = MockTestRunnerAgent()

    registry = AgentRegistry()
    registry.register("write_code", code_agent)
    registry.register("run_tests", test_agent)

    runner = SprintRunner(backend=backend, agent_registry=registry)
    await runner.run(sprint_id)

    assert code_agent.call_count == 1
    assert test_agent.call_count == 1


@pytest.mark.asyncio
async def test_context_includes_previous_outputs():
    """Second step's StepContext includes the first step's AgentResult."""
    tasks = [{"name": "implement"}, {"name": "test"}]
    backend, sprint_id = await _setup_single_step(tasks=tasks)

    first_result = AgentResult(success=True, output="step-1 done")
    agent1 = MockProductEngineerAgent(result=first_result)
    agent2 = MockProductEngineerAgent()

    registry = AgentRegistry()
    registry.register("implement", agent1)
    registry.register("test", agent2)

    runner = SprintRunner(backend=backend, agent_registry=registry)
    await runner.run(sprint_id)

    # The second agent should have received the first agent's result
    assert agent2.last_context is not None
    assert len(agent2.last_context.previous_outputs) == 1
    assert agent2.last_context.previous_outputs[0].output == "step-1 done"


# ---------------------------------------------------------------------------
# Progress callbacks (2 tests)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_progress_callback_called():
    """on_progress is called once per step."""
    tasks = [{"name": "implement"}, {"name": "test"}]
    backend, sprint_id = await _setup_single_step(tasks=tasks)
    runner = _make_runner(backend, mock_agent=MockProductEngineerAgent())

    progress_log: list[dict] = []
    await runner.run(sprint_id, on_progress=lambda status: progress_log.append(status))

    assert len(progress_log) == 2


@pytest.mark.asyncio
async def test_progress_callback_has_step_info():
    """Progress callback receives a dict with step status information."""
    backend, sprint_id = await _setup_single_step(tasks=[{"name": "implement"}])
    runner = _make_runner(backend, mock_agent=MockProductEngineerAgent())

    progress_log: list[dict] = []
    await runner.run(sprint_id, on_progress=lambda status: progress_log.append(status))

    assert len(progress_log) == 1
    status = progress_log[0]
    assert "current_step" in status
    assert "total_steps" in status
    assert "completed_steps" in status
    assert "progress_pct" in status


# ---------------------------------------------------------------------------
# Failure handling (2 tests)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_agent_failure_blocks_sprint():
    """When an agent returns success=False, the sprint is blocked and RunResult reflects failure."""
    backend, sprint_id = await _setup_single_step()
    failing_agent = MockProductEngineerAgent(
        result=AgentResult(success=False, output="Something broke")
    )
    runner = _make_runner(backend, mock_agent=failing_agent)

    result = await runner.run(sprint_id)

    assert result.success is False
    sprint = await backend.get_sprint(sprint_id)
    assert sprint.status is SprintStatus.BLOCKED


@pytest.mark.asyncio
async def test_agent_failure_stops_execution():
    """After a step fails, remaining steps are not executed."""
    tasks = [{"name": "implement"}, {"name": "test"}]
    backend, sprint_id = await _setup_single_step(tasks=tasks)

    failing_agent = MockProductEngineerAgent(
        result=AgentResult(success=False, output="Fail")
    )
    second_agent = MockProductEngineerAgent()

    registry = AgentRegistry()
    registry.register("implement", failing_agent)
    registry.register("test", second_agent)

    runner = SprintRunner(backend=backend, agent_registry=registry)
    result = await runner.run(sprint_id)

    assert result.success is False
    assert failing_agent.call_count == 1
    assert second_agent.call_count == 0  # never reached


# ---------------------------------------------------------------------------
# Deferred items (2 tests)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_deferred_items_aggregated():
    """Deferred items from multiple agents are collected in RunResult."""
    tasks = [{"name": "implement"}, {"name": "test"}]
    backend, sprint_id = await _setup_single_step(tasks=tasks)

    agent1 = MockProductEngineerAgent(
        result=AgentResult(success=True, output="ok", deferred_items=["TODO-1"])
    )
    agent2 = MockProductEngineerAgent(
        result=AgentResult(success=True, output="ok", deferred_items=["TODO-2", "TODO-3"])
    )

    registry = AgentRegistry()
    registry.register("implement", agent1)
    registry.register("test", agent2)

    runner = SprintRunner(backend=backend, agent_registry=registry)
    result = await runner.run(sprint_id)

    assert result.deferred_items == ["TODO-1", "TODO-2", "TODO-3"]


@pytest.mark.asyncio
async def test_empty_deferred_items():
    """When no agent returns deferred items, the list is empty."""
    backend, sprint_id = await _setup_single_step()
    runner = _make_runner(backend, mock_agent=MockProductEngineerAgent())

    result = await runner.run(sprint_id)

    assert result.deferred_items == []
