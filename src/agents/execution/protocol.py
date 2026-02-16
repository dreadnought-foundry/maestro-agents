"""Protocol definition for execution agents."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.agents.execution.types import AgentResult, StepContext


@runtime_checkable
class ExecutionAgent(Protocol):
    name: str
    description: str

    async def execute(self, context: StepContext) -> AgentResult: ...
