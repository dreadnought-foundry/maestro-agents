"""Tests for ProductEngineerAgent and MockProductEngineerAgent."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.agents.execution.mocks import MockProductEngineerAgent
from src.agents.execution.product_engineer import ProductEngineerAgent
from src.agents.execution.protocol import ExecutionAgent
from src.agents.execution.registry import AgentRegistry
from src.agents.execution.types import AgentResult, StepContext
from src.workflow.models import Epic, EpicStatus, Sprint, SprintStatus, Step


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_context(
    *,
    step_name: str = "Implement feature",
    sprint_goal: str = "Build the widget",
    epic_title: str = "Widget Epic",
    epic_description: str = "All about widgets",
    deliverables: list[str] | None = None,
    previous_outputs: list[AgentResult] | None = None,
) -> StepContext:
    step = Step(id="step-1", name=step_name)
    sprint = Sprint(
        id="sprint-1",
        goal=sprint_goal,
        status=SprintStatus.IN_PROGRESS,
        epic_id="epic-1",
        deliverables=deliverables or [],
    )
    epic = Epic(
        id="epic-1",
        title=epic_title,
        description=epic_description,
        status=EpicStatus.ACTIVE,
    )
    return StepContext(
        step=step,
        sprint=sprint,
        epic=epic,
        project_root=Path("/tmp/project"),
        previous_outputs=previous_outputs or [],
    )


# ===========================================================================
# MockProductEngineerAgent tests
# ===========================================================================


class TestMockProductEngineerAgent:
    """Tests for the mock agent used in sprint runner testing."""

    def test_satisfies_execution_agent_protocol(self) -> None:
        agent = MockProductEngineerAgent()
        assert isinstance(agent, ExecutionAgent)

    async def test_returns_default_success_result(self) -> None:
        agent = MockProductEngineerAgent()
        ctx = _make_context()
        result = await agent.execute(ctx)
        assert result.success is True
        assert result.output == "Mock implementation complete"
        assert "mock_file.py" in result.files_created

    async def test_returns_custom_result(self) -> None:
        custom = AgentResult(success=False, output="custom failure")
        agent = MockProductEngineerAgent(result=custom)
        ctx = _make_context()
        result = await agent.execute(ctx)
        assert result.success is False
        assert result.output == "custom failure"

    async def test_tracks_call_count(self) -> None:
        agent = MockProductEngineerAgent()
        ctx = _make_context()
        assert agent.call_count == 0
        await agent.execute(ctx)
        assert agent.call_count == 1
        await agent.execute(ctx)
        assert agent.call_count == 2

    async def test_captures_last_context(self) -> None:
        agent = MockProductEngineerAgent()
        assert agent.last_context is None
        ctx = _make_context(step_name="special step")
        await agent.execute(ctx)
        assert agent.last_context is ctx
        assert agent.last_context.step.name == "special step"

    def test_can_be_registered_in_agent_registry(self) -> None:
        registry = AgentRegistry()
        agent = MockProductEngineerAgent()
        registry.register("implement", agent)
        assert registry.get_agent("implement") is agent


# ===========================================================================
# ProductEngineerAgent tests
# ===========================================================================


class TestProductEngineerAgent:
    """Tests for the real product engineer agent (structural / unit tests)."""

    def test_satisfies_execution_agent_protocol(self) -> None:
        agent = ProductEngineerAgent()
        assert isinstance(agent, ExecutionAgent)

    def test_has_correct_name_and_description(self) -> None:
        agent = ProductEngineerAgent()
        assert agent.name == "product_engineer"
        assert "code" in agent.description.lower() or "write" in agent.description.lower()

    def test_build_prompt_includes_step_name(self) -> None:
        agent = ProductEngineerAgent()
        ctx = _make_context(step_name="Write unit tests")
        prompt = agent._build_prompt(ctx)
        assert "Write unit tests" in prompt

    def test_build_prompt_includes_sprint_goal(self) -> None:
        agent = ProductEngineerAgent()
        ctx = _make_context(sprint_goal="Finish authentication")
        prompt = agent._build_prompt(ctx)
        assert "Finish authentication" in prompt

    def test_build_prompt_includes_epic_title(self) -> None:
        agent = ProductEngineerAgent()
        ctx = _make_context(epic_title="Auth Epic", epic_description="User auth system")
        prompt = agent._build_prompt(ctx)
        assert "Auth Epic" in prompt
        assert "User auth system" in prompt

    def test_build_prompt_includes_previous_outputs_count(self) -> None:
        agent = ProductEngineerAgent()
        prev = [
            AgentResult(success=True, output="step 1 done"),
            AgentResult(success=True, output="step 2 done"),
        ]
        ctx = _make_context(previous_outputs=prev)
        prompt = agent._build_prompt(ctx)
        assert "2" in prompt

    def test_build_prompt_omits_previous_outputs_when_empty(self) -> None:
        agent = ProductEngineerAgent()
        ctx = _make_context(previous_outputs=[])
        prompt = agent._build_prompt(ctx)
        assert "Previous" not in prompt

    def test_build_prompt_includes_deliverables(self) -> None:
        agent = ProductEngineerAgent()
        ctx = _make_context(deliverables=["api.py", "tests/test_api.py"])
        prompt = agent._build_prompt(ctx)
        assert "api.py" in prompt
        assert "tests/test_api.py" in prompt

    def test_build_prompt_omits_deliverables_when_empty(self) -> None:
        agent = ProductEngineerAgent()
        ctx = _make_context(deliverables=[])
        prompt = agent._build_prompt(ctx)
        assert "deliverable" not in prompt.lower()

    async def test_execute_returns_failure_when_sdk_unavailable(self) -> None:
        agent = ProductEngineerAgent()
        ctx = _make_context()
        result = await agent.execute(ctx)
        assert result.success is False
        assert "failed" in result.output.lower() or "error" in result.output.lower()
