"""Tests for phase-based sprint runner execution."""

from __future__ import annotations

import pytest

from src.adapters.memory import InMemoryAdapter
from src.agents.execution.mocks import MockProductEngineerAgent, MockTestRunnerAgent
from src.agents.execution.registry import AgentRegistry
from src.agents.execution.types import AgentResult
from src.execution.config import RunConfig
from src.execution.hooks import HookRegistry, MockHook, HookPoint, HookResult
from src.execution.phases import Phase, PhaseConfig, PhaseResult
from src.execution.runner import RunResult, SprintRunner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _setup(tasks=None):
    """Create backend with one epic and one sprint, return (backend, sprint_id)."""
    backend = InMemoryAdapter()
    epic = await backend.create_epic("Test Epic", "An epic for testing")
    tasks = tasks or [{"name": "implement"}]
    sprint = await backend.create_sprint(epic.id, "Build feature", tasks=tasks)
    return backend, sprint.id


def _make_phase_configs(
    plan_agent=None,
    tdd_agent=None,
    build_agent=None,
    validate_agent=None,
    plan_gate=None,
    tdd_gate=None,
    build_gate=None,
    validate_gate=None,
    include_review=True,
    include_complete=True,
) -> list[PhaseConfig]:
    """Build a standard set of phase configs for testing."""
    configs = [
        PhaseConfig(phase=Phase.PLAN, agent_type="plan", gate=plan_gate),
        PhaseConfig(phase=Phase.TDD, agent_type="tdd", gate=tdd_gate),
        PhaseConfig(phase=Phase.BUILD, agent_type="build", gate=build_gate),
        PhaseConfig(phase=Phase.VALIDATE, agent_type="validate", gate=validate_gate),
    ]
    if include_review:
        configs.append(PhaseConfig(phase=Phase.REVIEW, agent_type=None))
    if include_complete:
        configs.append(PhaseConfig(phase=Phase.COMPLETE, agent_type=None))
    return configs


def _make_phased_runner(backend, registry, phase_configs, config=None):
    """Create a SprintRunner configured for phase-based execution."""
    if config is None:
        config = RunConfig(max_retries=0, retry_delay_seconds=0.0)
    return SprintRunner(
        backend=backend,
        agent_registry=registry,
        config=config,
        phase_configs=phase_configs,
    )


# ---------------------------------------------------------------------------
# Phase progression (3 tests)
# ---------------------------------------------------------------------------

async def test_phase_progression_plan_tdd_build_validate_stops_at_review():
    """Phases execute in order and stop at REVIEW."""
    backend, sprint_id = await _setup()

    plan_agent = MockProductEngineerAgent()
    tdd_agent = MockTestRunnerAgent()
    build_agent = MockProductEngineerAgent()
    validate_agent = MockTestRunnerAgent()

    registry = AgentRegistry()
    registry.register("plan", plan_agent)
    registry.register("tdd", tdd_agent)
    registry.register("build", build_agent)
    registry.register("validate", validate_agent)

    phase_configs = _make_phase_configs()
    runner = _make_phased_runner(backend, registry, phase_configs)

    result = await runner.run(sprint_id)

    assert result.success is True
    assert result.stopped_at_review is True
    assert result.current_phase is Phase.REVIEW
    assert plan_agent.call_count == 1
    assert tdd_agent.call_count == 1
    assert build_agent.call_count == 1
    assert validate_agent.call_count == 1
    assert len(result.phase_results) == 4  # PLAN, TDD, BUILD, VALIDATE


async def test_phase_results_recorded_in_order():
    """Phase results are recorded in execution order."""
    backend, sprint_id = await _setup()

    registry = AgentRegistry()
    for name in ("plan", "tdd", "build", "validate"):
        registry.register(name, MockProductEngineerAgent())

    phase_configs = _make_phase_configs()
    runner = _make_phased_runner(backend, registry, phase_configs)

    result = await runner.run(sprint_id)

    phases = [pr.phase for pr in result.phase_results]
    assert phases == [Phase.PLAN, Phase.TDD, Phase.BUILD, Phase.VALIDATE]


async def test_all_agent_results_collected():
    """Agent results from all phases are collected in RunResult."""
    backend, sprint_id = await _setup()

    registry = AgentRegistry()
    for name in ("plan", "tdd", "build", "validate"):
        registry.register(name, MockProductEngineerAgent())

    phase_configs = _make_phase_configs()
    runner = _make_phased_runner(backend, registry, phase_configs)

    result = await runner.run(sprint_id)

    assert len(result.agent_results) == 4


# ---------------------------------------------------------------------------
# Gate failure blocks advancement (3 tests)
# ---------------------------------------------------------------------------

async def test_gate_failure_blocks_sprint():
    """When a phase gate fails, the sprint is blocked."""
    backend, sprint_id = await _setup()

    registry = AgentRegistry()
    registry.register("plan", MockProductEngineerAgent())
    registry.register("tdd", MockTestRunnerAgent())

    async def failing_gate(phase_result: PhaseResult) -> tuple[bool, str]:
        return False, "Tests must all fail initially"

    phase_configs = _make_phase_configs(tdd_gate=failing_gate)
    runner = _make_phased_runner(backend, registry, phase_configs)

    result = await runner.run(sprint_id)

    assert result.success is False
    assert result.current_phase is Phase.TDD
    # Only PLAN succeeded, TDD was executed but gate failed
    assert len(result.phase_results) == 2
    assert result.phase_results[0].success is True  # PLAN
    assert result.phase_results[1].success is False  # TDD (gate failed)


async def test_gate_failure_stops_subsequent_phases():
    """When a gate fails, no subsequent phases execute."""
    backend, sprint_id = await _setup()

    plan_agent = MockProductEngineerAgent()
    tdd_agent = MockTestRunnerAgent()
    build_agent = MockProductEngineerAgent()

    registry = AgentRegistry()
    registry.register("plan", plan_agent)
    registry.register("tdd", tdd_agent)
    registry.register("build", build_agent)
    registry.register("validate", MockTestRunnerAgent())

    async def failing_gate(phase_result: PhaseResult) -> tuple[bool, str]:
        return False, "Gate check failed"

    phase_configs = _make_phase_configs(plan_gate=failing_gate)
    runner = _make_phased_runner(backend, registry, phase_configs)

    result = await runner.run(sprint_id)

    assert result.success is False
    assert plan_agent.call_count == 1
    assert tdd_agent.call_count == 0  # never reached
    assert build_agent.call_count == 0  # never reached


async def test_gate_passes_allows_next_phase():
    """When a gate passes, execution continues to the next phase."""
    backend, sprint_id = await _setup()

    registry = AgentRegistry()
    for name in ("plan", "tdd", "build", "validate"):
        registry.register(name, MockProductEngineerAgent())

    async def passing_gate(phase_result: PhaseResult) -> tuple[bool, str]:
        return True, "All checks passed"

    phase_configs = _make_phase_configs(plan_gate=passing_gate, build_gate=passing_gate)
    runner = _make_phased_runner(backend, registry, phase_configs)

    result = await runner.run(sprint_id)

    assert result.success is True
    assert result.stopped_at_review is True
    assert len(result.phase_results) == 4


# ---------------------------------------------------------------------------
# Backwards compatibility (2 tests)
# ---------------------------------------------------------------------------

async def test_no_phase_configs_uses_flat_steps():
    """When no phase_configs provided, runner uses original flat step execution."""
    backend, sprint_id = await _setup(tasks=[{"name": "implement"}, {"name": "test"}])

    mock = MockProductEngineerAgent()
    registry = AgentRegistry()
    registry.register("implement", mock)
    registry.register("test", mock)

    # No phase_configs = flat step execution
    runner = SprintRunner(backend=backend, agent_registry=registry)
    result = await runner.run(sprint_id)

    assert result.success is True
    assert result.steps_completed == 2
    assert result.phase_results == []  # No phase results in flat mode
    assert result.stopped_at_review is True  # Flat mode now stops at review (Sprint 30)


async def test_flat_mode_still_works_with_all_features():
    """Flat mode preserves hooks, retries, and deferred items."""
    backend, sprint_id = await _setup(tasks=[{"name": "implement"}])

    agent = MockProductEngineerAgent(
        result=AgentResult(success=True, output="done", deferred_items=["TODO-1"])
    )
    registry = AgentRegistry()
    registry.register("implement", agent)

    runner = SprintRunner(backend=backend, agent_registry=registry)
    result = await runner.run(sprint_id)

    assert result.success is True
    assert result.deferred_items == ["TODO-1"]


# ---------------------------------------------------------------------------
# Phase-aware progress callbacks (2 tests)
# ---------------------------------------------------------------------------

async def test_phase_progress_callback_called():
    """on_progress is called after each phase with agent execution."""
    backend, sprint_id = await _setup()

    registry = AgentRegistry()
    for name in ("plan", "tdd", "build", "validate"):
        registry.register(name, MockProductEngineerAgent())

    phase_configs = _make_phase_configs()
    runner = _make_phased_runner(backend, registry, phase_configs)

    progress_log: list[dict] = []
    await runner.run(sprint_id, on_progress=lambda s: progress_log.append(s))

    assert len(progress_log) == 4  # PLAN, TDD, BUILD, VALIDATE


async def test_phase_progress_includes_phase_info():
    """Progress callback includes phase-specific information."""
    backend, sprint_id = await _setup()

    registry = AgentRegistry()
    for name in ("plan", "tdd", "build", "validate"):
        registry.register(name, MockProductEngineerAgent())

    phase_configs = _make_phase_configs()
    runner = _make_phased_runner(backend, registry, phase_configs)

    progress_log: list[dict] = []
    await runner.run(sprint_id, on_progress=lambda s: progress_log.append(s))

    assert progress_log[0]["current_phase"] == "plan"
    assert progress_log[1]["current_phase"] == "tdd"
    assert progress_log[2]["current_phase"] == "build"
    assert progress_log[3]["current_phase"] == "validate"
    assert progress_log[0]["phases_completed"] == 1
    assert progress_log[3]["phases_completed"] == 4


# ---------------------------------------------------------------------------
# Agent failure in phase (2 tests)
# ---------------------------------------------------------------------------

async def test_agent_failure_in_phase_blocks_sprint():
    """When an agent fails within a phase, the sprint is blocked."""
    backend, sprint_id = await _setup()

    plan_agent = MockProductEngineerAgent()
    failing_tdd = MockProductEngineerAgent(
        result=AgentResult(success=False, output="Test writing failed")
    )

    registry = AgentRegistry()
    registry.register("plan", plan_agent)
    registry.register("tdd", failing_tdd)
    registry.register("build", MockProductEngineerAgent())
    registry.register("validate", MockTestRunnerAgent())

    phase_configs = [
        PhaseConfig(phase=Phase.PLAN, agent_type="plan", max_retries=0),
        PhaseConfig(phase=Phase.TDD, agent_type="tdd", max_retries=0),
        PhaseConfig(phase=Phase.BUILD, agent_type="build", max_retries=0),
        PhaseConfig(phase=Phase.VALIDATE, agent_type="validate", max_retries=0),
        PhaseConfig(phase=Phase.REVIEW, agent_type=None),
    ]
    runner = _make_phased_runner(backend, registry, phase_configs)

    result = await runner.run(sprint_id)

    assert result.success is False
    assert result.current_phase is Phase.TDD
    assert plan_agent.call_count == 1
    assert failing_tdd.call_count == 1


async def test_deferred_items_collected_across_phases():
    """Deferred items from all phases are aggregated."""
    backend, sprint_id = await _setup()

    plan_agent = MockProductEngineerAgent(
        result=AgentResult(success=True, output="planned", deferred_items=["DEFER-1"])
    )
    build_agent = MockProductEngineerAgent(
        result=AgentResult(success=True, output="built", deferred_items=["DEFER-2", "DEFER-3"])
    )

    registry = AgentRegistry()
    registry.register("plan", plan_agent)
    registry.register("tdd", MockProductEngineerAgent())
    registry.register("build", build_agent)
    registry.register("validate", MockTestRunnerAgent())

    phase_configs = _make_phase_configs()
    runner = _make_phased_runner(backend, registry, phase_configs)

    result = await runner.run(sprint_id)

    assert "DEFER-1" in result.deferred_items
    assert "DEFER-2" in result.deferred_items
    assert "DEFER-3" in result.deferred_items


# ---------------------------------------------------------------------------
# Phase without review (runs to completion)
# ---------------------------------------------------------------------------

async def test_phases_without_review_runs_to_completion():
    """If REVIEW phase is excluded, runner completes the sprint."""
    backend, sprint_id = await _setup()

    registry = AgentRegistry()
    for name in ("plan", "tdd", "build", "validate"):
        registry.register(name, MockProductEngineerAgent())

    phase_configs = _make_phase_configs(include_review=False, include_complete=True)
    runner = _make_phased_runner(backend, registry, phase_configs)

    result = await runner.run(sprint_id)

    assert result.success is True
    assert result.stopped_at_review is False
    assert result.current_phase is Phase.COMPLETE


# ---------------------------------------------------------------------------
# Phase retry
# ---------------------------------------------------------------------------

async def test_phase_retries_on_failure():
    """Phase agent execution retries up to max_retries."""
    backend, sprint_id = await _setup()

    call_count = 0
    original_result = AgentResult(success=False, output="fail")
    success_result = AgentResult(success=True, output="ok")

    class RetryAgent:
        name = "retry_agent"
        description = "Agent that fails once then succeeds"

        async def execute(self, context):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                return original_result
            return success_result

    registry = AgentRegistry()
    registry.register("plan", RetryAgent())
    registry.register("tdd", MockProductEngineerAgent())
    registry.register("build", MockProductEngineerAgent())
    registry.register("validate", MockTestRunnerAgent())

    phase_configs = [
        PhaseConfig(phase=Phase.PLAN, agent_type="plan", max_retries=2),
        PhaseConfig(phase=Phase.TDD, agent_type="tdd"),
        PhaseConfig(phase=Phase.BUILD, agent_type="build"),
        PhaseConfig(phase=Phase.VALIDATE, agent_type="validate"),
        PhaseConfig(phase=Phase.REVIEW, agent_type=None),
    ]
    runner = _make_phased_runner(backend, registry, phase_configs)

    result = await runner.run(sprint_id)

    assert result.success is True
    assert call_count == 2  # 1 fail + 1 success


# ---------------------------------------------------------------------------
# Hooks in phased mode
# ---------------------------------------------------------------------------

async def test_pre_sprint_hook_failure_blocks_phased_run():
    """PRE_SPRINT hook failure blocks the sprint in phased mode."""
    backend, sprint_id = await _setup()

    registry = AgentRegistry()
    for name in ("plan", "tdd", "build", "validate"):
        registry.register(name, MockProductEngineerAgent())

    hook_registry = HookRegistry()
    hook_registry.register(MockHook(
        HookPoint.PRE_SPRINT,
        HookResult(passed=False, message="Blocked by pre-sprint check", blocking=True),
    ))

    phase_configs = _make_phase_configs()
    runner = SprintRunner(
        backend=backend,
        agent_registry=registry,
        config=RunConfig(max_retries=0, retry_delay_seconds=0.0),
        hook_registry=hook_registry,
        phase_configs=phase_configs,
    )

    result = await runner.run(sprint_id)

    assert result.success is False


async def test_post_step_hook_evaluated_per_phase():
    """POST_STEP hooks are evaluated after each phase's agent execution."""
    backend, sprint_id = await _setup()

    registry = AgentRegistry()
    for name in ("plan", "tdd", "build", "validate"):
        registry.register(name, MockProductEngineerAgent())

    post_step_hook = MockHook(
        HookPoint.POST_STEP,
        HookResult(passed=True, message="OK"),
    )
    hook_registry = HookRegistry()
    hook_registry.register(post_step_hook)

    phase_configs = _make_phase_configs()
    runner = SprintRunner(
        backend=backend,
        agent_registry=registry,
        config=RunConfig(max_retries=0, retry_delay_seconds=0.0),
        hook_registry=hook_registry,
        phase_configs=phase_configs,
    )

    result = await runner.run(sprint_id)

    assert result.success is True
    assert post_step_hook.call_count == 4  # Once per agent-executed phase
