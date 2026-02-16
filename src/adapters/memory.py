"""In-memory workflow backend for testing."""

from ..workflow.models import Epic, EpicStatus, ProjectState, Sprint, SprintStatus


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
