"""Mock execution agents for testing."""

from __future__ import annotations

from src.agents.execution.types import AgentResult, StepContext


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
