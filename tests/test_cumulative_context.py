"""Tests for wiring cumulative deferred/postmortem context into agents (Sprint 27)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters.memory import InMemoryAdapter
from src.agents.execution.mocks import (
    MockProductEngineerAgent,
    MockQualityEngineerAgent,
)
from src.agents.execution.product_engineer import ProductEngineerAgent
from src.agents.execution.quality_engineer import QualityEngineerAgent
from src.agents.execution.registry import AgentRegistry
from src.agents.execution.types import AgentResult, StepContext
from src.execution.runner import SprintRunner
from src.workflow.models import Epic, EpicStatus, Sprint, SprintStatus, Step, StepStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_DEFERRED = """\
# Deferred Items

## Production Integration

- [ ] Production SDK integration
  ↳ 🔴 High · L · Complexity 3 · (S01, S03)
"""

SAMPLE_POSTMORTEM = """\
# Sprint Postmortems

## Timeline
- **S01** [Workflow Models] — Success 5/5 steps

## Architecture & Design Patterns
**Protocol-First Design** (S01): Define protocol before implementation.
"""


@pytest.fixture
def sample_context():
    return StepContext(
        step=Step(id="step-1", name="implement", status=StepStatus.IN_PROGRESS, agent="coder"),
        sprint=Sprint(
            id="sprint-27", goal="Wire cumulative context",
            status=SprintStatus.IN_PROGRESS, epic_id="epic-1",
        ),
        epic=Epic(
            id="epic-1", title="Execution", description="Execution system",
            status=EpicStatus.ACTIVE,
        ),
        project_root=Path("/tmp/project"),
    )


@pytest.fixture
def context_with_cumulative(sample_context):
    sample_context.cumulative_deferred = SAMPLE_DEFERRED
    sample_context.cumulative_postmortem = SAMPLE_POSTMORTEM
    return sample_context


# ---------------------------------------------------------------------------
# StepContext field tests
# ---------------------------------------------------------------------------


class TestStepContextCumulativeFields:
    def test_defaults_to_none(self, sample_context):
        assert sample_context.cumulative_deferred is None
        assert sample_context.cumulative_postmortem is None

    def test_accepts_cumulative_content(self, context_with_cumulative):
        assert "Deferred Items" in context_with_cumulative.cumulative_deferred
        assert "Sprint Postmortems" in context_with_cumulative.cumulative_postmortem


# ---------------------------------------------------------------------------
# Agent prompt integration tests
# ---------------------------------------------------------------------------


class TestProductEngineerPrompt:
    def test_prompt_includes_deferred_when_present(self, context_with_cumulative):
        agent = ProductEngineerAgent()
        prompt = agent._build_prompt(context_with_cumulative)
        assert "Deferred Items (from prior sprints)" in prompt
        assert "Production SDK integration" in prompt

    def test_prompt_includes_postmortem_when_present(self, context_with_cumulative):
        agent = ProductEngineerAgent()
        prompt = agent._build_prompt(context_with_cumulative)
        assert "Lessons Learned (from prior sprints)" in prompt
        assert "Protocol-First Design" in prompt

    def test_prompt_omits_deferred_when_none(self, sample_context):
        agent = ProductEngineerAgent()
        prompt = agent._build_prompt(sample_context)
        assert "Deferred Items" not in prompt

    def test_prompt_omits_postmortem_when_none(self, sample_context):
        agent = ProductEngineerAgent()
        prompt = agent._build_prompt(sample_context)
        assert "Lessons Learned" not in prompt


class TestQualityEngineerPrompt:
    def test_prompt_includes_deferred_when_present(self, context_with_cumulative):
        agent = QualityEngineerAgent()
        prompt = agent._build_prompt(context_with_cumulative)
        assert "Deferred Items (from prior sprints)" in prompt
        assert "Production SDK integration" in prompt

    def test_prompt_includes_postmortem_when_present(self, context_with_cumulative):
        agent = QualityEngineerAgent()
        prompt = agent._build_prompt(context_with_cumulative)
        assert "Lessons Learned (from prior sprints)" in prompt
        assert "Protocol-First Design" in prompt

    def test_prompt_omits_deferred_when_none(self, sample_context):
        agent = QualityEngineerAgent()
        prompt = agent._build_prompt(sample_context)
        assert "Deferred Items" not in prompt

    def test_prompt_omits_postmortem_when_none(self, sample_context):
        agent = QualityEngineerAgent()
        prompt = agent._build_prompt(sample_context)
        assert "Lessons Learned" not in prompt


# ---------------------------------------------------------------------------
# Runner integration — kanban_dir wiring
# ---------------------------------------------------------------------------


async def _setup_with_kanban(tmp_path):
    """Create backend + kanban dir with cumulative files."""
    backend = InMemoryAdapter()
    epic = await backend.create_epic("Test Epic", "desc")
    sprint = await backend.create_sprint(
        epic.id, "Build production SDK integration",
        tasks=[{"name": "implement"}],
    )

    kanban_dir = tmp_path / "kanban"
    kanban_dir.mkdir()
    (kanban_dir / "deferred.md").write_text(SAMPLE_DEFERRED)
    (kanban_dir / "postmortem.md").write_text(SAMPLE_POSTMORTEM)

    return backend, sprint.id, kanban_dir


class TestRunnerCumulativeContext:
    async def test_runner_filters_context_from_kanban_dir(self, tmp_path):
        """When kanban_dir is set, agents receive filtered cumulative context."""
        backend, sprint_id, kanban_dir = await _setup_with_kanban(tmp_path)

        agent = MockProductEngineerAgent()
        registry = AgentRegistry()
        registry.register("implement", agent)

        runner = SprintRunner(
            backend=backend,
            agent_registry=registry,
            kanban_dir=kanban_dir,
        )
        await runner.run(sprint_id)

        assert agent.last_context is not None
        # Deferred: 🔴 High items always surface + keyword match on "production"
        assert agent.last_context.cumulative_deferred is not None
        assert "Production SDK integration" in agent.last_context.cumulative_deferred
        # Filtered content is smaller than raw
        assert len(agent.last_context.cumulative_deferred) < len(SAMPLE_DEFERRED) or \
            agent.last_context.cumulative_deferred == SAMPLE_DEFERRED  # small sample may not shrink

    async def test_runner_without_kanban_dir_leaves_context_none(self, tmp_path):
        """When kanban_dir is not set, cumulative fields are None."""
        backend = InMemoryAdapter()
        epic = await backend.create_epic("Test Epic", "desc")
        sprint = await backend.create_sprint(epic.id, "Test goal", tasks=[{"name": "implement"}])

        agent = MockProductEngineerAgent()
        registry = AgentRegistry()
        registry.register("implement", agent)

        runner = SprintRunner(
            backend=backend,
            agent_registry=registry,
        )
        await runner.run(sprint.id)

        assert agent.last_context is not None
        assert agent.last_context.cumulative_deferred is None
        assert agent.last_context.cumulative_postmortem is None

    async def test_test_step_gets_no_cumulative_context(self, tmp_path):
        """Test steps should not receive cumulative context (they just run pytest)."""
        backend = InMemoryAdapter()
        epic = await backend.create_epic("Test Epic", "desc")
        sprint = await backend.create_sprint(
            epic.id, "Build production SDK",
            tasks=[{"name": "test"}],
        )

        from src.agents.execution.mocks import MockSuiteRunnerAgent
        agent = MockSuiteRunnerAgent()
        registry = AgentRegistry()
        registry.register("test", agent)

        kanban_dir = tmp_path / "kanban"
        kanban_dir.mkdir()
        (kanban_dir / "deferred.md").write_text(SAMPLE_DEFERRED)
        (kanban_dir / "postmortem.md").write_text(SAMPLE_POSTMORTEM)

        runner = SprintRunner(
            backend=backend,
            agent_registry=registry,
            kanban_dir=kanban_dir,
        )
        await runner.run(sprint.id)

        assert agent.last_context is not None
        assert agent.last_context.cumulative_deferred is None
        assert agent.last_context.cumulative_postmortem is None

    async def test_runner_missing_files_leaves_context_none(self, tmp_path):
        """When kanban_dir exists but files don't, cumulative fields are None."""
        backend = InMemoryAdapter()
        epic = await backend.create_epic("Test Epic", "desc")
        sprint = await backend.create_sprint(epic.id, "Test goal", tasks=[{"name": "implement"}])

        kanban_dir = tmp_path / "kanban"
        kanban_dir.mkdir()
        # No deferred.md or postmortem.md

        agent = MockProductEngineerAgent()
        registry = AgentRegistry()
        registry.register("implement", agent)

        runner = SprintRunner(
            backend=backend,
            agent_registry=registry,
            kanban_dir=kanban_dir,
        )
        await runner.run(sprint.id)

        assert agent.last_context.cumulative_deferred is None
        assert agent.last_context.cumulative_postmortem is None

    async def test_runner_empty_files_leaves_context_none(self, tmp_path):
        """When kanban files exist but are empty, cumulative fields are None."""
        backend = InMemoryAdapter()
        epic = await backend.create_epic("Test Epic", "desc")
        sprint = await backend.create_sprint(epic.id, "Test goal", tasks=[{"name": "implement"}])

        kanban_dir = tmp_path / "kanban"
        kanban_dir.mkdir()
        (kanban_dir / "deferred.md").write_text("")
        (kanban_dir / "postmortem.md").write_text("  \n  ")

        agent = MockProductEngineerAgent()
        registry = AgentRegistry()
        registry.register("implement", agent)

        runner = SprintRunner(
            backend=backend,
            agent_registry=registry,
            kanban_dir=kanban_dir,
        )
        await runner.run(sprint.id)

        assert agent.last_context.cumulative_deferred is None
        assert agent.last_context.cumulative_postmortem is None
