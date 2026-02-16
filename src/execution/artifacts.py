"""Sprint completion artifact generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from src.agents.execution.types import AgentResult
from src.execution.hooks import HookResult
from src.workflow.models import Sprint

from .runner import RunResult


@dataclass
class SprintArtifacts:
    """Container for all generated artifact content."""

    deferred: str
    postmortem: str
    quality: str
    contracts: str


class ArtifactGenerator:
    """Generates sprint completion artifact files."""

    def __init__(
        self,
        sprint: Sprint,
        run_result: RunResult,
        hook_results: dict[str, list[HookResult]] | None = None,
    ):
        self._sprint = sprint
        self._result = run_result
        self._hook_results = hook_results or getattr(run_result, "hook_results", {}) or {}

    def generate_deferred(self) -> str:
        """Generate deferred items markdown content."""
        lines = [f"# Deferred Items — {self._sprint.id}: {self._sprint.goal}\n"]
        items = self._result.deferred_items

        if not items:
            lines.append("No deferred items.\n")
            return "\n".join(lines)

        lines.append("")
        for item in items:
            lines.append(f"- [ ] {item}")
        lines.append("")
        return "\n".join(lines)

    def generate_postmortem(self) -> str:
        """Generate postmortem markdown content."""
        r = self._result
        s = self._sprint
        status = "Success" if r.success else "Failed"

        lines = [
            f"# Postmortem — {s.id}: {s.goal}\n",
            f"**Result**: {status} | {r.steps_completed}/{r.steps_total} steps | {r.duration_seconds:.2f}s\n",
        ]

        # Per-step summaries
        if r.agent_results:
            lines.append("## Step Results\n")
            for i, agent_result in enumerate(r.agent_results):
                step_name = s.steps[i].name if i < len(s.steps) else f"step-{i+1}"
                step_status = "passed" if agent_result.success else "FAILED"
                lines.append(f"### {step_name} ({step_status})\n")
                lines.append(f"{agent_result.output}\n")

        # Deferred items summary
        if r.deferred_items:
            lines.append("## Deferred Items\n")
            for item in r.deferred_items:
                lines.append(f"- {item}")
            lines.append("")

        return "\n".join(lines)

    def generate_quality_report(self) -> str:
        """Generate quality report markdown content."""
        lines = [f"# Quality Report — {self._sprint.id}: {self._sprint.goal}\n"]

        # Coverage
        coverages = [
            ar.coverage for ar in self._result.agent_results if ar.coverage is not None
        ]
        if coverages:
            lines.append("## Coverage\n")
            for cov in coverages:
                lines.append(f"- {cov}%")
            lines.append("")

        # Review verdicts
        verdicts = [
            ar.review_verdict
            for ar in self._result.agent_results
            if ar.review_verdict is not None
        ]
        if verdicts:
            lines.append("## Review Verdicts\n")
            for v in verdicts:
                lines.append(f"- {v}")
            lines.append("")

        # Hook/gate results
        if self._hook_results:
            lines.append("## Gate Results\n")
            for point, results in self._hook_results.items():
                lines.append(f"### {point}\n")
                for hr in results:
                    icon = "PASS" if hr.passed else "FAIL"
                    lines.append(f"- [{icon}] {hr.message}")
                lines.append("")

        # Files
        all_modified = []
        all_created = []
        for ar in self._result.agent_results:
            all_modified.extend(ar.files_modified)
            all_created.extend(ar.files_created)

        if all_modified or all_created:
            lines.append("## Files Changed\n")
            if all_modified:
                lines.append("### Modified\n")
                for f in sorted(set(all_modified)):
                    lines.append(f"- `{f}`")
                lines.append("")
            if all_created:
                lines.append("### Created\n")
                for f in sorted(set(all_created)):
                    lines.append(f"- `{f}`")
                lines.append("")

        return "\n".join(lines)

    def generate_contracts(self) -> str:
        """Generate API contracts markdown content."""
        lines = [f"# API Contracts — {self._sprint.id}: {self._sprint.goal}\n"]

        # Deliverables
        if self._sprint.deliverables:
            lines.append("## Deliverables\n")
            for d in self._sprint.deliverables:
                lines.append(f"- {d}")
            lines.append("")

        # Files modified/created (the actual interfaces produced)
        all_modified = []
        all_created = []
        for ar in self._result.agent_results:
            all_modified.extend(ar.files_modified)
            all_created.extend(ar.files_created)

        if all_modified:
            lines.append("## Backend Contracts (Modified)\n")
            for f in sorted(set(all_modified)):
                lines.append(f"- `{f}`")
            lines.append("")

        if all_created:
            lines.append("## Frontend/New Contracts (Created)\n")
            for f in sorted(set(all_created)):
                lines.append(f"- `{f}`")
            lines.append("")

        if not all_modified and not all_created and not self._sprint.deliverables:
            lines.append("None — no files modified or created.\n")

        return "\n".join(lines)

    def generate_all(self) -> SprintArtifacts:
        """Generate all artifact content."""
        return SprintArtifacts(
            deferred=self.generate_deferred(),
            postmortem=self.generate_postmortem(),
            quality=self.generate_quality_report(),
            contracts=self.generate_contracts(),
        )

    def write_sprint_artifacts(self, sprint_dir: Path) -> list[Path]:
        """Write per-sprint artifact files to the sprint folder."""
        sprint_dir.mkdir(parents=True, exist_ok=True)
        artifacts = self.generate_all()
        sid = self._sprint.id

        paths = []
        for name, content in [
            (f"{sid}_deferred.md", artifacts.deferred),
            (f"{sid}_postmortem.md", artifacts.postmortem),
            (f"{sid}_quality.md", artifacts.quality),
            (f"{sid}_contracts.md", artifacts.contracts),
        ]:
            path = sprint_dir / name
            path.write_text(content)
            paths.append(path)

        return paths

    def append_to_cumulative_deferred(self, kanban_dir: Path) -> Path:
        """Append new deferred items to kanban/deferred.md."""
        kanban_dir.mkdir(parents=True, exist_ok=True)
        path = kanban_dir / "deferred.md"
        today = datetime.now().strftime("%Y-%m-%d")

        section = f"\n## {self._sprint.id}: {self._sprint.goal} ({today})\n\n"
        if self._result.deferred_items:
            for item in self._result.deferred_items:
                section += f"- [ ] {item}\n"
        else:
            section += "No deferred items.\n"

        if not path.exists():
            path.write_text(f"# Deferred Items\n{section}")
        else:
            with open(path, "a") as f:
                f.write(section)

        return path

    async def append_and_synthesize_deferred(
        self, kanban_dir: Path, synthesizer=None
    ) -> Path:
        """Append new deferred items then optionally synthesize the file."""
        path = self.append_to_cumulative_deferred(kanban_dir)
        if synthesizer is not None:
            await synthesizer.synthesize_deferred(path)
        return path

    def append_to_cumulative_postmortem(self, kanban_dir: Path) -> Path:
        """Append sprint lessons to kanban/postmortem.md."""
        kanban_dir.mkdir(parents=True, exist_ok=True)
        path = kanban_dir / "postmortem.md"
        today = datetime.now().strftime("%Y-%m-%d")
        status = "Success" if self._result.success else "Failed"
        r = self._result

        section = f"\n## {self._sprint.id}: {self._sprint.goal} ({today})\n\n"
        section += f"**Result**: {status} | {r.steps_completed}/{r.steps_total} steps | {r.duration_seconds:.2f}s\n"

        if r.deferred_items:
            section += "\n**Deferred**: " + ", ".join(r.deferred_items) + "\n"

        if not path.exists():
            path.write_text(f"# Sprint Postmortems\n{section}")
        else:
            with open(path, "a") as f:
                f.write(section)

        return path

    async def append_and_synthesize_postmortem(
        self, kanban_dir: Path, synthesizer=None
    ) -> Path:
        """Append sprint lessons then optionally synthesize the file."""
        path = self.append_to_cumulative_postmortem(kanban_dir)
        if synthesizer is not None:
            await synthesizer.synthesize_postmortem(path)
        return path
