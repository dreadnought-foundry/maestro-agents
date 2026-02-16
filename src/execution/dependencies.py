"""Dependency validation for sprint execution."""

from __future__ import annotations

from ..workflow.exceptions import DependencyNotMetError
from ..workflow.models import Sprint, SprintStatus, Step, StepStatus


async def check_sprint_dependencies(sprint_id: str, backend) -> list[str]:
    """Check if all sprint dependencies are met (DONE status).

    Returns list of unmet dependency sprint IDs. Empty list means all met.
    """
    sprint = await backend.get_sprint(sprint_id)
    if not sprint.dependencies:
        return []

    unmet = []
    for dep_id in sprint.dependencies:
        dep_sprint = await backend.get_sprint(dep_id)
        if dep_sprint.status is not SprintStatus.DONE:
            unmet.append(dep_id)
    return unmet


async def validate_sprint_dependencies(sprint_id: str, backend) -> None:
    """Validate all dependencies are met. Raises DependencyNotMetError if not."""
    unmet = await check_sprint_dependencies(sprint_id, backend)
    if unmet:
        raise DependencyNotMetError(sprint_id, unmet)


def validate_step_order(sprint: Sprint, current_step: Step) -> bool:
    """Validate that a step can execute given completed steps.

    A step can execute if all steps before it in the list are DONE or SKIPPED.
    """
    for step in sprint.steps:
        if step.id == current_step.id:
            return True  # All preceding steps are done
        if step.status not in (StepStatus.DONE, StepStatus.SKIPPED):
            return False  # A preceding step isn't done
    return False  # Step not found in sprint
