"""File-based workflow backend using .maestro/ directory structure."""

import asyncio
import json
from dataclasses import asdict
from pathlib import Path

from ..workflow.models import Epic, EpicStatus, ProjectState, Sprint, SprintStatus


class MaestroAdapter:
    """Implements WorkflowBackend using file-based storage.

    Directory layout:
        {project_root}/.maestro/
            state.json
            epics/{epic_id}.md
            sprints/{sprint_id}.md
    """

    def __init__(self, project_root: Path | str):
        self.root = Path(project_root)
        self.state_dir = self.root / ".maestro"
        self.epics_dir = self.state_dir / "epics"
        self.sprints_dir = self.state_dir / "sprints"
        self._state: ProjectState | None = None

    async def _ensure_dirs(self):
        """Create directory structure if it doesn't exist."""
        def _create():
            self.state_dir.mkdir(parents=True, exist_ok=True)
            self.epics_dir.mkdir(exist_ok=True)
            self.sprints_dir.mkdir(exist_ok=True)
        await asyncio.to_thread(_create)

    async def _load_state(self) -> ProjectState:
        """Load state from disk, or create default."""
        if self._state is not None:
            return self._state

        await self._ensure_dirs()
        state_file = self.state_dir / "state.json"

        def _read():
            if state_file.exists():
                data = json.loads(state_file.read_text())
                epics = [
                    Epic(
                        id=e["id"],
                        title=e["title"],
                        description=e["description"],
                        status=EpicStatus(e["status"]),
                        sprint_ids=e.get("sprint_ids", []),
                        metadata=e.get("metadata", {}),
                    )
                    for e in data.get("epics", [])
                ]
                sprints = [
                    Sprint(
                        id=s["id"],
                        goal=s["goal"],
                        status=SprintStatus(s["status"]),
                        epic_id=s["epic_id"],
                        tasks=s.get("tasks", []),
                        dependencies=s.get("dependencies", []),
                        deliverables=s.get("deliverables", []),
                        metadata=s.get("metadata", {}),
                    )
                    for s in data.get("sprints", [])
                ]
                return ProjectState(
                    project_name=data.get("project_name", self.root.name),
                    epics=epics,
                    sprints=sprints,
                    active_sprint_id=data.get("active_sprint_id"),
                    metadata=data.get("metadata", {}),
                )
            return ProjectState(project_name=self.root.name)

        self._state = await asyncio.to_thread(_read)
        return self._state

    async def _save_state(self):
        """Persist state to disk."""
        state = await self._load_state()
        await self._ensure_dirs()
        state_file = self.state_dir / "state.json"

        def _serialize_state(s):
            data = {
                "project_name": s.project_name,
                "active_sprint_id": s.active_sprint_id,
                "metadata": s.metadata,
                "epics": [
                    {**asdict(e), "status": e.status.value} for e in s.epics
                ],
                "sprints": [
                    {**asdict(s), "status": s.status.value} for s in s.sprints
                ],
            }
            return data

        def _write():
            data = _serialize_state(state)
            state_file.write_text(json.dumps(data, indent=2, default=str))

        await asyncio.to_thread(_write)

    async def _write_epic_md(self, epic: Epic):
        """Write epic description as markdown."""
        content = f"""---
id: {epic.id}
title: "{epic.title}"
status: {epic.status.value}
---

# {epic.title}

{epic.description}
"""
        path = self.epics_dir / f"{epic.id}.md"
        await asyncio.to_thread(path.write_text, content)

    async def _write_sprint_md(self, sprint: Sprint):
        """Write sprint spec as markdown."""
        tasks_md = "\n".join(
            f"- {t.get('name', t) if isinstance(t, dict) else t}"
            for t in sprint.tasks
        ) if sprint.tasks else "- (no tasks defined)"

        deps_md = ", ".join(sprint.dependencies) if sprint.dependencies else "none"
        deliverables_md = "\n".join(
            f"- {d}" for d in sprint.deliverables
        ) if sprint.deliverables else "- (no deliverables defined)"

        content = f"""---
id: {sprint.id}
epic_id: {sprint.epic_id}
goal: "{sprint.goal}"
status: {sprint.status.value}
---

# {sprint.goal}

## Tasks
{tasks_md}

## Dependencies
{deps_md}

## Deliverables
{deliverables_md}
"""
        path = self.sprints_dir / f"{sprint.id}.md"
        await asyncio.to_thread(path.write_text, content)

    # --- WorkflowBackend implementation ---

    async def get_project_state(self) -> ProjectState:
        return await self._load_state()

    async def get_epic(self, epic_id: str) -> Epic:
        state = await self._load_state()
        for epic in state.epics:
            if epic.id == epic_id:
                return epic
        raise KeyError(f"Epic not found: {epic_id}")

    async def get_sprint(self, sprint_id: str) -> Sprint:
        state = await self._load_state()
        for sprint in state.sprints:
            if sprint.id == sprint_id:
                return sprint
        raise KeyError(f"Sprint not found: {sprint_id}")

    async def list_epics(self) -> list[Epic]:
        state = await self._load_state()
        return list(state.epics)

    async def list_sprints(self, epic_id: str | None = None) -> list[Sprint]:
        state = await self._load_state()
        sprints = list(state.sprints)
        if epic_id is not None:
            sprints = [s for s in sprints if s.epic_id == epic_id]
        return sprints

    async def create_epic(self, title: str, description: str) -> Epic:
        state = await self._load_state()
        next_num = len(state.epics) + 1
        epic = Epic(
            id=f"e-{next_num}",
            title=title,
            description=description,
            status=EpicStatus.DRAFT,
        )
        state.epics.append(epic)
        await self._save_state()
        await self._write_epic_md(epic)
        return epic

    async def create_sprint(
        self,
        epic_id: str,
        goal: str,
        tasks: list[dict] | None = None,
        dependencies: list[str] | None = None,
        deliverables: list[str] | None = None,
    ) -> Sprint:
        state = await self._load_state()

        # Verify epic exists
        epic = None
        for e in state.epics:
            if e.id == epic_id:
                epic = e
                break
        if epic is None:
            raise KeyError(f"Epic not found: {epic_id}")

        next_num = len(state.sprints) + 1
        sprint = Sprint(
            id=f"s-{next_num}",
            goal=goal,
            status=SprintStatus.TODO,
            epic_id=epic_id,
            tasks=tasks or [],
            dependencies=dependencies or [],
            deliverables=deliverables or [],
        )
        state.sprints.append(sprint)
        epic.sprint_ids.append(sprint.id)
        await self._save_state()
        await self._write_sprint_md(sprint)
        return sprint

    async def update_sprint(self, sprint_id: str, **fields) -> Sprint:
        state = await self._load_state()
        for sprint in state.sprints:
            if sprint.id == sprint_id:
                for key, value in fields.items():
                    if hasattr(sprint, key):
                        setattr(sprint, key, value)
                    else:
                        raise ValueError(f"Unknown sprint field: {key}")
                await self._save_state()
                await self._write_sprint_md(sprint)
                return sprint
        raise KeyError(f"Sprint not found: {sprint_id}")

    async def get_status_summary(self) -> dict:
        state = await self._load_state()
        total = len(state.sprints)
        completed = sum(1 for s in state.sprints if s.status is SprintStatus.DONE)
        in_progress = sum(1 for s in state.sprints if s.status is SprintStatus.IN_PROGRESS)
        blocked = sum(1 for s in state.sprints if s.status is SprintStatus.BLOCKED)
        planned = sum(1 for s in state.sprints if s.status is SprintStatus.TODO)

        return {
            "project_name": state.project_name,
            "total_epics": len(state.epics),
            "total_sprints": total,
            "sprints_done": completed,
            "sprints_in_progress": in_progress,
            "sprints_blocked": blocked,
            "sprints_todo": planned,
            "progress_pct": round(completed / total * 100, 1) if total > 0 else 0.0,
        }
