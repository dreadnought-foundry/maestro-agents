"""Core sprint runner — orchestrates end-to-end sprint execution."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from src.agents.execution.registry import AgentRegistry
from src.agents.execution.types import AgentResult, StepContext
from src.workflow.models import StepStatus


@dataclass
class RunResult:
    sprint_id: str
    success: bool
    steps_completed: int
    steps_total: int
    agent_results: list[AgentResult] = field(default_factory=list)
    deferred_items: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0


class SprintRunner:
    """Orchestrates end-to-end sprint execution."""

    def __init__(
        self,
        backend,
        agent_registry: AgentRegistry,
        project_root: Path | None = None,
    ):
        self._backend = backend
        self._registry = agent_registry
        self._project_root = project_root or Path(".")

    async def run(
        self,
        sprint_id: str,
        on_progress: Callable | None = None,
    ) -> RunResult:
        """Run a sprint from start to completion."""
        start_time = time.monotonic()
        agent_results: list[AgentResult] = []
        deferred_items: list[str] = []

        # Start the sprint (validates TODO -> IN_PROGRESS, creates steps)
        sprint = await self._backend.start_sprint(sprint_id)
        epic = await self._backend.get_epic(sprint.epic_id)

        # Iterate through steps
        while True:
            status = await self._backend.get_step_status(sprint_id)
            current_step_name = status["current_step"]

            if current_step_name is None:
                # No more steps in progress — all done or none left
                break

            # Find the current IN_PROGRESS step
            sprint = await self._backend.get_sprint(sprint_id)
            current_step = None
            for step in sprint.steps:
                if step.status is StepStatus.IN_PROGRESS:
                    current_step = step
                    break

            if current_step is None:
                break

            # Determine the step type for agent dispatch
            # Use step metadata "type" if set, otherwise use step name
            step_type = current_step.metadata.get("type", current_step.name)

            # Get the agent for this step type
            agent = self._registry.get_agent(step_type)

            # Build context
            context = StepContext(
                step=current_step,
                sprint=sprint,
                epic=epic,
                project_root=self._project_root,
                previous_outputs=list(agent_results),
            )

            # Execute the agent
            result = await agent.execute(context)
            agent_results.append(result)

            # Collect deferred items
            deferred_items.extend(result.deferred_items)

            # If agent failed, block the sprint
            if not result.success:
                await self._backend.block_sprint(
                    sprint_id, f"Step '{current_step.name}' failed: {result.output}"
                )
                elapsed = time.monotonic() - start_time
                step_status = await self._backend.get_step_status(sprint_id)
                return RunResult(
                    sprint_id=sprint_id,
                    success=False,
                    steps_completed=step_status["completed_steps"],
                    steps_total=step_status["total_steps"],
                    agent_results=agent_results,
                    deferred_items=deferred_items,
                    duration_seconds=elapsed,
                )

            # Advance to next step
            await self._backend.advance_step(sprint_id, {"output": result.output})

            # Fire progress callback
            if on_progress:
                step_status = await self._backend.get_step_status(sprint_id)
                on_progress(step_status)

        # Complete the sprint
        await self._backend.complete_sprint(sprint_id)
        elapsed = time.monotonic() - start_time
        step_status = await self._backend.get_step_status(sprint_id)

        return RunResult(
            sprint_id=sprint_id,
            success=True,
            steps_completed=step_status["completed_steps"],
            steps_total=step_status["total_steps"],
            agent_results=agent_results,
            deferred_items=deferred_items,
            duration_seconds=elapsed,
        )
