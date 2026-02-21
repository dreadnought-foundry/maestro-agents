"""End-to-end integration tests for the full sprint execution pipeline."""

import pytest

from src.adapters.memory import InMemoryAdapter
from src.agents.execution.mocks import (
    MockProductEngineerAgent,
    MockQualityEngineerAgent,
    MockSuiteRunnerAgent,
)
from src.agents.execution.registry import AgentRegistry
from src.agents.execution.types import AgentResult
from src.execution.convenience import (
    create_registry,
    create_test_registry,
    create_hook_registry,
    run_sprint,
)
from src.execution.dependencies import validate_sprint_dependencies
from src.execution.gates import CoverageGate
from src.execution.hooks import HookContext, HookPoint, HookRegistry
from src.execution.resume import cancel_sprint, resume_sprint
from src.execution.config import RunConfig
from src.execution.runner import RunResult, SprintRunner
from src.workflow.exceptions import DependencyNotMetError

_TEST_CONFIG = RunConfig(max_retries=2, retry_delay_seconds=0.0)
from src.workflow.models import SprintStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _setup_sprint(backend, tasks=None, dependencies=None):
    """Create an epic + sprint with tasks, returning (epic, sprint)."""
    if tasks is None:
        tasks = [
            {"name": "implement"},
            {"name": "test"},
            {"name": "review"},
        ]
    epic = await backend.create_epic("E2E Epic", "End-to-end test epic")
    sprint = await backend.create_sprint(
        epic.id,
        goal="Complete all tasks",
        tasks=tasks,
        dependencies=dependencies or [],
    )
    return epic, sprint


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_full_lifecycle_create_to_completion():
    """Create epic -> create sprint with tasks -> run -> verify DONE, all steps completed."""
    backend = InMemoryAdapter(project_name="e2e-project")
    epic, sprint = await _setup_sprint(backend)
    registry = create_test_registry()

    runner = SprintRunner(backend=backend, agent_registry=registry, config=_TEST_CONFIG)
    result = await runner.run(sprint.id)

    assert result.success is True
    assert result.steps_completed == 3
    assert result.steps_total == 3
    assert result.duration_seconds >= 0

    # Verify backend state — runner stops at REVIEW
    updated_sprint = await backend.get_sprint(sprint.id)
    assert updated_sprint.status is SprintStatus.REVIEW


async def test_full_lifecycle_with_multiple_step_types():
    """Sprint with implement/test/review tasks; each agent type is called."""
    backend = InMemoryAdapter()
    epic, sprint = await _setup_sprint(
        backend,
        tasks=[
            {"name": "implement"},
            {"name": "test"},
            {"name": "review"},
        ],
    )

    impl_agent = MockProductEngineerAgent()
    test_agent = MockSuiteRunnerAgent()
    review_agent = MockQualityEngineerAgent()

    registry = AgentRegistry()
    registry.register("implement", impl_agent)
    registry.register("test", test_agent)
    registry.register("review", review_agent)

    runner = SprintRunner(backend=backend, agent_registry=registry, config=_TEST_CONFIG)
    result = await runner.run(sprint.id)

    assert result.success is True
    assert impl_agent.call_count == 1
    assert test_agent.call_count == 1
    assert review_agent.call_count == 1


async def test_dependency_enforcement():
    """Sprint B depends on A. B fails before A is done; succeeds after."""
    backend = InMemoryAdapter()
    epic_a, sprint_a = await _setup_sprint(backend, tasks=[{"name": "implement"}])
    _, sprint_b = await _setup_sprint(
        backend,
        tasks=[{"name": "implement"}],
        dependencies=[sprint_a.id],
    )

    # Validate deps for B before A is done -> should raise
    with pytest.raises(DependencyNotMetError) as exc_info:
        await validate_sprint_dependencies(sprint_b.id, backend)
    assert sprint_a.id in exc_info.value.unmet_dependencies

    # Run sprint A (stops at REVIEW), then manually complete it
    registry = create_test_registry()
    runner = SprintRunner(backend=backend, agent_registry=registry, config=_TEST_CONFIG)
    result_a = await runner.run(sprint_a.id)
    assert result_a.success is True
    await backend.complete_sprint(sprint_a.id)

    # Now B's deps should be met
    await validate_sprint_dependencies(sprint_b.id, backend)  # no exception

    result_b = await runner.run(sprint_b.id)
    assert result_b.success is True


async def test_coverage_gate_blocks_low_coverage():
    """CoverageGate blocks when coverage is below threshold."""
    gate = CoverageGate(threshold=80.0)

    from src.workflow.models import Sprint, SprintStatus, Step

    sprint = Sprint(id="s-1", goal="test", status=SprintStatus.IN_PROGRESS, epic_id="e-1")
    step = Step(id="step-1", name="test")
    low_coverage_result = AgentResult(success=True, output="Tests passed", coverage=50.0)

    context = HookContext(
        sprint=sprint,
        step=step,
        agent_result=low_coverage_result,
    )
    hook_result = await gate.evaluate(context)

    assert hook_result.passed is False
    assert hook_result.blocking is True
    assert "50.0%" in hook_result.message


async def test_resume_after_failure():
    """Run sprint, agent fails on step 2, sprint blocked. Resume -> completes from step 2."""
    backend = InMemoryAdapter()
    epic, sprint = await _setup_sprint(
        backend,
        tasks=[{"name": "implement"}, {"name": "test"}, {"name": "review"}],
    )

    # First run: test agent fails
    fail_test_agent = MockSuiteRunnerAgent(
        result=AgentResult(success=False, output="Tests failed")
    )

    registry = AgentRegistry()
    registry.register("implement", MockProductEngineerAgent())
    registry.register("test", fail_test_agent)
    registry.register("review", MockQualityEngineerAgent())

    runner = SprintRunner(backend=backend, agent_registry=registry, config=_TEST_CONFIG)
    result = await runner.run(sprint.id)

    assert result.success is False
    updated = await backend.get_sprint(sprint.id)
    assert updated.status is SprintStatus.BLOCKED

    # Now fix the test agent and resume
    passing_test_agent = MockSuiteRunnerAgent()  # default passes
    registry2 = AgentRegistry()
    registry2.register("implement", MockProductEngineerAgent())
    registry2.register("test", passing_test_agent)
    registry2.register("review", MockQualityEngineerAgent())

    result2 = await resume_sprint(
        sprint.id, backend, agent_registry=registry2
    )
    assert result2.success is True
    assert result2.steps_completed == 3


async def test_cancel_in_progress_sprint():
    """Start a sprint manually, cancel it -> BLOCKED with reason."""
    backend = InMemoryAdapter()
    epic, sprint = await _setup_sprint(backend)

    await backend.start_sprint(sprint.id)
    assert (await backend.get_sprint(sprint.id)).status is SprintStatus.IN_PROGRESS

    await cancel_sprint(sprint.id, "Requirements changed", backend)
    updated = await backend.get_sprint(sprint.id)
    assert updated.status is SprintStatus.BLOCKED


async def test_deferred_items_flow_through():
    """Agent returns deferred_items -> RunResult.deferred_items includes them."""
    backend = InMemoryAdapter()
    epic, sprint = await _setup_sprint(
        backend,
        tasks=[{"name": "implement"}],
    )

    agent = MockProductEngineerAgent(
        result=AgentResult(
            success=True,
            output="Done",
            deferred_items=["TODO: add error handling", "TODO: add logging"],
        )
    )
    registry = AgentRegistry()
    registry.register("implement", agent)

    runner = SprintRunner(backend=backend, agent_registry=registry, config=_TEST_CONFIG)
    result = await runner.run(sprint.id)

    assert result.success is True
    assert "TODO: add error handling" in result.deferred_items
    assert "TODO: add logging" in result.deferred_items


async def test_create_test_registry_has_common_types():
    """create_test_registry has implement, test, review agents."""
    registry = create_test_registry()
    agents = registry.list_agents()

    assert "implement" in agents
    assert "write_code" in agents
    assert "test" in agents
    assert "run_tests" in agents
    assert "review" in agents
    assert "quality_review" in agents


async def test_run_sprint_convenience_function():
    """run_sprint() with defaults works end-to-end."""
    backend = InMemoryAdapter()
    epic, sprint = await _setup_sprint(backend)

    result = await run_sprint(sprint.id, backend=backend, mock=True)

    assert result.success is True
    assert result.steps_completed == 3
    assert result.steps_total == 3

    updated = await backend.get_sprint(sprint.id)
    assert updated.status is SprintStatus.REVIEW


# ---------------------------------------------------------------------------
# Sprint 26 regression tests — real registry wiring
# ---------------------------------------------------------------------------


async def test_create_registry_returns_real_agents():
    """create_registry() wires real agents with ClaudeCodeExecutor."""
    from src.agents.execution.product_engineer import ProductEngineerAgent
    from src.agents.execution.quality_engineer import QualityEngineerAgent
    from src.agents.execution.suite_runner import SuiteRunnerAgent

    registry = create_registry()
    agents = registry.list_agents()

    # Same step types as test registry
    assert "implement" in agents
    assert "write_code" in agents
    assert "test" in agents
    assert "run_tests" in agents
    assert "review" in agents
    assert "quality_review" in agents

    # But real agent classes, not mocks
    assert isinstance(agents["implement"], ProductEngineerAgent)
    assert isinstance(agents["test"], SuiteRunnerAgent)
    assert isinstance(agents["review"], QualityEngineerAgent)

    # Each agent has an executor injected
    assert agents["implement"]._executor is not None
    assert agents["test"]._executor is not None
    assert agents["review"]._executor is not None


async def test_create_test_registry_returns_mock_agents():
    """create_test_registry() returns mock agents, not real ones."""
    registry = create_test_registry()
    agents = registry.list_agents()

    assert isinstance(agents["implement"], MockProductEngineerAgent)
    assert isinstance(agents["test"], MockSuiteRunnerAgent)
    assert isinstance(agents["review"], MockQualityEngineerAgent)


async def test_run_sprint_mock_flag_uses_test_registry():
    """run_sprint(mock=True) uses mock agents and completes fast."""
    backend = InMemoryAdapter()
    epic, sprint = await _setup_sprint(backend)

    result = await run_sprint(sprint.id, backend=backend, mock=True)

    assert result.success is True
    assert result.steps_completed == 3


async def test_quality_engineer_parses_approve_verdict():
    """QualityEngineerAgent extracts review_verdict from output text."""
    from unittest.mock import AsyncMock

    from src.agents.execution.quality_engineer import QualityEngineerAgent

    # Create a mock executor that returns output containing "approve"
    mock_executor = AsyncMock()
    mock_executor.run.return_value = AgentResult(
        success=True,
        output="Code review complete. Verdict: approve. All criteria met.",
    )

    agent = QualityEngineerAgent(executor=mock_executor)
    context = _make_context()
    result = await agent.execute(context)

    assert result.review_verdict == "approve"


async def test_quality_engineer_parses_request_changes_verdict():
    """QualityEngineerAgent detects request_changes verdict."""
    from unittest.mock import AsyncMock

    from src.agents.execution.quality_engineer import QualityEngineerAgent

    mock_executor = AsyncMock()
    mock_executor.run.return_value = AgentResult(
        success=True,
        output="Issues found. Verdict: request_changes. Fix error handling.",
    )

    agent = QualityEngineerAgent(executor=mock_executor)
    context = _make_context()
    result = await agent.execute(context)

    assert result.review_verdict == "request_changes"


async def test_quality_engineer_no_verdict_in_output():
    """QualityEngineerAgent leaves review_verdict as None if not found."""
    from unittest.mock import AsyncMock

    from src.agents.execution.quality_engineer import QualityEngineerAgent

    mock_executor = AsyncMock()
    mock_executor.run.return_value = AgentResult(
        success=True,
        output="Reviewed the code. Looks fine overall.",
    )

    agent = QualityEngineerAgent(executor=mock_executor)
    context = _make_context()
    result = await agent.execute(context)

    assert result.review_verdict is None


def _make_context():
    """Create a minimal StepContext for testing."""
    from pathlib import Path

    from src.agents.execution.types import StepContext
    from src.workflow.models import Epic, EpicStatus, Sprint, SprintStatus, Step

    step = Step(id="s1", name="review")
    sprint = Sprint(
        id="test-sprint",
        goal="Test sprint",
        status=SprintStatus.IN_PROGRESS,
        epic_id="test-epic",
        steps=[step],
    )
    epic = Epic(
        id="test-epic",
        title="Test Epic",
        description="Test epic",
        status=EpicStatus.ACTIVE,
        sprint_ids=["test-sprint"],
    )
    return StepContext(
        step=step,
        sprint=sprint,
        epic=epic,
        project_root=Path("."),
    )
