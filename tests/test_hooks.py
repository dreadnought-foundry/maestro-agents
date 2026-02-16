"""TDD tests for the hook system architecture."""

from __future__ import annotations

import pytest

from src.agents.execution.types import AgentResult
from src.execution.hooks import (
    Hook,
    HookContext,
    HookPoint,
    HookRegistry,
    HookResult,
    MockHook,
)
from src.workflow.models import Sprint, SprintStatus, Step, StepStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_sprint():
    return Sprint(id="s-1", goal="Test", status=SprintStatus.IN_PROGRESS, epic_id="e-1")


@pytest.fixture
def sample_step():
    return Step(id="step-1", name="Implement")


# ---------------------------------------------------------------------------
# HookPoint
# ---------------------------------------------------------------------------

class TestHookPoint:
    def test_all_hook_points(self):
        assert HookPoint.PRE_SPRINT.value == "pre_sprint"
        assert HookPoint.PRE_STEP.value == "pre_step"
        assert HookPoint.POST_STEP.value == "post_step"
        assert HookPoint.PRE_COMPLETION.value == "pre_completion"
        assert HookPoint.POST_COMPLETION.value == "post_completion"
        assert len(HookPoint) == 5


# ---------------------------------------------------------------------------
# HookContext
# ---------------------------------------------------------------------------

class TestHookContext:
    def test_required_fields(self, sample_sprint):
        ctx = HookContext(sprint=sample_sprint)
        assert ctx.sprint is sample_sprint

    def test_defaults(self, sample_sprint):
        ctx = HookContext(sprint=sample_sprint)
        assert ctx.step is None
        assert ctx.agent_result is None
        assert ctx.run_state == {}


# ---------------------------------------------------------------------------
# HookResult
# ---------------------------------------------------------------------------

class TestHookResult:
    def test_defaults(self):
        result = HookResult(passed=True, message="OK")
        assert result.blocking is True
        assert result.deferred_items == []

    def test_with_all_fields(self):
        result = HookResult(
            passed=False,
            message="Coverage too low",
            blocking=False,
            deferred_items=["item-1", "item-2"],
        )
        assert result.passed is False
        assert result.message == "Coverage too low"
        assert result.blocking is False
        assert result.deferred_items == ["item-1", "item-2"]


# ---------------------------------------------------------------------------
# MockHook
# ---------------------------------------------------------------------------

class TestMockHook:
    def test_satisfies_hook_protocol(self):
        hook = MockHook(hook_point=HookPoint.PRE_SPRINT)
        assert isinstance(hook, Hook)

    @pytest.mark.asyncio
    async def test_returns_configured_result(self, sample_sprint):
        custom_result = HookResult(passed=False, message="blocked")
        hook = MockHook(hook_point=HookPoint.POST_STEP, result=custom_result)

        ctx = HookContext(sprint=sample_sprint)
        result = await hook.evaluate(ctx)

        assert result is custom_result
        assert hook.call_count == 1
        assert hook.last_context is ctx


# ---------------------------------------------------------------------------
# HookRegistry
# ---------------------------------------------------------------------------

class TestHookRegistry:
    def test_register_and_get(self):
        registry = HookRegistry()
        hook = MockHook(hook_point=HookPoint.PRE_SPRINT)
        registry.register(hook)
        assert hook in registry.get_hooks(HookPoint.PRE_SPRINT)

    def test_get_empty_returns_empty(self):
        registry = HookRegistry()
        assert registry.get_hooks(HookPoint.PRE_STEP) == []

    def test_multiple_hooks_same_point(self):
        registry = HookRegistry()
        hook1 = MockHook(hook_point=HookPoint.PRE_STEP)
        hook2 = MockHook(hook_point=HookPoint.PRE_STEP)
        registry.register(hook1)
        registry.register(hook2)
        hooks = registry.get_hooks(HookPoint.PRE_STEP)
        assert len(hooks) == 2
        assert hook1 in hooks
        assert hook2 in hooks

    @pytest.mark.asyncio
    async def test_evaluate_all_passes(self, sample_sprint):
        registry = HookRegistry()
        registry.register(MockHook(hook_point=HookPoint.PRE_SPRINT))
        registry.register(MockHook(hook_point=HookPoint.PRE_SPRINT))

        ctx = HookContext(sprint=sample_sprint)
        results = await registry.evaluate_all(HookPoint.PRE_SPRINT, ctx)

        assert len(results) == 2
        assert all(r.passed for r in results)

    @pytest.mark.asyncio
    async def test_evaluate_all_mixed(self, sample_sprint):
        registry = HookRegistry()
        registry.register(MockHook(hook_point=HookPoint.POST_STEP))
        registry.register(
            MockHook(
                hook_point=HookPoint.POST_STEP,
                result=HookResult(passed=False, message="fail"),
            )
        )

        ctx = HookContext(sprint=sample_sprint)
        results = await registry.evaluate_all(HookPoint.POST_STEP, ctx)

        assert len(results) == 2
        assert results[0].passed is True
        assert results[1].passed is False

    @pytest.mark.asyncio
    async def test_evaluate_all_collects_deferred_items(self, sample_sprint):
        registry = HookRegistry()
        registry.register(
            MockHook(
                hook_point=HookPoint.PRE_COMPLETION,
                result=HookResult(
                    passed=True,
                    message="deferred",
                    deferred_items=["todo-1", "todo-2"],
                ),
            )
        )

        ctx = HookContext(sprint=sample_sprint)
        results = await registry.evaluate_all(HookPoint.PRE_COMPLETION, ctx)

        assert len(results) == 1
        assert results[0].deferred_items == ["todo-1", "todo-2"]
