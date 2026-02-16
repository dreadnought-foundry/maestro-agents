"""Kanban board data models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SprintEntry:
    number: int
    title: str
    status: str
    sprint_type: str | None = None
    epic: int | None = None
    created: str | None = None
    started: str | None = None
    completed: str | None = None
    hours: float | None = None
    path: str = ""


@dataclass
class EpicEntry:
    number: int
    title: str
    status: str
    created: str | None = None
    started: str | None = None
    completed: str | None = None
    total_sprints: int = 0
    completed_sprints: int = 0
    sprint_numbers: list[int] = field(default_factory=list)
    path: str = ""


@dataclass
class BoardState:
    epics: dict[int, EpicEntry] = field(default_factory=dict)
    sprints: dict[int, SprintEntry] = field(default_factory=dict)
    next_epic: int = 1
    next_sprint: int = 1
