"""Planning artifacts — structured output from the PLAN phase.

PlanningArtifacts contains 5 markdown documents that guide execution agents:
contracts, team_plan, tdd_strategy, coding_strategy, and context_brief.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ARTIFACT_NAMES = [
    "contracts",
    "team_plan",
    "tdd_strategy",
    "coding_strategy",
    "context_brief",
]


@dataclass
class PlanningArtifacts:
    """Structured planning output that guides execution agents."""

    contracts: str = ""
    team_plan: str = ""
    tdd_strategy: str = ""
    coding_strategy: str = ""
    context_brief: str = ""

    def is_complete(self) -> bool:
        """Check that all artifacts have non-empty content."""
        return all(
            getattr(self, name).strip()
            for name in ARTIFACT_NAMES
        )

    def missing(self) -> list[str]:
        """Return names of empty/missing artifacts."""
        return [
            name for name in ARTIFACT_NAMES
            if not getattr(self, name).strip()
        ]

    def write_to_dir(self, sprint_dir: Path, sprint_prefix: str | None = None) -> list[Path]:
        """Write each artifact as a markdown file in the sprint directory.

        If *sprint_prefix* is given (e.g. ``"sprint-37"``), files are named
        ``sprint-37_planning_contracts.md``.  Without a prefix the legacy
        ``_planning_contracts.md`` pattern is used for backward compatibility.
        """
        sprint_dir.mkdir(parents=True, exist_ok=True)
        paths = []
        for name in ARTIFACT_NAMES:
            content = getattr(self, name)
            if sprint_prefix:
                filename = f"{sprint_prefix}_planning_{name}.md"
            else:
                filename = f"_planning_{name}.md"
            path = sprint_dir / filename
            path.write_text(content)
            paths.append(path)
        return paths

    @classmethod
    def read_from_dir(cls, sprint_dir: Path, sprint_prefix: str | None = None) -> PlanningArtifacts | None:
        """Read planning artifacts from a sprint directory. Returns None if not found.

        Tries the new ``sprint-NN_planning_*.md`` naming first (when *sprint_prefix*
        is provided), then falls back to the legacy ``_planning_*.md`` pattern.
        """
        fields = {}
        for name in ARTIFACT_NAMES:
            path = None
            if sprint_prefix:
                candidate = sprint_dir / f"{sprint_prefix}_planning_{name}.md"
                if candidate.exists():
                    path = candidate
            if path is None:
                legacy = sprint_dir / f"_planning_{name}.md"
                if legacy.exists():
                    path = legacy
            if path is None:
                return None
            fields[name] = path.read_text()
        return cls(**fields)

    def to_context_string(self) -> str:
        """Format all artifacts as a single context string for agent prompts."""
        sections = []
        labels = {
            "contracts": "API Contracts & Interfaces",
            "team_plan": "Team Plan & Agent Composition",
            "tdd_strategy": "TDD Strategy",
            "coding_strategy": "Coding Strategy & Patterns",
            "context_brief": "Context Brief & Domain Knowledge",
        }
        for name in ARTIFACT_NAMES:
            content = getattr(self, name).strip()
            if content:
                label = labels.get(name, name)
                sections.append(f"## {label}\n\n{content}")
        return "\n\n".join(sections)
