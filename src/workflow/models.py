"""Domain models for the workflow system."""

from dataclasses import dataclass, field
from enum import Enum


class SprintStatus(Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    ABANDONED = "abandoned"


class EpicStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"


@dataclass
class Sprint:
    id: str
    goal: str
    status: SprintStatus
    epic_id: str
    tasks: list[dict] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    deliverables: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class Epic:
    id: str
    title: str
    description: str
    status: EpicStatus
    sprint_ids: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class ProjectState:
    project_name: str
    epics: list[Epic] = field(default_factory=list)
    sprints: list[Sprint] = field(default_factory=list)
    active_sprint_id: str | None = None
    metadata: dict = field(default_factory=dict)
