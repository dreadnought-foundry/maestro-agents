"""Tests for DAG-based step scheduler and parallel execution."""

from __future__ import annotations

import asyncio
import time

import pytest

from src.adapters.memory import InMemoryAdapter
from src.agents.execution.mocks import MockProductEngineerAgent
from src.agents.execution.registry import AgentRegistry
from src.agents.execution.types import AgentResult
from src.execution.config import RunConfig
from src.execution.phases import Phase, PhaseConfig, PhaseResult
from src.execution.runner import RunResult, SprintRunner
from src.execution.scheduler import CyclicDependencyError, Scheduler, steps_to_sequential
from src.workflow.models import Step, StepStatus


# ===========================================================================
# Scheduler unit tests
# ===========================================================================


class TestSchedulerBasic:
    def test_no_deps_all_ready(self):
        """Steps with no dependencies are all immediately ready."""
        steps = [
            Step(id="a", name="build_backend"),
            Step(id="b", name="build_frontend"),
            Step(id="c", name="build_docs"),
        ]
        scheduler = Scheduler(steps)
        ready = scheduler.get_ready_steps()

        assert len(ready) == 3
        assert {s.id for s in ready} == {"a", "b", "c"}

    def test_linear_deps_sequential(self):
        """Linear dependencies produce sequential execution."""
        steps = [
            Step(id="a", name="plan"),
            Step(id="b", name="build", depends_on=["a"]),
            Step(id="c", name="test", depends_on=["b"]),
        ]
        scheduler = Scheduler(steps)

        # Only A is ready initially
        ready = scheduler.get_ready_steps()
        assert [s.id for s in ready] == ["a"]

        scheduler.mark_in_progress("a")
        scheduler.mark_complete("a")

        # Now B is ready
        ready = scheduler.get_ready_steps()
        assert [s.id for s in ready] == ["b"]

        scheduler.mark_in_progress("b")
        scheduler.mark_complete("b")

        # Now C is ready
        ready = scheduler.get_ready_steps()
        assert [s.id for s in ready] == ["c"]

    def test_diamond_pattern(self):
        """Diamond: A→C, B→C. A and B run in parallel, C waits for both."""
        steps = [
            Step(id="a", name="build_backend"),
            Step(id="b", name="build_frontend"),
            Step(id="c", name="run_tests", depends_on=["a", "b"]),
        ]
        scheduler = Scheduler(steps)

        ready = scheduler.get_ready_steps()
        assert {s.id for s in ready} == {"a", "b"}

        scheduler.mark_in_progress("a")
        scheduler.mark_in_progress("b")

        # C not ready yet (A and B still in progress)
        assert scheduler.get_ready_steps() == []

        scheduler.mark_complete("a")
        # C still not ready (B still in progress)
        assert scheduler.get_ready_steps() == []

        scheduler.mark_complete("b")
        # Now C is ready
        ready = scheduler.get_ready_steps()
        assert [s.id for s in ready] == ["c"]

    def test_mark_complete_unlocks_dependents(self):
        """Completing a step unlocks its dependents."""
        steps = [
            Step(id="a", name="first"),
            Step(id="b", name="second", depends_on=["a"]),
        ]
        scheduler = Scheduler(steps)

        assert len(scheduler.get_ready_steps()) == 1  # only A
        scheduler.mark_in_progress("a")
        scheduler.mark_complete("a")
        assert len(scheduler.get_ready_steps()) == 1  # now B

    def test_mark_failed_blocks_dependents(self):
        """Failed step prevents dependents from becoming ready."""
        steps = [
            Step(id="a", name="first"),
            Step(id="b", name="second", depends_on=["a"]),
        ]
        scheduler = Scheduler(steps)

        scheduler.mark_in_progress("a")
        scheduler.mark_failed("a")

        # B can never become ready
        assert scheduler.get_ready_steps() == []
        assert scheduler.is_done()
        assert scheduler.has_failures()

    def test_is_done_when_all_complete(self):
        """is_done returns True when all steps completed."""
        steps = [Step(id="a", name="only")]
        scheduler = Scheduler(steps)

        assert not scheduler.is_done()
        scheduler.mark_in_progress("a")
        assert not scheduler.is_done()
        scheduler.mark_complete("a")
        assert scheduler.is_done()

    def test_is_done_with_failures(self):
        """is_done returns True when all steps are either completed or failed."""
        steps = [
            Step(id="a", name="first"),
            Step(id="b", name="second"),
        ]
        scheduler = Scheduler(steps)

        scheduler.mark_in_progress("a")
        scheduler.mark_complete("a")
        scheduler.mark_in_progress("b")
        scheduler.mark_failed("b")

        assert scheduler.is_done()
        assert scheduler.has_failures()

    def test_cycle_detection(self):
        """Cyclic dependencies raise CyclicDependencyError."""
        steps = [
            Step(id="a", name="first", depends_on=["b"]),
            Step(id="b", name="second", depends_on=["a"]),
        ]
        with pytest.raises(CyclicDependencyError):
            Scheduler(steps)

    def test_self_cycle_detection(self):
        """Step depending on itself raises CyclicDependencyError."""
        steps = [Step(id="a", name="first", depends_on=["a"])]
        with pytest.raises(CyclicDependencyError):
            Scheduler(steps)

    def test_unknown_dep_ignored(self):
        """Dependencies on unknown step IDs are ignored (treated as met)."""
        steps = [Step(id="a", name="first", depends_on=["nonexistent"])]
        scheduler = Scheduler(steps)
        ready = scheduler.get_ready_steps()
        assert [s.id for s in ready] == ["a"]

    def test_unknown_step_id_raises(self):
        """Operations on unknown step IDs raise KeyError."""
        scheduler = Scheduler([Step(id="a", name="first")])
        with pytest.raises(KeyError):
            scheduler.mark_complete("unknown")
        with pytest.raises(KeyError):
            scheduler.mark_failed("unknown")
        with pytest.raises(KeyError):
            scheduler.mark_in_progress("unknown")

    def test_completed_and_failed_ids(self):
        """Properties expose completed and failed step IDs."""
        steps = [Step(id="a", name="first"), Step(id="b", name="second")]
        scheduler = Scheduler(steps)

        scheduler.mark_in_progress("a")
        scheduler.mark_complete("a")
        scheduler.mark_in_progress("b")
        scheduler.mark_failed("b")

        assert scheduler.completed_ids == {"a"}
        assert scheduler.failed_ids == {"b"}


class TestStepsToSequential:
    def test_adds_linear_deps(self):
        """steps_to_sequential chains steps without deps."""
        steps = [
            Step(id="a", name="first"),
            Step(id="b", name="second"),
            Step(id="c", name="third"),
        ]
        result = steps_to_sequential(steps)

        assert result[0].depends_on == []
        assert result[1].depends_on == ["a"]
        assert result[2].depends_on == ["b"]

    def test_preserves_existing_deps(self):
        """steps_to_sequential does nothing if any step has depends_on."""
        steps = [
            Step(id="a", name="first"),
            Step(id="b", name="second", depends_on=["a"]),
        ]
        result = steps_to_sequential(steps)

        assert result[0].depends_on == []
        assert result[1].depends_on == ["a"]

    def test_single_step(self):
        """Single step remains unchanged."""
        steps = [Step(id="a", name="only")]
        result = steps_to_sequential(steps)
        assert result[0].depends_on == []

    def test_empty_list(self):
        """Empty list returns empty."""
        assert steps_to_sequential([]) == []


# ===========================================================================
# Parallel execution integration tests (with SprintRunner)
# ===========================================================================

async def _setup(tasks=None):
    """Create backend with one epic and one sprint."""
    backend = InMemoryAdapter()
    epic = await backend.create_epic("Test Epic", "Testing")
    tasks = tasks or [{"name": "implement"}]
    sprint = await backend.create_sprint(epic.id, "Build feature", tasks=tasks)
    return backend, sprint.id


async def test_parallel_steps_run_concurrently():
    """Independent steps within a phase run concurrently (faster than sequential)."""
    backend, sprint_id = await _setup()

    # Agent that takes ~50ms to execute
    class SlowAgent:
        name = "slow_agent"
        description = "Agent with artificial delay"

        def __init__(self, delay: float = 0.05):
            self._delay = delay
            self.call_count = 0

        async def execute(self, context):
            self.call_count += 1
            await asyncio.sleep(self._delay)
            return AgentResult(success=True, output=f"done-{context.step.id}")

    agent_a = SlowAgent()
    agent_b = SlowAgent()

    registry = AgentRegistry()
    registry.register("build_backend", agent_a)
    registry.register("build_frontend", agent_b)

    # Two independent steps in BUILD phase
    parallel_steps = [
        Step(id="s1", name="build_backend", status=StepStatus.TODO,
             metadata={"type": "build_backend"}),
        Step(id="s2", name="build_frontend", status=StepStatus.TODO,
             metadata={"type": "build_frontend"}),
    ]

    phase_configs = [
        PhaseConfig(phase=Phase.BUILD, steps=parallel_steps, max_retries=0),
        PhaseConfig(phase=Phase.REVIEW, agent_type=None),
    ]

    runner = SprintRunner(
        backend=backend,
        agent_registry=registry,
        config=RunConfig(max_retries=0, retry_delay_seconds=0.0),
        phase_configs=phase_configs,
    )

    start = time.monotonic()
    result = await runner.run(sprint_id)
    elapsed = time.monotonic() - start

    assert result.success is True
    assert agent_a.call_count == 1
    assert agent_b.call_count == 1
    # Parallel should take ~50ms, sequential would take ~100ms
    assert elapsed < 0.09  # generous margin but less than 2x


async def test_dependent_steps_wait():
    """Steps with dependencies wait for their prerequisites."""
    backend, sprint_id = await _setup()

    execution_order = []

    class TrackingAgent:
        name = "tracking"
        description = "Tracks execution order"

        def __init__(self, label: str):
            self._label = label

        async def execute(self, context):
            execution_order.append(self._label)
            return AgentResult(success=True, output=f"done-{self._label}")

    registry = AgentRegistry()
    registry.register("build_backend", TrackingAgent("backend"))
    registry.register("build_frontend", TrackingAgent("frontend"))
    registry.register("run_tests", TrackingAgent("tests"))

    # Diamond: backend + frontend → tests
    steps = [
        Step(id="s1", name="build_backend", status=StepStatus.TODO,
             metadata={"type": "build_backend"}),
        Step(id="s2", name="build_frontend", status=StepStatus.TODO,
             metadata={"type": "build_frontend"}),
        Step(id="s3", name="run_tests", status=StepStatus.TODO,
             depends_on=["s1", "s2"], metadata={"type": "run_tests"}),
    ]

    phase_configs = [
        PhaseConfig(phase=Phase.BUILD, steps=steps, max_retries=0),
        PhaseConfig(phase=Phase.REVIEW, agent_type=None),
    ]

    runner = SprintRunner(
        backend=backend,
        agent_registry=registry,
        config=RunConfig(max_retries=0, retry_delay_seconds=0.0),
        phase_configs=phase_configs,
    )

    result = await runner.run(sprint_id)

    assert result.success is True
    # Tests must run after both build steps
    assert execution_order.index("tests") > execution_order.index("backend")
    assert execution_order.index("tests") > execution_order.index("frontend")


async def test_partial_failure_in_parallel():
    """When one parallel step fails, other running steps complete, then sprint blocks."""
    backend, sprint_id = await _setup()

    success_agent = MockProductEngineerAgent(
        result=AgentResult(success=True, output="ok")
    )
    failing_agent = MockProductEngineerAgent(
        result=AgentResult(success=False, output="failed")
    )

    registry = AgentRegistry()
    registry.register("good", success_agent)
    registry.register("bad", failing_agent)

    steps = [
        Step(id="s1", name="good_step", status=StepStatus.TODO,
             metadata={"type": "good"}),
        Step(id="s2", name="bad_step", status=StepStatus.TODO,
             metadata={"type": "bad"}),
    ]

    phase_configs = [
        PhaseConfig(phase=Phase.BUILD, steps=steps, max_retries=0),
        PhaseConfig(phase=Phase.REVIEW, agent_type=None),
    ]

    runner = SprintRunner(
        backend=backend,
        agent_registry=registry,
        config=RunConfig(max_retries=0, retry_delay_seconds=0.0),
        phase_configs=phase_configs,
    )

    result = await runner.run(sprint_id)

    assert result.success is False
    # Both agents were called (they ran concurrently)
    assert success_agent.call_count == 1
    assert failing_agent.call_count == 1
    assert len(result.agent_results) == 2


async def test_dependent_step_skipped_on_failure():
    """Steps depending on a failed step never execute."""
    backend, sprint_id = await _setup()

    failing_agent = MockProductEngineerAgent(
        result=AgentResult(success=False, output="failed")
    )
    dependent_agent = MockProductEngineerAgent()

    registry = AgentRegistry()
    registry.register("build", failing_agent)
    registry.register("test", dependent_agent)

    steps = [
        Step(id="s1", name="build", status=StepStatus.TODO,
             metadata={"type": "build"}),
        Step(id="s2", name="test", status=StepStatus.TODO,
             depends_on=["s1"], metadata={"type": "test"}),
    ]

    phase_configs = [
        PhaseConfig(phase=Phase.BUILD, steps=steps, max_retries=0),
        PhaseConfig(phase=Phase.REVIEW, agent_type=None),
    ]

    runner = SprintRunner(
        backend=backend,
        agent_registry=registry,
        config=RunConfig(max_retries=0, retry_delay_seconds=0.0),
        phase_configs=phase_configs,
    )

    result = await runner.run(sprint_id)

    assert result.success is False
    assert failing_agent.call_count == 1
    assert dependent_agent.call_count == 0  # never reached


async def test_deferred_items_from_parallel_steps():
    """Deferred items are collected from all parallel steps."""
    backend, sprint_id = await _setup()

    agent_a = MockProductEngineerAgent(
        result=AgentResult(success=True, output="ok", deferred_items=["TODO-A"])
    )
    agent_b = MockProductEngineerAgent(
        result=AgentResult(success=True, output="ok", deferred_items=["TODO-B"])
    )

    registry = AgentRegistry()
    registry.register("step_a", agent_a)
    registry.register("step_b", agent_b)

    steps = [
        Step(id="s1", name="step_a", status=StepStatus.TODO,
             metadata={"type": "step_a"}),
        Step(id="s2", name="step_b", status=StepStatus.TODO,
             metadata={"type": "step_b"}),
    ]

    phase_configs = [
        PhaseConfig(phase=Phase.BUILD, steps=steps, max_retries=0),
        PhaseConfig(phase=Phase.REVIEW, agent_type=None),
    ]

    runner = SprintRunner(
        backend=backend,
        agent_registry=registry,
        config=RunConfig(max_retries=0, retry_delay_seconds=0.0),
        phase_configs=phase_configs,
    )

    result = await runner.run(sprint_id)

    assert result.success is True
    assert "TODO-A" in result.deferred_items
    assert "TODO-B" in result.deferred_items


async def test_single_agent_phase_still_works():
    """Phases with agent_type (no steps) still work as before."""
    backend, sprint_id = await _setup()

    mock = MockProductEngineerAgent()
    registry = AgentRegistry()
    registry.register("plan", mock)

    phase_configs = [
        PhaseConfig(phase=Phase.PLAN, agent_type="plan", max_retries=0),
        PhaseConfig(phase=Phase.REVIEW, agent_type=None),
    ]

    runner = SprintRunner(
        backend=backend,
        agent_registry=registry,
        config=RunConfig(max_retries=0, retry_delay_seconds=0.0),
        phase_configs=phase_configs,
    )

    result = await runner.run(sprint_id)

    assert result.success is True
    assert mock.call_count == 1


async def test_mixed_phases_single_and_parallel():
    """Sprint with both single-agent and parallel phases."""
    backend, sprint_id = await _setup()

    plan_agent = MockProductEngineerAgent()
    build_a = MockProductEngineerAgent()
    build_b = MockProductEngineerAgent()

    registry = AgentRegistry()
    registry.register("plan", plan_agent)
    registry.register("build_a", build_a)
    registry.register("build_b", build_b)

    parallel_steps = [
        Step(id="ba", name="build_a", status=StepStatus.TODO,
             metadata={"type": "build_a"}),
        Step(id="bb", name="build_b", status=StepStatus.TODO,
             metadata={"type": "build_b"}),
    ]

    phase_configs = [
        PhaseConfig(phase=Phase.PLAN, agent_type="plan", max_retries=0),
        PhaseConfig(phase=Phase.BUILD, steps=parallel_steps, max_retries=0),
        PhaseConfig(phase=Phase.REVIEW, agent_type=None),
    ]

    runner = SprintRunner(
        backend=backend,
        agent_registry=registry,
        config=RunConfig(max_retries=0, retry_delay_seconds=0.0),
        phase_configs=phase_configs,
    )

    result = await runner.run(sprint_id)

    assert result.success is True
    assert plan_agent.call_count == 1
    assert build_a.call_count == 1
    assert build_b.call_count == 1
    assert len(result.phase_results) == 2  # PLAN + BUILD (REVIEW stops)
