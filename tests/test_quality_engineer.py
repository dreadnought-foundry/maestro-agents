"""Tests for QualityEngineerAgent and MockQualityEngineerAgent."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.agents.execution.mocks import MockQualityEngineerAgent
from src.agents.execution.quality_engineer import QualityEngineerAgent
from src.agents.execution.protocol import ExecutionAgent
from src.agents.execution.types import AgentResult, StepContext
from src.workflow.models import Epic, EpicStatus, Sprint, SprintStatus, Step


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_context(
    *,
    step_name: str = "Review code",
    sprint_goal: str = "Build the widget",
    epic_title: str = "Widget Epic",
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
        description="All about widgets",
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
# MockQualityEngineerAgent tests
# ===========================================================================


class TestMockQualityEngineerAgent:
    """Tests for the mock quality engineer agent."""

    def test_satisfies_execution_agent_protocol(self) -> None:
        agent = MockQualityEngineerAgent()
        assert isinstance(agent, ExecutionAgent)

    async def test_default_result_has_approve_verdict(self) -> None:
        agent = MockQualityEngineerAgent()
        ctx = _make_context()
        result = await agent.execute(ctx)
        assert result.success is True
        assert result.review_verdict == "approve"
        assert "acceptance criteria" in result.output.lower()

    async def test_custom_result_with_request_changes(self) -> None:
        custom = AgentResult(
            success=False,
            output="Missing test coverage",
            review_verdict="request_changes",
        )
        agent = MockQualityEngineerAgent(result=custom)
        ctx = _make_context()
        result = await agent.execute(ctx)
        assert result.success is False
        assert result.review_verdict == "request_changes"

    async def test_can_configure_deferred_items(self) -> None:
        custom = AgentResult(
            success=True,
            output="Approved with notes",
            review_verdict="approve",
            deferred_items=["Add integration tests", "Improve error messages"],
        )
        agent = MockQualityEngineerAgent(result=custom)
        ctx = _make_context()
        result = await agent.execute(ctx)
        assert len(result.deferred_items) == 2
        assert "Add integration tests" in result.deferred_items

    async def test_tracks_call_count_and_last_context(self) -> None:
        agent = MockQualityEngineerAgent()
        assert agent.call_count == 0
        assert agent.last_context is None
        ctx = _make_context(step_name="QA review")
        await agent.execute(ctx)
        assert agent.call_count == 1
        assert agent.last_context is ctx
        assert agent.last_context.step.name == "QA review"


# ===========================================================================
# QualityEngineerAgent tests
# ===========================================================================


class TestQualityEngineerAgent:
    """Tests for the real quality engineer agent (structural / unit tests)."""

    def test_satisfies_execution_agent_protocol(self) -> None:
        agent = QualityEngineerAgent()
        assert isinstance(agent, ExecutionAgent)

    def test_has_correct_name_and_description(self) -> None:
        agent = QualityEngineerAgent()
        assert agent.name == "quality_engineer"
        assert "review" in agent.description.lower() or "acceptance" in agent.description.lower()

    def test_build_prompt_includes_sprint_goal_and_step_name(self) -> None:
        agent = QualityEngineerAgent()
        ctx = _make_context(step_name="Validate tests", sprint_goal="Finish auth module")
        prompt = agent._build_prompt(ctx)
        assert "Validate tests" in prompt
        assert "Finish auth module" in prompt

    def test_build_prompt_includes_previous_outputs_summary(self) -> None:
        agent = QualityEngineerAgent()
        prev = [
            AgentResult(
                success=True,
                output="Implementation done",
                files_created=["src/auth.py"],
                files_modified=["src/config.py"],
            ),
            AgentResult(success=False, output="Tests failed"),
        ]
        ctx = _make_context(previous_outputs=prev)
        prompt = agent._build_prompt(ctx)
        assert "2" in prompt  # count of previous outputs
        assert "PASS" in prompt
        assert "FAIL" in prompt
        assert "src/auth.py" in prompt
        assert "src/config.py" in prompt

    def test_build_prompt_includes_deliverables(self) -> None:
        agent = QualityEngineerAgent()
        ctx = _make_context(deliverables=["api.py", "tests/test_api.py"])
        prompt = agent._build_prompt(ctx)
        assert "api.py" in prompt
        assert "tests/test_api.py" in prompt

    def test_build_prompt_omits_previous_outputs_when_empty(self) -> None:
        agent = QualityEngineerAgent()
        ctx = _make_context(previous_outputs=[])
        prompt = agent._build_prompt(ctx)
        assert "Previous" not in prompt

    async def test_execute_returns_failure_with_error_verdict(self) -> None:
        agent = QualityEngineerAgent()
        ctx = _make_context()
        result = await agent.execute(ctx)
        assert result.success is False
        assert result.review_verdict == "error"
        assert "failed" in result.output.lower() or "error" in result.output.lower()
