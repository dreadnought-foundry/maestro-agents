"""Tests for ClaudeCodeExecutor and agent wiring (Sprint 25).

These tests use the real claude-agent-sdk — no mocking of the SDK.
The SDK invokes the claude CLI, which is free (no API costs).
Only the timeout test mocks query() since we can't force a real timeout reliably.
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


# --- Fixtures ---


@pytest.fixture
def executor():
    return ClaudeCodeExecutor(model="sonnet", max_turns=3)


@pytest.fixture
def working_dir(tmp_path):
    return tmp_path


@pytest.fixture
def sample_context(tmp_path):
    return StepContext(
        step=Step(id="step-1", name="Implement feature", status=StepStatus.TODO, agent="coder"),
        sprint=Sprint(
            id="sprint-25",
            goal="Build Claude Code executor",
            status=SprintStatus.IN_PROGRESS,
            epic_id="epic-7",
        ),
        epic=Epic(
            id="epic-7",
            title="Production Integration",
            description="Wire real Claude Code execution",
            status=EpicStatus.ACTIVE,
        ),
        project_root=tmp_path,
    )


# --- ClaudeCodeExecutor tests (real SDK) ---


class TestClaudeCodeExecutor:
    @pytest.mark.asyncio
    async def test_simple_prompt(self, executor, working_dir):
        """Run a real prompt through the SDK and verify we get output."""
        result = await executor.run(
            "Respond with exactly: HELLO_TEST_PASS",
            working_dir,
            allowed_tools=[],
        )
        assert result.success is True
        assert "HELLO_TEST_PASS" in result.output

    @pytest.mark.asyncio
    async def test_returns_agent_result(self, executor, working_dir):
        """Verify the return type is a proper AgentResult."""
        result = await executor.run(
            "Say OK",
            working_dir,
            allowed_tools=[],
        )
        assert isinstance(result, AgentResult)
        assert isinstance(result.output, str)
        assert isinstance(result.files_created, list)
        assert isinstance(result.files_modified, list)

    @pytest.mark.asyncio
    async def test_file_write_tracked(self, executor, working_dir):
        """Ask the SDK to write a file and verify it's tracked."""
        result = await executor.run(
            f"Create a file at {working_dir}/hello.txt containing 'hello world'. "
            "Do not explain, just create the file.",
            working_dir,
            allowed_tools=["Write"],
        )
        assert result.success is True
        assert (working_dir / "hello.txt").exists()
        assert any("hello.txt" in f for f in result.files_created)

    @pytest.mark.asyncio
    async def test_timeout_handling(self, executor, working_dir):
        """Timeout produces a failed AgentResult."""
        # This is the one test where we mock — can't reliably force a real timeout
        async def _hang(*, prompt, options):
            import asyncio
            await asyncio.sleep(999)
            yield  # pragma: no cover

        with patch("src.agents.execution.claude_code.query", _hang):
            result = await executor.run("hang", working_dir, timeout=1)

        assert result.success is False
        assert "timed out" in result.output

    @pytest.mark.asyncio
    async def test_no_output_gives_placeholder(self, executor, working_dir):
        """If the SDK returns empty text, we get a placeholder."""
        result = await executor.run(
            "Respond with nothing. Do not output any text at all. Be completely silent.",
            working_dir,
            allowed_tools=[],
            timeout=30,
        )
        # Either we get some output or the placeholder
        assert isinstance(result.output, str)
        assert len(result.output) > 0


# --- Agent wiring tests (real SDK) ---


class TestProductEngineerAgent:
    @pytest.mark.asyncio
    async def test_no_executor_fails_gracefully(self, sample_context):
        """Without an executor, agent returns a failed result (not a crash)."""
        agent = ProductEngineerAgent()
        result = await agent.execute(sample_context)
        assert result.success is False
        assert "No ClaudeCodeExecutor" in result.output

    @pytest.mark.asyncio
    async def test_executes_with_real_sdk(self, sample_context):
        """Run the real agent through the real SDK."""
        executor = ClaudeCodeExecutor(model="sonnet", max_turns=2)
        agent = ProductEngineerAgent(executor=executor)
        result = await agent.execute(sample_context)

        assert isinstance(result, AgentResult)
        assert isinstance(result.output, str)
        assert len(result.output) > 0


class TestTestRunnerAgent:
    @pytest.mark.asyncio
    async def test_no_executor_fails_gracefully(self, sample_context):
        agent = TestRunnerAgent()
        result = await agent.execute(sample_context)
        assert result.success is False
        assert "No ClaudeCodeExecutor" in result.output

    @pytest.mark.asyncio
    async def test_executes_with_real_sdk(self, sample_context):
        """Run the real test runner agent through the SDK."""
        executor = ClaudeCodeExecutor(model="sonnet", max_turns=2)
        agent = TestRunnerAgent(executor=executor)
        result = await agent.execute(sample_context)

        assert isinstance(result, AgentResult)
        assert isinstance(result.output, str)
        assert len(result.output) > 0


class TestQualityEngineerAgent:
    @pytest.mark.asyncio
    async def test_no_executor_fails_gracefully(self, sample_context):
        agent = QualityEngineerAgent()
        result = await agent.execute(sample_context)
        assert result.success is False
        assert "No ClaudeCodeExecutor" in result.output

    @pytest.mark.asyncio
    async def test_executes_with_real_sdk(self, sample_context):
        """Run the real quality engineer agent through the SDK."""
        executor = ClaudeCodeExecutor(model="sonnet", max_turns=2)
        agent = QualityEngineerAgent(executor=executor)
        result = await agent.execute(sample_context)

        assert isinstance(result, AgentResult)
        assert isinstance(result.output, str)
        assert len(result.output) > 0


# --- Mock agents still work (regression check) ---


class TestMockAgentsUnchanged:
    @pytest.mark.asyncio
    async def test_mock_product_engineer(self, sample_context):
        from src.agents.execution.mocks import MockProductEngineerAgent

        agent = MockProductEngineerAgent()
        result = await agent.execute(sample_context)
        assert result.success is True
        assert agent.call_count == 1

    @pytest.mark.asyncio
    async def test_mock_test_runner(self, sample_context):
        from src.agents.execution.mocks import MockTestRunnerAgent

        agent = MockTestRunnerAgent()
        result = await agent.execute(sample_context)
        assert result.success is True
        assert result.test_results["total"] == 10

    @pytest.mark.asyncio
    async def test_mock_quality_engineer(self, sample_context):
        from src.agents.execution.mocks import MockQualityEngineerAgent

        agent = MockQualityEngineerAgent()
        result = await agent.execute(sample_context)
        assert result.success is True
        assert result.review_verdict == "approve"
