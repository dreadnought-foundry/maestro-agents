"""Registry for mapping step types to execution agents."""

from __future__ import annotations

from src.agents.execution.protocol import ExecutionAgent


class AgentRegistry:
    """Maps step types to execution agents."""

    def __init__(self) -> None:
        self._agents: dict[str, ExecutionAgent] = {}

    def register(self, step_type: str, agent: ExecutionAgent) -> None:
        self._agents[step_type] = agent

    def get_agent(self, step_type: str) -> ExecutionAgent:
        if step_type not in self._agents:
            raise KeyError(f"No agent registered for step type: {step_type}")
        return self._agents[step_type]

    def list_agents(self) -> dict[str, ExecutionAgent]:
        return dict(self._agents)
