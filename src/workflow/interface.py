"""Abstract workflow backend protocol."""

from typing import Protocol

from .models import Epic, ProjectState, Sprint


class WorkflowBackend(Protocol):
    """Interface that any workflow backend must implement.

    Covers plan/manage operations and sprint execution lifecycle.
    """

    async def get_project_state(self) -> ProjectState: ...

    async def get_epic(self, epic_id: str) -> Epic: ...

    async def get_sprint(self, sprint_id: str) -> Sprint: ...

    async def list_epics(self) -> list[Epic]: ...

    async def list_sprints(self, epic_id: str | None = None) -> list[Sprint]: ...

    async def create_epic(self, title: str, description: str) -> Epic: ...

    async def create_sprint(
        self,
        epic_id: str,
        goal: str,
        tasks: list[dict] | None = None,
        dependencies: list[str] | None = None,
        deliverables: list[str] | None = None,
    ) -> Sprint: ...

    async def update_sprint(self, sprint_id: str, **fields) -> Sprint: ...

    async def get_status_summary(self) -> dict: ...

    # Sprint execution lifecycle methods

    async def start_sprint(self, sprint_id: str) -> Sprint: ...

    async def advance_step(
        self, sprint_id: str, step_output: dict | None = None
    ) -> Sprint: ...

    async def complete_sprint(self, sprint_id: str) -> Sprint: ...

    async def block_sprint(self, sprint_id: str, reason: str) -> Sprint: ...

    async def get_step_status(self, sprint_id: str) -> dict: ...
