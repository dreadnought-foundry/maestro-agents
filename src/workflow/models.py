"""Domain models for the workflow system."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SprintStatus(Enum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    BLOCKED = "blocked"
    ABANDONED = "abandoned"
    ARCHIVED = "archived"


class StepStatus(Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"
    FAILED = "failed"
    SKIPPED = "skipped"


class EpicStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"


@dataclass
class Step:
    id: str
    name: str
    status: StepStatus = StepStatus.TODO
    agent: str | None = None
    output: dict | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    depends_on: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class SprintTransition:
    from_status: SprintStatus
    to_status: SprintStatus
    timestamp: datetime
    reason: str | None = None


@dataclass
class Sprint:
    id: str
    goal: str
    status: SprintStatus
    epic_id: str
    tasks: list[dict] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    deliverables: list[str] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    transitions: list[SprintTransition] = field(default_factory=list)
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
