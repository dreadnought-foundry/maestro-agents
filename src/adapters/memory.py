"""In-memory workflow backend for testing."""

from datetime import datetime

from ..workflow.exceptions import InvalidTransitionError
from ..workflow.models import (
    Epic,
    EpicStatus,
    ProjectState,
    Sprint,
    SprintStatus,
    SprintTransition,
    Step,
    StepStatus,
)
from ..workflow.transitions import validate_transition


class InMemoryAdapter:
    """WorkflowBackend backed by dicts. For tests and demos."""

    def __init__(self, project_name: str = "test-project"):
        self._project_name = project_name
        self._epics: dict[str, Epic] = {}
        self._sprints: dict[str, Sprint] = {}
        self._next_epic_id = 1
        self._next_sprint_id = 1

    async def get_project_state(self) -> ProjectState:
        active = None
        for s in self._sprints.values():
            if s.status is SprintStatus.IN_PROGRESS:
                active = s.id
                break
        return ProjectState(
            project_name=self._project_name,
            epics=list(self._epics.values()),
            sprints=list(self._sprints.values()),
            active_sprint_id=active,
        )

    async def get_epic(self, epic_id: str) -> Epic:
        if epic_id not in self._epics:
            raise KeyError(f"Epic not found: {epic_id}")
        return self._epics[epic_id]

    async def get_sprint(self, sprint_id: str) -> Sprint:
        if sprint_id not in self._sprints:
            raise KeyError(f"Sprint not found: {sprint_id}")
        return self._sprints[sprint_id]

    async def list_epics(self) -> list[Epic]:
        return list(self._epics.values())

    async def list_sprints(self, epic_id: str | None = None) -> list[Sprint]:
        sprints = list(self._sprints.values())
        if epic_id is not None:
            sprints = [s for s in sprints if s.epic_id == epic_id]
        return sprints

    async def create_epic(self, title: str, description: str) -> Epic:
        epic_id = f"e-{self._next_epic_id}"
        self._next_epic_id += 1
        epic = Epic(
            id=epic_id,
            title=title,
            description=description,
            status=EpicStatus.DRAFT,
        )
        self._epics[epic_id] = epic
        return epic

    async def create_sprint(
        self,
        epic_id: str,
        goal: str,
        tasks: list[dict] | None = None,
        dependencies: list[str] | None = None,
        deliverables: list[str] | None = None,
    ) -> Sprint:
        if epic_id not in self._epics:
            raise KeyError(f"Epic not found: {epic_id}")

        sprint_id = f"s-{self._next_sprint_id}"
        self._next_sprint_id += 1
        sprint = Sprint(
            id=sprint_id,
            goal=goal,
            status=SprintStatus.TODO,
            epic_id=epic_id,
            tasks=tasks or [],
            dependencies=dependencies or [],
            deliverables=deliverables or [],
        )
        self._sprints[sprint_id] = sprint
        self._epics[epic_id].sprint_ids.append(sprint_id)
        return sprint

    async def update_sprint(self, sprint_id: str, **fields) -> Sprint:
        if sprint_id not in self._sprints:
            raise KeyError(f"Sprint not found: {sprint_id}")
        sprint = self._sprints[sprint_id]
        for key, value in fields.items():
            if hasattr(sprint, key):
                setattr(sprint, key, value)
            else:
                raise ValueError(f"Unknown sprint field: {key}")
        return sprint

    async def get_status_summary(self) -> dict:
        total_sprints = len(self._sprints)
        completed = sum(1 for s in self._sprints.values() if s.status is SprintStatus.DONE)
        in_progress = sum(1 for s in self._sprints.values() if s.status is SprintStatus.IN_PROGRESS)
        blocked = sum(1 for s in self._sprints.values() if s.status is SprintStatus.BLOCKED)
        planned = sum(1 for s in self._sprints.values() if s.status is SprintStatus.TODO)

        return {
            "project_name": self._project_name,
            "total_epics": len(self._epics),
            "total_sprints": total_sprints,
            "sprints_done": completed,
            "sprints_in_progress": in_progress,
            "sprints_blocked": blocked,
            "sprints_todo": planned,
            "progress_pct": round(completed / total_sprints * 100, 1) if total_sprints > 0 else 0.0,
        }

    async def start_sprint(self, sprint_id: str) -> Sprint:
        sprint = await self.get_sprint(sprint_id)
        validate_transition(sprint_id, sprint.status, SprintStatus.IN_PROGRESS)

        # Auto-create steps from tasks if no steps exist
        if not sprint.steps:
            for i, task in enumerate(sprint.tasks, start=1):
                sprint.steps.append(
                    Step(id=f"step-{i}", name=task["name"])
                )

        # Set sprint status
        sprint.status = SprintStatus.IN_PROGRESS

        # Start the first step
        if sprint.steps:
            sprint.steps[0].status = StepStatus.IN_PROGRESS
            sprint.steps[0].started_at = datetime.now()

        # Record transition
        sprint.transitions.append(
            SprintTransition(
                from_status=SprintStatus.TODO,
                to_status=SprintStatus.IN_PROGRESS,
                timestamp=datetime.now(),
            )
        )
        return sprint

    async def advance_step(self, sprint_id: str, step_output: dict | None = None) -> Sprint:
        sprint = await self.get_sprint(sprint_id)

        # Find current IN_PROGRESS step
        current_idx = None
        for i, step in enumerate(sprint.steps):
            if step.status is StepStatus.IN_PROGRESS:
                current_idx = i
                break

        if current_idx is None:
            raise ValueError(f"No step currently in progress for sprint {sprint_id}")

        # Mark current step DONE
        current_step = sprint.steps[current_idx]
        current_step.status = StepStatus.DONE
        current_step.completed_at = datetime.now()
        if step_output is not None:
            current_step.output = step_output

        # If there's a next step, start it
        next_idx = current_idx + 1
        if next_idx < len(sprint.steps):
            sprint.steps[next_idx].status = StepStatus.IN_PROGRESS
            sprint.steps[next_idx].started_at = datetime.now()

        return sprint

    async def complete_sprint(self, sprint_id: str) -> Sprint:
        sprint = await self.get_sprint(sprint_id)
        previous_status = sprint.status
        validate_transition(sprint_id, sprint.status, SprintStatus.DONE)

        # Verify all steps are done or skipped
        terminal = {StepStatus.DONE, StepStatus.SKIPPED}
        if sprint.steps and not all(s.status in terminal for s in sprint.steps):
            raise ValueError(
                f"Not all steps are done for sprint {sprint_id}"
            )

        sprint.status = SprintStatus.DONE
        sprint.transitions.append(
            SprintTransition(
                from_status=previous_status,
                to_status=SprintStatus.DONE,
                timestamp=datetime.now(),
            )
        )
        return sprint

    async def block_sprint(self, sprint_id: str, reason: str) -> Sprint:
        sprint = await self.get_sprint(sprint_id)
        validate_transition(sprint_id, sprint.status, SprintStatus.BLOCKED)

        sprint.status = SprintStatus.BLOCKED
        sprint.transitions.append(
            SprintTransition(
                from_status=SprintStatus.IN_PROGRESS,
                to_status=SprintStatus.BLOCKED,
                timestamp=datetime.now(),
                reason=reason,
            )
        )
        return sprint

    async def move_to_review(self, sprint_id: str) -> Sprint:
        sprint = await self.get_sprint(sprint_id)
        validate_transition(sprint_id, sprint.status, SprintStatus.REVIEW)

        sprint.status = SprintStatus.REVIEW
        sprint.transitions.append(
            SprintTransition(
                from_status=SprintStatus.IN_PROGRESS,
                to_status=SprintStatus.REVIEW,
                timestamp=datetime.now(),
            )
        )
        return sprint

    async def reject_sprint(self, sprint_id: str, reason: str) -> Sprint:
        sprint = await self.get_sprint(sprint_id)
        validate_transition(sprint_id, sprint.status, SprintStatus.IN_PROGRESS)

        sprint.status = SprintStatus.IN_PROGRESS
        sprint.transitions.append(
            SprintTransition(
                from_status=SprintStatus.REVIEW,
                to_status=SprintStatus.IN_PROGRESS,
                timestamp=datetime.now(),
                reason=reason,
            )
        )
        sprint.metadata["rejection_reason"] = reason
        sprint.metadata.setdefault("rejection_history", []).append({
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        })
        return sprint

    async def get_step_status(self, sprint_id: str) -> dict:
        sprint = await self.get_sprint(sprint_id)

        current_step = None
        for step in sprint.steps:
            if step.status is StepStatus.IN_PROGRESS:
                current_step = step.name
                break

        total = len(sprint.steps)
        completed = sum(1 for s in sprint.steps if s.status is StepStatus.DONE)

        return {
            "current_step": current_step,
            "total_steps": total,
            "completed_steps": completed,
            "progress_pct": round(completed / total * 100, 1) if total > 0 else 0.0,
            "steps": [
                {"id": s.id, "name": s.name, "status": s.status.value}
                for s in sprint.steps
            ],
        }
