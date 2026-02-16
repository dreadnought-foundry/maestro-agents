"""Data types for agent execution infrastructure."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from src.workflow.models import Epic, Sprint, Step


@dataclass
class AgentResult:
    success: bool
    output: str
    files_modified: list[str] = field(default_factory=list)
    files_created: list[str] = field(default_factory=list)
    test_results: dict | None = None
    coverage: float | None = None
    review_verdict: str | None = None
    deferred_items: list[str] = field(default_factory=list)


@dataclass
class StepContext:
    step: Step
    sprint: Sprint
    epic: Epic
    project_root: Path
    previous_outputs: list[AgentResult] = field(default_factory=list)
    cumulative_deferred: str | None = None
    cumulative_postmortem: str | None = None
