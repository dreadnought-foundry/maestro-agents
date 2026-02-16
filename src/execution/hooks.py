"""Hook system for workflow enforcement gates."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable

from src.agents.execution.types import AgentResult
from src.workflow.models import Sprint, Step


class HookPoint(Enum):
    PRE_SPRINT = "pre_sprint"
    PRE_STEP = "pre_step"
    POST_STEP = "post_step"
    PRE_COMPLETION = "pre_completion"
    POST_COMPLETION = "post_completion"


@dataclass
class HookContext:
    sprint: Sprint
    step: Step | None = None
    agent_result: AgentResult | None = None
    run_state: dict = field(default_factory=dict)


@dataclass
class HookResult:
    passed: bool
    message: str
    blocking: bool = True
    deferred_items: list[str] = field(default_factory=list)


@runtime_checkable
class Hook(Protocol):
    hook_point: HookPoint

    async def evaluate(self, context: HookContext) -> HookResult: ...


class HookRegistry:
    """Registry for hooks organized by hook point."""

    def __init__(self) -> None:
        self._hooks: dict[HookPoint, list[Hook]] = {point: [] for point in HookPoint}

    def register(self, hook: Hook) -> None:
        self._hooks[hook.hook_point].append(hook)

    def get_hooks(self, point: HookPoint) -> list[Hook]:
        return list(self._hooks[point])

    async def evaluate_all(self, point: HookPoint, context: HookContext) -> list[HookResult]:
        """Evaluate all hooks for a given point. Returns list of results."""
        results = []
        for hook in self._hooks[point]:
            result = await hook.evaluate(context)
            results.append(result)
        return results


class MockHook:
    """Configurable mock hook for testing."""

    def __init__(
        self,
        hook_point: HookPoint,
        result: HookResult | None = None,
    ) -> None:
        self.hook_point = hook_point
        self._result = result or HookResult(passed=True, message="OK")
        self.call_count = 0
        self.last_context: HookContext | None = None

    async def evaluate(self, context: HookContext) -> HookResult:
        self.call_count += 1
        self.last_context = context
        return self._result
