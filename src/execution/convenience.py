"""Convenience functions for common sprint execution patterns."""

from __future__ import annotations

from pathlib import Path

from src.adapters.memory import InMemoryAdapter
from src.agents.execution.registry import AgentRegistry
from src.execution.config import RunConfig
from src.execution.gates import create_default_hooks
from src.execution.hooks import HookRegistry
from src.execution.runner import RunResult, SprintRunner


def create_default_registry() -> AgentRegistry:
    """Create an AgentRegistry with mock agents registered for common step types.

    In production, you'd register real agents. This is for demos and testing.
    """
    from src.agents.execution.mocks import (
        MockProductEngineerAgent,
        MockQualityEngineerAgent,
        MockTestRunnerAgent,
    )

    registry = AgentRegistry()
    registry.register("implement", MockProductEngineerAgent())
    registry.register("write_code", MockProductEngineerAgent())
    registry.register("test", MockTestRunnerAgent())
    registry.register("run_tests", MockTestRunnerAgent())
    registry.register("review", MockQualityEngineerAgent())
    registry.register("quality_review", MockQualityEngineerAgent())
    return registry


def create_hook_registry(sprint_type: str = "backend") -> HookRegistry:
    """Create a HookRegistry pre-loaded with default gates for a sprint type."""
    hook_registry = HookRegistry()
    for hook in create_default_hooks(sprint_type):
        hook_registry.register(hook)
    return hook_registry


async def run_sprint(
    sprint_id: str,
    backend,
    agent_registry: AgentRegistry | None = None,
    project_root: Path | None = None,
    on_progress=None,
) -> RunResult:
    """Convenience function to run a sprint with sensible defaults.

    Creates a default registry if none provided.
    """
    if agent_registry is None:
        agent_registry = create_default_registry()

    runner = SprintRunner(
        backend=backend,
        agent_registry=agent_registry,
        project_root=project_root,
    )
    return await runner.run(sprint_id, on_progress=on_progress)
