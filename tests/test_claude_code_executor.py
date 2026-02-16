"""Tests for ClaudeCodeExecutor and agent wiring.

Slow tests use haiku + max_turns=1 for speed — they verify wiring, not output quality.
Only 2 real SDK calls: one for executor, one for all 3 agents (batched).
The timeout test mocks query() since we can't force a real timeout reliably.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from src.agents.execution.claude_code import ClaudeCodeExecutor
from src.agents.execution.product_engineer import ProductEngineerAgent
from src.agents.execution.quality_engineer import QualityEngineerAgent
from src.agents.execution.test_runner import TestRunnerAgent
from src.agents.execution.types import AgentResult, StepContext
from src.workflow.models import Epic, EpicStatus, Sprint, SprintStatus, Step, StepStatus

# Use haiku + 1 turn for smoke tests — fast API round-trip, just verifies wiring.
_FAST_EXECUTOR = ClaudeCodeExecutor(model="haiku", max_turns=1)


# --- Fixtures ---


@pytest.fixture
def working_dir(tmp_path):
    return tmp_path


@pytest.fixture
def sample_context(tmp_path):
    return StepContext(
        step=Step(id="step-1", name="implement", status=StepStatus.TODO, agent="coder"),
        sprint=Sprint(
            id="sprint-25",
            goal="Say hello",
            status=SprintStatus.IN_PROGRESS,
            epic_id="epic-7",
        ),
        epic=Epic(
            id="epic-7",
            title="Test",
            description="Test",
            status=EpicStatus.ACTIVE,
        ),
        project_root=tmp_path,
    )


# --- ClaudeCodeExecutor tests ---


class TestClaudeCodeExecutor:
    @pytest.mark.slow
    @pytest.mark.timeout(60)
    async def test_prompt_and_result_shape(self, working_dir):
        """One real SDK call: verify output text and AgentResult shape."""
        result = await _FAST_EXECUTOR.run(
            "Respond with exactly: HELLO_TEST_PASS",
            working_dir,
            allowed_tools=[],
        )
        assert result.success is True
        assert isinstance(result, AgentResult)
        assert "HELLO_TEST_PASS" in result.output
        assert isinstance(result.files_created, list)
        assert isinstance(result.files_modified, list)

    async def test_timeout_handling(self, working_dir):
        """Timeout produces a failed AgentResult (mocked, no real SDK call)."""
        async def _hang(*, prompt, options):
            import asyncio
            await asyncio.sleep(999)
            yield  # pragma: no cover

        executor = ClaudeCodeExecutor(model="haiku", max_turns=1)
        with patch("src.agents.execution.claude_code.query", _hang):
            result = await executor.run("hang", working_dir, timeout=1)

        assert result.success is False
        assert "timed out" in result.output


# --- Agent wiring tests ---


class TestAgentWiring:
    """Verify each agent type calls the executor and returns an AgentResult."""

    async def test_no_executor_fails_gracefully_product(self, sample_context):
        result = await ProductEngineerAgent().execute(sample_context)
        assert result.success is False
        assert "No ClaudeCodeExecutor" in result.output

    async def test_no_executor_fails_gracefully_test_runner(self, sample_context):
        result = await TestRunnerAgent().execute(sample_context)
        assert result.success is False
        assert "No ClaudeCodeExecutor" in result.output

    async def test_no_executor_fails_gracefully_quality(self, sample_context):
        result = await QualityEngineerAgent().execute(sample_context)
        assert result.success is False
        assert "No ClaudeCodeExecutor" in result.output

    @pytest.mark.slow
    @pytest.mark.timeout(60)
    async def test_all_agents_real_sdk(self, sample_context):
        """One test, three agents — minimizes SDK calls (~5s each)."""
        for AgentClass in (ProductEngineerAgent, TestRunnerAgent, QualityEngineerAgent):
            agent = AgentClass(executor=_FAST_EXECUTOR)
            result = await agent.execute(sample_context)
            assert isinstance(result, AgentResult), f"{AgentClass.__name__} failed"
            assert len(result.output) > 0, f"{AgentClass.__name__} empty output"


# --- Mock agents still work (regression check) ---


class TestMockAgentsUnchanged:
    async def test_mock_product_engineer(self, sample_context):
        from src.agents.execution.mocks import MockProductEngineerAgent

        agent = MockProductEngineerAgent()
        result = await agent.execute(sample_context)
        assert result.success is True
        assert agent.call_count == 1

    async def test_mock_test_runner(self, sample_context):
        from src.agents.execution.mocks import MockTestRunnerAgent

        agent = MockTestRunnerAgent()
        result = await agent.execute(sample_context)
        assert result.success is True
        assert result.test_results["total"] == 10

    async def test_mock_quality_engineer(self, sample_context):
        from src.agents.execution.mocks import MockQualityEngineerAgent

        agent = MockQualityEngineerAgent()
        result = await agent.execute(sample_context)
        assert result.success is True
        assert result.review_verdict == "approve"
