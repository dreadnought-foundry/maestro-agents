"""Tests for TestRunnerAgent and MockTestRunnerAgent."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.agents.execution.mocks import MockTestRunnerAgent
from src.agents.execution.protocol import ExecutionAgent
from src.agents.execution.test_runner import TestRunnerAgent
from src.agents.execution.types import AgentResult, StepContext
from src.workflow.models import Epic, EpicStatus, Sprint, SprintStatus, Step


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_context(
    *,
    step_name: str = "Run tests",
    sprint_goal: str = "Build the widget",
    epic_title: str = "Widget Epic",
    epic_description: str = "All about widgets",
    previous_outputs: list[AgentResult] | None = None,
) -> StepContext:
    step = Step(id="step-1", name=step_name)
    sprint = Sprint(
        id="sprint-1",
        goal=sprint_goal,
        status=SprintStatus.IN_PROGRESS,
        epic_id="epic-1",
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
# MockTestRunnerAgent tests
# ===========================================================================


class TestMockTestRunnerAgent:
    """Tests for the mock test runner used in sprint runner testing."""

    def test_satisfies_execution_agent_protocol(self) -> None:
        agent = MockTestRunnerAgent()
        assert isinstance(agent, ExecutionAgent)

    @pytest.mark.asyncio
    async def test_returns_default_result_with_test_results_and_coverage(self) -> None:
        agent = MockTestRunnerAgent()
        ctx = _make_context()
        result = await agent.execute(ctx)
        assert result.success is True
        assert result.output == "All tests passed"
        assert result.test_results is not None
        assert result.test_results["total"] == 10
        assert result.test_results["passed"] == 10
        assert result.test_results["failed"] == 0
        assert result.test_results["errors"] == 0
        assert result.test_results["failed_tests"] == []
        assert result.coverage == 95.0

    @pytest.mark.asyncio
    async def test_tracks_call_count_and_last_context(self) -> None:
        agent = MockTestRunnerAgent()
        ctx = _make_context(step_name="special test step")
        assert agent.call_count == 0
        assert agent.last_context is None
        await agent.execute(ctx)
        assert agent.call_count == 1
        assert agent.last_context is ctx
        assert agent.last_context.step.name == "special test step"
        await agent.execute(ctx)
        assert agent.call_count == 2


# ===========================================================================
# TestRunnerAgent tests
# ===========================================================================


class TestTestRunnerAgent:
    """Tests for the real test runner agent (structural / unit tests)."""

    def test_satisfies_execution_agent_protocol(self) -> None:
        agent = TestRunnerAgent()
        assert isinstance(agent, ExecutionAgent)

    def test_has_correct_name_and_description(self) -> None:
        agent = TestRunnerAgent()
        assert agent.name == "test_runner"
        assert "pytest" in agent.description.lower() or "test" in agent.description.lower()

    def test_build_command_includes_project_root(self) -> None:
        agent = TestRunnerAgent()
        cmd = agent._build_command(Path("/my/project"))
        assert "/my/project" in cmd
        assert "pytest" in cmd

    def test_parse_results_all_passing(self) -> None:
        agent = TestRunnerAgent()
        stdout = (
            "tests/test_foo.py::test_one PASSED\n"
            "tests/test_foo.py::test_two PASSED\n"
            "========================= 5 passed in 0.42s =========================\n"
        )
        result = agent._parse_results(stdout, returncode=0)
        assert result.success is True
        assert result.test_results is not None
        assert result.test_results["passed"] == 5
        assert result.test_results["failed"] == 0
        assert result.test_results["total"] == 5
        assert result.test_results["failed_tests"] == []

    def test_parse_results_with_failures(self) -> None:
        agent = TestRunnerAgent()
        stdout = (
            "tests/test_foo.py::test_one PASSED\n"
            "tests/test_foo.py::test_two FAILED\n"
            "FAILED tests/test_foo.py::test_two - AssertionError\n"
            "=================== 3 passed, 2 failed in 0.55s ====================\n"
        )
        result = agent._parse_results(stdout, returncode=1)
        assert result.success is False
        assert result.test_results is not None
        assert result.test_results["passed"] == 3
        assert result.test_results["failed"] == 2
        assert result.test_results["total"] == 5
        assert "tests/test_foo.py::test_two" in result.test_results["failed_tests"]

    def test_parse_results_with_coverage(self) -> None:
        agent = TestRunnerAgent()
        stdout = (
            "tests/test_foo.py::test_one PASSED\n"
            "========================= 4 passed in 0.30s =========================\n"
            "----------- coverage: platform linux, python 3.12 -----------\n"
            "Name          Stmts   Miss  Cover\n"
            "src/foo.py       20      2    90%\n"
            "TOTAL            20      2    90%\n"
        )
        result = agent._parse_results(stdout, returncode=0)
        assert result.success is True
        assert result.coverage == 90.0

    @pytest.mark.asyncio
    async def test_execute_returns_failure_when_subprocess_unavailable(self) -> None:
        agent = TestRunnerAgent()
        ctx = _make_context()
        result = await agent.execute(ctx)
        assert result.success is False
        assert "failed" in result.output.lower() or "error" in result.output.lower()
