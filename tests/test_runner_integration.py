"""TDD tests for Sprint 22: Runner Integration — dependencies, hooks, retry."""

from __future__ import annotations

import pytest

from src.adapters.memory import InMemoryAdapter
from src.agents.execution.mocks import MockProductEngineerAgent
from src.agents.execution.registry import AgentRegistry
from src.agents.execution.types import AgentResult
from src.execution.config import RunConfig
from src.execution.hooks import HookPoint, HookRegistry, HookResult, MockHook
from src.execution.runner import RunResult, SprintRunner
from src.workflow.exceptions import DependencyNotMetError
from src.workflow.models import SprintStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _setup(tasks=None, dependencies=None):
    """Create backend with one epic and one sprint, return (backend, sprint_id, epic_id)."""
    backend = InMemoryAdapter()
    epic = await backend.create_epic("Test Epic", "An epic for testing")
    tasks = tasks or [{"name": "implement"}]
    sprint = await backend.create_sprint(
        epic.id, "Build feature", tasks=tasks, dependencies=dependencies,
    )
    return backend, sprint.id, epic.id


def _registry(mock_agent=None, names=None):
    """Create an AgentRegistry with a mock agent for given step names."""
    registry = AgentRegistry()
    agent = mock_agent or MockProductEngineerAgent()
    for name in (names or ["implement", "test", "review"]):
        registry.register(name, agent)
    return registry


class FailNTimesAgent:
    """Fails N times then succeeds."""
    name = "fail_n"
    description = "Fails N times"

    def __init__(self, fail_count: int):
        self._fail_count = fail_count
        self._attempts = 0

    async def execute(self, context):
        self._attempts += 1
        if self._attempts <= self._fail_count:
            return AgentResult(success=False, output=f"Attempt {self._attempts} failed")
        return AgentResult(success=True, output=f"Succeeded on attempt {self._attempts}")


# ---------------------------------------------------------------------------
# Dependency checking (2 tests)
# ---------------------------------------------------------------------------

class TestRunnerDependencies:
    async def test_runner_checks_dependencies_before_start(self):
        """Runner calls validate_sprint_dependencies — met deps proceed normally."""
        backend = InMemoryAdapter()
        epic = await backend.create_epic("E", "desc")
        dep = await backend.create_sprint(epic.id, "Dep sprint", tasks=[{"name": "implement"}])
        # Complete the dependency sprint
        await backend.start_sprint(dep.id)
        await backend.advance_step(dep.id, {"output": "done"})
        await backend.complete_sprint(dep.id)

        main = await backend.create_sprint(
            epic.id, "Main sprint",
            tasks=[{"name": "implement"}],
            dependencies=[dep.id],
        )
        runner = SprintRunner(
            backend=backend,
            agent_registry=_registry(),
        )
        result = await runner.run(main.id)
        assert result.success is True

    async def test_runner_unmet_deps_raises(self):
        """Runner with unmet dependencies raises DependencyNotMetError."""
        backend = InMemoryAdapter()
        epic = await backend.create_epic("E", "desc")
        dep = await backend.create_sprint(epic.id, "Dep sprint", tasks=[{"name": "implement"}])
        # dep is still TODO — not met

        main = await backend.create_sprint(
            epic.id, "Main sprint",
            tasks=[{"name": "implement"}],
            dependencies=[dep.id],
        )
        runner = SprintRunner(
            backend=backend,
            agent_registry=_registry(),
        )
        with pytest.raises(DependencyNotMetError):
            await runner.run(main.id)


# ---------------------------------------------------------------------------
# Hook evaluation (4 tests)
# ---------------------------------------------------------------------------

class TestRunnerHooks:
    async def test_pre_sprint_hooks_evaluated(self):
        """PRE_SPRINT hooks are evaluated before execution begins."""
        backend, sprint_id, _ = await _setup()
        hook = MockHook(hook_point=HookPoint.PRE_SPRINT)
        hook_registry = HookRegistry()
        hook_registry.register(hook)

        runner = SprintRunner(
            backend=backend,
            agent_registry=_registry(),
            hook_registry=hook_registry,
        )
        await runner.run(sprint_id)
        assert hook.call_count == 1

    async def test_post_step_hooks_evaluated_per_step(self):
        """POST_STEP hooks are evaluated after each step."""
        backend, sprint_id, _ = await _setup(
            tasks=[{"name": "implement"}, {"name": "test"}]
        )
        hook = MockHook(hook_point=HookPoint.POST_STEP)
        hook_registry = HookRegistry()
        hook_registry.register(hook)

        runner = SprintRunner(
            backend=backend,
            agent_registry=_registry(),
            hook_registry=hook_registry,
        )
        await runner.run(sprint_id)
        assert hook.call_count == 2

    async def test_blocking_hook_failure_blocks_sprint(self):
        """A blocking hook that fails should block the sprint."""
        backend, sprint_id, _ = await _setup()
        hook = MockHook(
            hook_point=HookPoint.PRE_SPRINT,
            result=HookResult(passed=False, message="Gate failed", blocking=True),
        )
        hook_registry = HookRegistry()
        hook_registry.register(hook)

        runner = SprintRunner(
            backend=backend,
            agent_registry=_registry(),
            hook_registry=hook_registry,
        )
        result = await runner.run(sprint_id)
        assert result.success is False
        sprint = await backend.get_sprint(sprint_id)
        assert sprint.status is SprintStatus.BLOCKED

    async def test_non_blocking_hook_failure_continues(self):
        """A non-blocking hook failure should not stop execution."""
        backend, sprint_id, _ = await _setup()
        hook = MockHook(
            hook_point=HookPoint.POST_STEP,
            result=HookResult(passed=False, message="Warning", blocking=False),
        )
        hook_registry = HookRegistry()
        hook_registry.register(hook)

        runner = SprintRunner(
            backend=backend,
            agent_registry=_registry(),
            hook_registry=hook_registry,
        )
        result = await runner.run(sprint_id)
        assert result.success is True


# ---------------------------------------------------------------------------
# Pre-completion hooks (1 test)
# ---------------------------------------------------------------------------

class TestRunnerPreCompletion:
    async def test_pre_completion_hooks_evaluated(self):
        """PRE_COMPLETION hooks are evaluated before completing the sprint."""
        backend, sprint_id, _ = await _setup()
        hook = MockHook(hook_point=HookPoint.PRE_COMPLETION)
        hook_registry = HookRegistry()
        hook_registry.register(hook)

        runner = SprintRunner(
            backend=backend,
            agent_registry=_registry(),
            hook_registry=hook_registry,
        )
        await runner.run(sprint_id)
        assert hook.call_count == 1

    async def test_pre_completion_blocking_failure_blocks(self):
        """A blocking PRE_COMPLETION hook failure should block the sprint."""
        backend, sprint_id, _ = await _setup()
        hook = MockHook(
            hook_point=HookPoint.PRE_COMPLETION,
            result=HookResult(passed=False, message="Review missing", blocking=True),
        )
        hook_registry = HookRegistry()
        hook_registry.register(hook)

        runner = SprintRunner(
            backend=backend,
            agent_registry=_registry(),
            hook_registry=hook_registry,
        )
        result = await runner.run(sprint_id)
        assert result.success is False


# ---------------------------------------------------------------------------
# Retry logic (2 tests)
# ---------------------------------------------------------------------------

class TestRunnerRetry:
    async def test_retry_on_agent_failure(self):
        """Runner retries failed step up to max_retries before blocking."""
        backend, sprint_id, _ = await _setup()
        agent = FailNTimesAgent(fail_count=1)  # Fails once, then succeeds
        registry = AgentRegistry()
        registry.register("implement", agent)

        config = RunConfig(max_retries=2, retry_delay_seconds=0.0)
        runner = SprintRunner(
            backend=backend,
            agent_registry=registry,
            config=config,
        )
        result = await runner.run(sprint_id)
        assert result.success is True
        assert agent._attempts == 2  # 1 fail + 1 success

    async def test_blocks_after_exhausting_retries(self):
        """Runner blocks sprint after exhausting all retries."""
        backend, sprint_id, _ = await _setup()
        agent = FailNTimesAgent(fail_count=999)  # Always fails
        registry = AgentRegistry()
        registry.register("implement", agent)

        config = RunConfig(max_retries=2, retry_delay_seconds=0.0)
        runner = SprintRunner(
            backend=backend,
            agent_registry=registry,
            config=config,
        )
        result = await runner.run(sprint_id)
        assert result.success is False
        assert agent._attempts == 3  # 1 initial + 2 retries
        sprint = await backend.get_sprint(sprint_id)
        assert sprint.status is SprintStatus.BLOCKED


# ---------------------------------------------------------------------------
# Run state / hook context (1 test)
# ---------------------------------------------------------------------------

class TestRunnerRunState:
    async def test_hook_context_has_agent_results(self):
        """POST_STEP hook context includes the agent result for that step."""
        backend, sprint_id, _ = await _setup()
        hook = MockHook(hook_point=HookPoint.POST_STEP)
        hook_registry = HookRegistry()
        hook_registry.register(hook)

        runner = SprintRunner(
            backend=backend,
            agent_registry=_registry(),
            hook_registry=hook_registry,
        )
        await runner.run(sprint_id)

        # The hook should have received context with agent_result set
        assert hook.last_context is not None
        assert hook.last_context.agent_result is not None
        assert hook.last_context.agent_result.success is True


# ---------------------------------------------------------------------------
# Resume transition fix (1 test)
# ---------------------------------------------------------------------------

class TestResumeTransition:
    async def test_resume_uses_validate_transition(self):
        """resume_sprint uses validate_transition (not raw update_sprint)."""
        from src.execution.resume import resume_sprint

        backend, sprint_id, _ = await _setup(
            tasks=[{"name": "implement"}, {"name": "test"}]
        )
        registry = _registry()

        # Start, complete first step, block
        await backend.start_sprint(sprint_id)
        await backend.advance_step(sprint_id, {"output": "done"})
        await backend.block_sprint(sprint_id, "test block")

        # Resume should work (BLOCKED -> IN_PROGRESS is valid)
        result = await resume_sprint(sprint_id, backend, registry)
        assert result.success is True

        # Trying to resume a TODO sprint should fail with InvalidTransitionError
        backend2, sprint_id2, _ = await _setup()
        from src.workflow.exceptions import InvalidTransitionError
        with pytest.raises((ValueError, InvalidTransitionError)):
            await resume_sprint(sprint_id2, backend2, registry)
