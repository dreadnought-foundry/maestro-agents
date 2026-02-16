"""Tests for agent execution infrastructure (Sprint 12)."""

from __future__ import annotations

import pytest
from pathlib import Path

from src.workflow.models import (
    Epic,
    EpicStatus,
    Sprint,
    SprintStatus,
    Step,
    StepStatus,
)
from src.agents.execution.types import AgentResult, StepContext
from src.agents.execution.protocol import ExecutionAgent
from src.agents.execution.registry import AgentRegistry


# --- Fixtures ---


@pytest.fixture
def sample_step() -> Step:
    return Step(id="step-1", name="Write tests", status=StepStatus.TODO, agent="coder")


@pytest.fixture
def sample_sprint() -> Sprint:
    return Sprint(
        id="sprint-12",
        goal="Build agent infrastructure",
        status=SprintStatus.IN_PROGRESS,
        epic_id="epic-1",
    )


@pytest.fixture
def sample_epic() -> Epic:
    return Epic(
        id="epic-1",
        title="Agent System",
        description="Build the agent execution system",
        status=EpicStatus.ACTIVE,
    )


@pytest.fixture
def sample_context(sample_step, sample_sprint, sample_epic) -> StepContext:
    return StepContext(
        step=sample_step,
        sprint=sample_sprint,
        epic=sample_epic,
        project_root=Path("/tmp/project"),
    )


# --- AgentResult tests ---


class TestAgentResult:
    def test_construction_required_fields_only(self):
        result = AgentResult(success=True, output="All tests passed")
        assert result.success is True
        assert result.output == "All tests passed"

    def test_construction_all_fields(self):
        result = AgentResult(
            success=True,
            output="Done",
            files_modified=["src/main.py"],
            files_created=["src/new.py"],
            test_results={"passed": 5, "failed": 0},
            coverage=95.5,
            review_verdict="approved",
            deferred_items=["refactor later"],
        )
        assert result.files_modified == ["src/main.py"]
        assert result.files_created == ["src/new.py"]
        assert result.test_results == {"passed": 5, "failed": 0}
        assert result.coverage == 95.5
        assert result.review_verdict == "approved"
        assert result.deferred_items == ["refactor later"]

    def test_defaults_are_correct(self):
        result = AgentResult(success=False, output="Failed")
        assert result.files_modified == []
        assert result.files_created == []
        assert result.test_results is None
        assert result.coverage is None
        assert result.review_verdict is None
        assert result.deferred_items == []

    def test_deferred_items_default_is_independent(self):
        """Each AgentResult instance should have its own deferred_items list."""
        r1 = AgentResult(success=True, output="a")
        r2 = AgentResult(success=True, output="b")
        r1.deferred_items.append("item")
        assert r2.deferred_items == []


# --- StepContext tests ---


class TestStepContext:
    def test_construction_with_all_fields(self, sample_step, sample_sprint, sample_epic):
        prev = [AgentResult(success=True, output="prev")]
        ctx = StepContext(
            step=sample_step,
            sprint=sample_sprint,
            epic=sample_epic,
            project_root=Path("/tmp/project"),
            previous_outputs=prev,
        )
        assert ctx.step is sample_step
        assert ctx.sprint is sample_sprint
        assert ctx.epic is sample_epic
        assert ctx.project_root == Path("/tmp/project")
        assert len(ctx.previous_outputs) == 1

    def test_previous_outputs_defaults_to_empty_list(self, sample_step, sample_sprint, sample_epic):
        ctx = StepContext(
            step=sample_step,
            sprint=sample_sprint,
            epic=sample_epic,
            project_root=Path("/tmp/project"),
        )
        assert ctx.previous_outputs == []


# --- AgentRegistry tests ---


class TestAgentRegistry:
    def _make_mock_agent(self, name: str = "mock", description: str = "A mock agent"):
        """Create a mock agent that satisfies the ExecutionAgent protocol."""

        class MockAgent:
            def __init__(self, name: str, description: str):
                self.name = name
                self.description = description

            async def execute(self, context: StepContext) -> AgentResult:
                return AgentResult(success=True, output=f"{self.name} executed")

        return MockAgent(name=name, description=description)

    def test_register_and_retrieve(self):
        registry = AgentRegistry()
        agent = self._make_mock_agent("coder", "Writes code")
        registry.register("code", agent)
        assert registry.get_agent("code") is agent

    def test_get_unknown_raises_key_error(self):
        registry = AgentRegistry()
        with pytest.raises(KeyError, match="No agent registered for step type: unknown"):
            registry.get_agent("unknown")

    def test_list_agents_returns_copy(self):
        registry = AgentRegistry()
        agent = self._make_mock_agent()
        registry.register("code", agent)
        listing = registry.list_agents()
        listing["test"] = agent  # mutate the copy
        assert "test" not in registry.list_agents()

    def test_register_overwrites_existing(self):
        registry = AgentRegistry()
        agent1 = self._make_mock_agent("v1")
        agent2 = self._make_mock_agent("v2")
        registry.register("code", agent1)
        registry.register("code", agent2)
        assert registry.get_agent("code") is agent2


# --- Protocol compliance test ---


class TestProtocolCompliance:
    def test_mock_agent_satisfies_protocol(self):
        """A class with name, description, and async execute() should work as ExecutionAgent."""

        class MyAgent:
            name = "my-agent"
            description = "Does things"

            async def execute(self, context: StepContext) -> AgentResult:
                return AgentResult(success=True, output="done")

        agent = MyAgent()
        registry = AgentRegistry()
        registry.register("custom", agent)
        assert registry.get_agent("custom") is agent
        assert isinstance(agent, ExecutionAgent)
