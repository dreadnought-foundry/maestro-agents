"""Mock execution agents for testing."""

from __future__ import annotations

from src.agents.execution.types import AgentResult, StepContext
from src.execution.planning_artifacts import PlanningArtifacts


class MockProductEngineerAgent:
    """Mock product engineer for testing. Returns configurable canned results."""

    name: str = "mock_product_engineer"
    description: str = "Mock agent for testing"

    def __init__(self, result: AgentResult | None = None) -> None:
        self._result = result or AgentResult(
            success=True,
            output="Mock implementation complete",
            files_created=["mock_file.py"],
        )
        self.call_count: int = 0
        self.last_context: StepContext | None = None

    async def execute(self, context: StepContext) -> AgentResult:
        self.call_count += 1
        self.last_context = context
        return self._result


class MockPlanningAgent:
    """Mock planning agent for testing. Returns canned planning artifacts."""

    name: str = "mock_planning_agent"
    description: str = "Mock planning agent for testing"

    def __init__(self, artifacts: PlanningArtifacts | None = None) -> None:
        self._artifacts = artifacts or PlanningArtifacts(
            contracts="## Interfaces\n\n- `create_widget(name: str) -> Widget`",
            team_plan="## Agents\n\n1 product engineer, 1 test runner",
            tdd_strategy="## Testing\n\n- Unit tests for all public API\n- 90% coverage target",
            coding_strategy="## Patterns\n\n- Protocol-based interfaces\n- snake_case naming",
            context_brief="## Context\n\n- Standard Python project with pytest",
        )
        self.call_count: int = 0
        self.last_context: StepContext | None = None

    async def execute(self, context: StepContext) -> AgentResult:
        self.call_count += 1
        self.last_context = context

        output = (
            f"### CONTRACTS\n{self._artifacts.contracts}\n\n"
            f"### TEAM_PLAN\n{self._artifacts.team_plan}\n\n"
            f"### TDD_STRATEGY\n{self._artifacts.tdd_strategy}\n\n"
            f"### CODING_STRATEGY\n{self._artifacts.coding_strategy}\n\n"
            f"### CONTEXT_BRIEF\n{self._artifacts.context_brief}"
        )

        return AgentResult(
            success=True,
            output=output,
            files_created=[
                "_planning_contracts.md",
                "_planning_team_plan.md",
                "_planning_tdd_strategy.md",
                "_planning_coding_strategy.md",
                "_planning_context_brief.md",
            ],
        )


class MockQualityEngineerAgent:
    """Mock quality engineer for testing. Returns configurable review verdict."""

    name: str = "mock_quality_engineer"
    description: str = "Mock quality engineer agent for testing"

    def __init__(self, result: AgentResult | None = None) -> None:
        self._result = result or AgentResult(
            success=True,
            output="Code review passed. All acceptance criteria met.",
            review_verdict="approve",
        )
        self.call_count: int = 0
        self.last_context: StepContext | None = None

    async def execute(self, context: StepContext) -> AgentResult:
        self.call_count += 1
        self.last_context = context
        return self._result


class MockTestRunnerAgent:
    """Mock test runner for testing. Returns configurable test results."""

    name: str = "mock_test_runner"
    description: str = "Mock test runner agent for testing"

    def __init__(self, result: AgentResult | None = None) -> None:
        self._result = result or AgentResult(
            success=True,
            output="All tests passed",
            test_results={
                "total": 10,
                "passed": 10,
                "failed": 0,
                "errors": 0,
                "failed_tests": [],
            },
            coverage=95.0,
        )
        self.call_count: int = 0
        self.last_context: StepContext | None = None

    async def execute(self, context: StepContext) -> AgentResult:
        self.call_count += 1
        self.last_context = context
        return self._result
