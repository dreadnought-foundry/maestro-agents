"""Resume and cancel logic for sprint execution."""

from __future__ import annotations

from src.agents.execution.registry import AgentRegistry
from src.agents.execution.types import AgentResult, StepContext
from src.workflow.models import SprintStatus, StepStatus

from .runner import RunResult


async def find_resume_point(sprint_id: str, backend) -> int:
    """Find the index of the first non-completed step.

    Returns the index into sprint.steps of the step to resume from.
    If all steps are done, returns len(steps).
    """
    sprint = await backend.get_sprint(sprint_id)
    for i, step in enumerate(sprint.steps):
        if step.status not in (StepStatus.DONE, StepStatus.SKIPPED):
            return i
    return len(sprint.steps)


async def resume_sprint(
    sprint_id: str,
    backend,
    agent_registry: AgentRegistry,
    project_root=None,
    on_progress=None,
) -> RunResult:
    """Resume a BLOCKED sprint from the last incomplete step.

    1. Validates sprint is BLOCKED
    2. Transitions BLOCKED -> IN_PROGRESS
    3. Finds first non-completed step
    4. Sets that step to IN_PROGRESS
    5. Continues execution like normal run
    """
    import time
    from pathlib import Path

    start_time = time.monotonic()
    project_root = project_root or Path(".")

    sprint = await backend.get_sprint(sprint_id)
    if sprint.status is not SprintStatus.BLOCKED:
        raise ValueError(
            f"Cannot resume sprint {sprint_id}: status is {sprint.status.value}, expected blocked"
        )

    # Transition BLOCKED -> IN_PROGRESS
    await backend.update_sprint(sprint_id, status=SprintStatus.IN_PROGRESS)

    # Find resume point
    resume_idx = await find_resume_point(sprint_id, backend)
    sprint = await backend.get_sprint(sprint_id)
    epic = await backend.get_epic(sprint.epic_id)

    # Set the resume step to IN_PROGRESS
    if resume_idx < len(sprint.steps):
        sprint.steps[resume_idx].status = StepStatus.IN_PROGRESS

    # Collect previous results from already-completed steps
    agent_results: list[AgentResult] = []
    deferred_items: list[str] = []

    # Execute remaining steps
    for i in range(resume_idx, len(sprint.steps)):
        step = sprint.steps[i]
        step_type = step.metadata.get("type", step.name)
        agent = agent_registry.get_agent(step_type)

        context = StepContext(
            step=step,
            sprint=sprint,
            epic=epic,
            project_root=project_root,
            previous_outputs=list(agent_results),
        )

        result = await agent.execute(context)
        agent_results.append(result)
        deferred_items.extend(result.deferred_items)

        if not result.success:
            await backend.block_sprint(
                sprint_id, f"Step '{step.name}' failed: {result.output}"
            )
            elapsed = time.monotonic() - start_time
            step_status = await backend.get_step_status(sprint_id)
            return RunResult(
                sprint_id=sprint_id,
                success=False,
                steps_completed=step_status["completed_steps"],
                steps_total=step_status["total_steps"],
                agent_results=agent_results,
                deferred_items=deferred_items,
                duration_seconds=elapsed,
            )

        await backend.advance_step(sprint_id, {"output": result.output})

        if on_progress:
            step_status = await backend.get_step_status(sprint_id)
            on_progress(step_status)

    await backend.complete_sprint(sprint_id)
    elapsed = time.monotonic() - start_time
    step_status = await backend.get_step_status(sprint_id)

    return RunResult(
        sprint_id=sprint_id,
        success=True,
        steps_completed=step_status["completed_steps"],
        steps_total=step_status["total_steps"],
        agent_results=agent_results,
        deferred_items=deferred_items,
        duration_seconds=elapsed,
    )


async def cancel_sprint(sprint_id: str, reason: str, backend) -> None:
    """Cancel a sprint -- block it with a reason."""
    sprint = await backend.get_sprint(sprint_id)
    if sprint.status is SprintStatus.IN_PROGRESS:
        await backend.block_sprint(sprint_id, reason)
    elif sprint.status is SprintStatus.TODO:
        # Can't block a TODO sprint, so just update metadata
        await backend.update_sprint(sprint_id, status=SprintStatus.ABANDONED)
    else:
        raise ValueError(
            f"Cannot cancel sprint {sprint_id}: status is {sprint.status.value}"
        )


async def retry_step(
    sprint_id: str,
    backend,
    agent_registry: AgentRegistry,
    max_retries: int = 2,
    project_root=None,
) -> AgentResult:
    """Retry the current failed/blocked step up to max_retries times.

    Returns the final AgentResult (success or last failure).
    """
    from pathlib import Path

    project_root = project_root or Path(".")
    sprint = await backend.get_sprint(sprint_id)
    epic = await backend.get_epic(sprint.epic_id)

    # Find the step to retry (first non-DONE, non-SKIPPED)
    current_step = None
    for step in sprint.steps:
        if step.status not in (StepStatus.DONE, StepStatus.SKIPPED):
            current_step = step
            break

    if current_step is None:
        raise ValueError(f"No step to retry in sprint {sprint_id}")

    step_type = current_step.metadata.get("type", current_step.name)
    agent = agent_registry.get_agent(step_type)

    last_result = None
    for attempt in range(max_retries + 1):
        context = StepContext(
            step=current_step,
            sprint=sprint,
            epic=epic,
            project_root=project_root,
        )
        last_result = await agent.execute(context)
        if last_result.success:
            return last_result

    return last_result
