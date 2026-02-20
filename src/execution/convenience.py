"""Convenience functions for common sprint execution patterns."""

from __future__ import annotations

from pathlib import Path

from src.adapters.memory import InMemoryAdapter
from src.agents.execution.registry import AgentRegistry
from src.execution.config import RunConfig
from src.execution.gates import create_default_hooks
from src.execution.hooks import HookRegistry
from src.execution.runner import RunResult, SprintRunner


def create_registry(model: str = "sonnet", max_turns: int = 25) -> AgentRegistry:
    """Create an AgentRegistry with real agents backed by ClaudeCodeExecutor."""
    from src.agents.execution.claude_code import ClaudeCodeExecutor
    from src.agents.execution.product_engineer import ProductEngineerAgent
    from src.agents.execution.quality_engineer import QualityEngineerAgent
    from src.agents.execution.test_runner import TestRunnerAgent

    executor = ClaudeCodeExecutor(model=model, max_turns=max_turns)
    registry = AgentRegistry()
    registry.register("implement", ProductEngineerAgent(executor=executor))
    registry.register("write_code", ProductEngineerAgent(executor=executor))
    registry.register("test", TestRunnerAgent(executor=executor))
    registry.register("run_tests", TestRunnerAgent(executor=executor))
    registry.register("review", QualityEngineerAgent(executor=executor))
    registry.register("quality_review", QualityEngineerAgent(executor=executor))
    return registry


def create_test_registry() -> AgentRegistry:
    """Create an AgentRegistry with mock agents for fast testing."""
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


# Backwards compat alias
create_default_registry = create_test_registry


def create_hook_registry(
    sprint_type: str = "backend",
    kanban_dir: Path | None = None,
    grooming_agent=None,
) -> HookRegistry:
    """Create a HookRegistry pre-loaded with default gates for a sprint type.

    If kanban_dir is provided, includes the GroomingHook (POST_COMPLETION)
    so grooming triggers automatically after each sprint completes.
    """
    hook_registry = HookRegistry()
    for hook in create_default_hooks(sprint_type, kanban_dir=kanban_dir, grooming_agent=grooming_agent):
        hook_registry.register(hook)
    return hook_registry


async def run_sprint(
    sprint_id: str,
    backend,
    agent_registry: AgentRegistry | None = None,
    project_root: Path | None = None,
    on_progress=None,
    kanban_dir: Path | None = None,
    synthesizer=None,
    grooming_agent=None,
    mock: bool = False,
) -> RunResult:
    """Convenience function to run a sprint with sensible defaults.

    Uses real ClaudeCodeExecutor agents by default. Pass mock=True for
    fast testing without burning tokens.
    """
    if agent_registry is None:
        agent_registry = create_registry() if not mock else create_test_registry()

    hook_registry = create_hook_registry(
        kanban_dir=kanban_dir, grooming_agent=grooming_agent,
    )

    runner = SprintRunner(
        backend=backend,
        agent_registry=agent_registry,
        project_root=project_root,
        hook_registry=hook_registry,
        kanban_dir=kanban_dir,
        synthesizer=synthesizer,
    )
    return await runner.run(sprint_id, on_progress=on_progress)
