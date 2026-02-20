"""Kanban filesystem workflow backend.

Implements WorkflowBackend by reading/writing the kanban/ directory structure.
Sprint and epic state lives in folders, YAML frontmatter, and state files —
survives process restarts, unlike InMemoryAdapter.
"""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

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

COLUMNS = [
    "0-backlog", "1-todo", "2-in-progress", "3-review",
    "4-done", "5-blocked", "6-abandoned", "7-archived",
]

COLUMN_TO_STATUS: dict[str, SprintStatus] = {
    "0-backlog": SprintStatus.BACKLOG,
    "1-todo": SprintStatus.TODO,
    "2-in-progress": SprintStatus.IN_PROGRESS,
    "3-review": SprintStatus.REVIEW,
    "4-done": SprintStatus.DONE,
    "5-blocked": SprintStatus.BLOCKED,
    "6-abandoned": SprintStatus.ABANDONED,
    "7-archived": SprintStatus.ARCHIVED,
}

COLUMN_TO_EPIC_STATUS: dict[str, EpicStatus] = {
    "0-backlog": EpicStatus.DRAFT,
    "1-todo": EpicStatus.DRAFT,
    "2-in-progress": EpicStatus.ACTIVE,
    "3-review": EpicStatus.ACTIVE,
    "4-done": EpicStatus.COMPLETED,
    "7-archived": EpicStatus.COMPLETED,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().strftime("%Y-%m-%dT%H:%M:%SZ")


def _slugify(title: str) -> str:
    s = title.lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    return s.strip("-")


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------

def _read_yaml(path: Path) -> dict:
    """Read YAML frontmatter from a markdown file."""
    content = path.read_text()
    m = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not m:
        return {}
    result = {}
    for line in m.group(1).split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            val = val.strip().strip('"')
            if val in ("null", ""):
                val = None
            result[key.strip()] = val
    return result


def _update_yaml(path: Path, **fields) -> None:
    """Update YAML frontmatter fields in a markdown file."""
    content = path.read_text()
    m = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not m:
        yaml_lines = ["---"]
        for k, v in fields.items():
            yaml_lines.append(f"{k}: {_yaml_val(v)}")
        yaml_lines.append("---\n")
        path.write_text("\n".join(yaml_lines) + "\n" + content)
        return

    yaml_block = m.group(1)
    for key, val in fields.items():
        pattern = rf"^{re.escape(key)}:\s*.*$"
        replacement = f"{key}: {_yaml_val(val)}"
        if re.search(pattern, yaml_block, re.MULTILINE):
            yaml_block = re.sub(pattern, replacement, yaml_block, flags=re.MULTILINE)
        else:
            yaml_block += f"\n{replacement}"

    new_content = content[: m.start(1)] + yaml_block + content[m.end(1) :]
    path.write_text(new_content)


def _yaml_val(v) -> str:
    if v is None:
        return "null"
    if isinstance(v, (int, float)):
        return str(v)
    return f'"{v}"' if isinstance(v, str) and " " in v else str(v)


def _find_sprint_file(kanban_dir: Path, sprint_id: str) -> Path | None:
    """Find a sprint .md file by sprint_id (e.g. 's-29' or '29') across all columns."""
    # Extract number from ID
    num_match = re.search(r"(\d+)", sprint_id)
    if not num_match:
        return None
    num = int(num_match.group(1))
    pattern = f"**/sprint-{num:02d}_*.md"
    for col in COLUMNS:
        col_dir = kanban_dir / col
        if not col_dir.exists():
            continue
        matches = [
            f for f in col_dir.glob(pattern)
            if not any(s in f.name for s in ["_postmortem", "_quality", "_contracts", "_deferred"])
        ]
        if matches:
            return matches[0]
    return None


def _find_epic_dir(kanban_dir: Path, epic_id: str) -> Path | None:
    """Find an epic folder by epic_id (e.g. 'e-7' or '7')."""
    num_match = re.search(r"(\d+)", epic_id)
    if not num_match:
        return None
    num = int(num_match.group(1))
    pattern = f"epic-{num:02d}_*"
    for col in COLUMNS:
        col_dir = kanban_dir / col
        if not col_dir.exists():
            continue
        for d in col_dir.glob(pattern):
            if d.is_dir():
                return d
    return None


def _column_of(path: Path) -> str:
    """Get column name from a path (e.g. '2-in-progress')."""
    for part in path.parts:
        if part in COLUMNS:
            return part
    return "unknown"


def _sprint_status_from_path(path: Path) -> SprintStatus:
    """Infer sprint status from filename suffixes and column."""
    name = path.name + " " + path.parent.name
    if "--done" in name:
        return SprintStatus.DONE
    if "--aborted" in name:
        return SprintStatus.ABANDONED
    if "--blocked" in name:
        return SprintStatus.BLOCKED
    col = _column_of(path)
    return COLUMN_TO_STATUS.get(col, SprintStatus.TODO)


def _is_in_epic(path: Path) -> tuple[bool, str | None]:
    """Check if a path is nested inside an epic folder."""
    for parent in path.parents:
        if parent.name.startswith("epic-"):
            m = re.match(r"epic-(\d+)_", parent.name)
            if m:
                return True, f"e-{int(m.group(1))}"
    return False, None


def _add_suffix(path: Path, suffix: str) -> Path:
    """Add --done or --blocked suffix to sprint file and its parent dir."""
    new_file_name = path.stem + f"--{suffix}" + path.suffix
    if path.parent.name.startswith("sprint-") and f"--{suffix}" not in path.parent.name:
        new_dir = path.parent.with_name(path.parent.name + f"--{suffix}")
        path.parent.rename(new_dir)
        old_file = new_dir / path.name
        new_path = new_dir / new_file_name
        old_file.rename(new_path)
        return new_path
    else:
        new_path = path.with_name(new_file_name)
        path.rename(new_path)
        return new_path


def _remove_suffix(path: Path, suffix: str) -> Path:
    """Remove --blocked suffix from sprint file and its parent dir."""
    new_file_name = path.name.replace(f"--{suffix}", "")
    if path.parent.name.startswith("sprint-") and f"--{suffix}" in path.parent.name:
        new_dir = path.parent.with_name(path.parent.name.replace(f"--{suffix}", ""))
        path.parent.rename(new_dir)
        old_file = new_dir / path.name
        new_path = new_dir / new_file_name
        old_file.rename(new_path)
        return new_path
    else:
        new_path = path.with_name(new_file_name)
        path.rename(new_path)
        return new_path


def _move_to_column(path: Path, kanban_dir: Path, target_col: str) -> Path:
    """Move a sprint file/folder to a target column. Returns new path."""
    target_dir = kanban_dir / target_col
    target_dir.mkdir(parents=True, exist_ok=True)

    in_epic, _ = _is_in_epic(path)
    if in_epic:
        # Move the entire epic folder
        epic_dir = path
        while not epic_dir.name.startswith("epic-"):
            epic_dir = epic_dir.parent
        new_epic_dir = target_dir / epic_dir.name
        if new_epic_dir.exists():
            rel = path.relative_to(epic_dir)
            return new_epic_dir / rel
        shutil.move(str(epic_dir), str(new_epic_dir))
        rel = path.relative_to(epic_dir)
        return new_epic_dir / rel
    else:
        if path.parent.name.startswith("sprint-"):
            new_dir = target_dir / path.parent.name
            shutil.move(str(path.parent), str(new_dir))
            return new_dir / path.name
        else:
            new_path = target_dir / path.name
            shutil.move(str(path), str(new_path))
            return new_path


# ---------------------------------------------------------------------------
# State file helpers
# ---------------------------------------------------------------------------

def _state_path(kanban_dir: Path, sprint_id: str) -> Path:
    num_match = re.search(r"(\d+)", sprint_id)
    num = int(num_match.group(1)) if num_match else 0
    # Walk up from kanban_dir to project root
    project_root = kanban_dir.parent
    return project_root / ".claude" / f"sprint-{num}-state.json"


def _read_state(kanban_dir: Path, sprint_id: str) -> dict | None:
    sp = _state_path(kanban_dir, sprint_id)
    if sp.exists():
        return json.loads(sp.read_text())
    return None


def _write_state(kanban_dir: Path, sprint_id: str, state: dict) -> None:
    sp = _state_path(kanban_dir, sprint_id)
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps(state, indent=2) + "\n")


# ---------------------------------------------------------------------------
# KanbanAdapter
# ---------------------------------------------------------------------------

class KanbanAdapter:
    """WorkflowBackend backed by the kanban/ filesystem."""

    def __init__(self, kanban_dir: Path | str = "kanban"):
        self._kanban_dir = Path(kanban_dir).resolve()
        if not self._kanban_dir.exists():
            raise FileNotFoundError(f"Kanban directory not found: {self._kanban_dir}")

    async def get_project_state(self) -> ProjectState:
        epics = await self.list_epics()
        sprints = await self.list_sprints()
        active = None
        for s in sprints:
            if s.status is SprintStatus.IN_PROGRESS:
                active = s.id
                break
        return ProjectState(
            project_name=self._kanban_dir.parent.name,
            epics=epics,
            sprints=sprints,
            active_sprint_id=active,
        )

    async def get_epic(self, epic_id: str) -> Epic:
        epic_dir = _find_epic_dir(self._kanban_dir, epic_id)
        if not epic_dir:
            raise KeyError(f"Epic not found: {epic_id}")
        return self._parse_epic(epic_dir)

    async def get_sprint(self, sprint_id: str) -> Sprint:
        path = _find_sprint_file(self._kanban_dir, sprint_id)
        if not path:
            raise KeyError(f"Sprint not found: {sprint_id}")
        return self._parse_sprint(path, sprint_id)

    async def list_epics(self) -> list[Epic]:
        epics = []
        for col in COLUMNS:
            col_dir = self._kanban_dir / col
            if not col_dir.exists():
                continue
            for d in col_dir.iterdir():
                if d.is_dir() and d.name.startswith("epic-"):
                    epics.append(self._parse_epic(d))
        return epics

    async def list_sprints(self, epic_id: str | None = None) -> list[Sprint]:
        sprints = []
        for col in COLUMNS:
            col_dir = self._kanban_dir / col
            if not col_dir.exists():
                continue
            # Find sprint files in this column (standalone or in epics)
            for md in col_dir.glob("**/sprint-*_*.md"):
                if any(s in md.name for s in ["_postmortem", "_quality", "_contracts", "_deferred"]):
                    continue
                # Extract sprint number for ID
                m = re.match(r"sprint-(\d+)_", md.name)
                if not m:
                    continue
                sid = f"s-{int(m.group(1))}"
                sprint = self._parse_sprint(md, sid)
                if epic_id is None or sprint.epic_id == epic_id:
                    sprints.append(sprint)
        return sprints

    async def create_epic(self, title: str, description: str) -> Epic:
        # Find next available epic number
        existing = await self.list_epics()
        nums = [int(re.search(r"(\d+)", e.id).group(1)) for e in existing if re.search(r"(\d+)", e.id)]
        num = max(nums, default=0) + 1

        slug = _slugify(title)
        epic_dir = self._kanban_dir / "1-todo" / f"epic-{num:02d}_{slug}"
        epic_dir.mkdir(parents=True, exist_ok=True)

        epic_file = epic_dir / "_epic.md"
        content = f"""---
epic: {num}
title: "{title}"
description: "{description}"
status: planning
created: {_now_iso()}
started: null
completed: null
---

# Epic {num:02d}: {title}

{description}

## Sprints

| Sprint | Title | Status |
|--------|-------|--------|
"""
        epic_file.write_text(content)

        return Epic(
            id=f"e-{num}",
            title=title,
            description=description,
            status=EpicStatus.DRAFT,
        )

    async def create_sprint(
        self,
        epic_id: str,
        goal: str,
        tasks: list[dict] | None = None,
        dependencies: list[str] | None = None,
        deliverables: list[str] | None = None,
    ) -> Sprint:
        epic_dir = _find_epic_dir(self._kanban_dir, epic_id)
        if not epic_dir:
            raise KeyError(f"Epic not found: {epic_id}")

        # Find next available sprint number
        all_sprints = await self.list_sprints()
        nums = [int(re.search(r"(\d+)", s.id).group(1)) for s in all_sprints if re.search(r"(\d+)", s.id)]
        num = max(nums, default=0) + 1

        slug = _slugify(goal[:40])
        sprint_dir = epic_dir / f"sprint-{num:02d}_{slug}"
        sprint_file = sprint_dir / f"sprint-{num:02d}_{slug}.md"
        sprint_dir.mkdir(parents=True, exist_ok=True)

        task_names = [t.get("name", "task") for t in (tasks or [])]
        content = f"""---
sprint: {num}
title: "{goal}"
type: fullstack
epic: {epic_id}
status: planning
created: {_now_iso()}
started: null
completed: null
---

# Sprint {num}: {goal}

## Goal

{goal}

## Tasks

{chr(10).join(f'- [ ] {name}' for name in task_names) if task_names else '- [ ] TBD'}
"""
        sprint_file.write_text(content)

        sprint_id = f"s-{num}"
        return Sprint(
            id=sprint_id,
            goal=goal,
            status=SprintStatus.TODO,
            epic_id=epic_id,
            tasks=tasks or [],
            dependencies=dependencies or [],
            deliverables=deliverables or [],
        )

    async def update_sprint(self, sprint_id: str, **fields) -> Sprint:
        path = _find_sprint_file(self._kanban_dir, sprint_id)
        if not path:
            raise KeyError(f"Sprint not found: {sprint_id}")

        # Handle status changes via YAML + filesystem
        if "status" in fields:
            new_status = fields["status"]
            if isinstance(new_status, SprintStatus):
                current_status = _sprint_status_from_path(path)
                _update_yaml(path, status=new_status.value)

                # Remove --blocked suffix when resuming
                if current_status is SprintStatus.BLOCKED and new_status is SprintStatus.IN_PROGRESS:
                    path = _remove_suffix(path, "blocked")

                # Update state file
                state = _read_state(self._kanban_dir, sprint_id) or {}
                state["status"] = new_status.value
                _write_state(self._kanban_dir, sprint_id, state)

        sprint = self._parse_sprint(path, sprint_id)
        for key, value in fields.items():
            if hasattr(sprint, key):
                setattr(sprint, key, value)
            else:
                raise ValueError(f"Unknown sprint field: {key}")
        return sprint

    async def get_status_summary(self) -> dict:
        sprints = await self.list_sprints()
        total = len(sprints)
        completed = sum(1 for s in sprints if s.status is SprintStatus.DONE)
        in_progress = sum(1 for s in sprints if s.status is SprintStatus.IN_PROGRESS)
        blocked = sum(1 for s in sprints if s.status is SprintStatus.BLOCKED)
        planned = sum(1 for s in sprints if s.status is SprintStatus.TODO)
        return {
            "project_name": self._kanban_dir.parent.name,
            "total_epics": len(await self.list_epics()),
            "total_sprints": total,
            "sprints_done": completed,
            "sprints_in_progress": in_progress,
            "sprints_blocked": blocked,
            "sprints_todo": planned,
            "progress_pct": round(completed / total * 100, 1) if total > 0 else 0.0,
        }

    # --- Lifecycle methods ---

    async def start_sprint(self, sprint_id: str) -> Sprint:
        path = _find_sprint_file(self._kanban_dir, sprint_id)
        if not path:
            raise KeyError(f"Sprint not found: {sprint_id}")

        sprint = self._parse_sprint(path, sprint_id)
        validate_transition(sprint_id, sprint.status, SprintStatus.IN_PROGRESS)

        # Auto-create steps from tasks
        if not sprint.steps:
            for i, task in enumerate(sprint.tasks, start=1):
                sprint.steps.append(Step(id=f"step-{i}", name=task["name"]))

        sprint.status = SprintStatus.IN_PROGRESS

        # Start the first step
        if sprint.steps:
            sprint.steps[0].status = StepStatus.IN_PROGRESS
            sprint.steps[0].started_at = _now()

        sprint.transitions.append(SprintTransition(
            from_status=SprintStatus.TODO,
            to_status=SprintStatus.IN_PROGRESS,
            timestamp=_now(),
        ))

        # Update filesystem
        _update_yaml(path, status="in-progress", started=_now_iso())
        col = _column_of(path)
        if col != "2-in-progress":
            path = _move_to_column(path, self._kanban_dir, "2-in-progress")

        # Create state file with steps
        state = {
            "sprint_id": sprint_id,
            "status": "in_progress",
            "started_at": _now_iso(),
            "steps": [
                {"id": s.id, "name": s.name, "status": s.status.value}
                for s in sprint.steps
            ],
        }
        _write_state(self._kanban_dir, sprint_id, state)

        return sprint

    async def advance_step(self, sprint_id: str, step_output: dict | None = None) -> Sprint:
        path = _find_sprint_file(self._kanban_dir, sprint_id)
        if not path:
            raise KeyError(f"Sprint not found: {sprint_id}")

        sprint = self._parse_sprint(path, sprint_id)

        # Find current IN_PROGRESS step
        current_idx = None
        for i, step in enumerate(sprint.steps):
            if step.status is StepStatus.IN_PROGRESS:
                current_idx = i
                break

        if current_idx is None:
            raise ValueError(f"No step currently in progress for sprint {sprint_id}")

        # Mark current step done
        current_step = sprint.steps[current_idx]
        current_step.status = StepStatus.DONE
        current_step.completed_at = _now()
        if step_output is not None:
            current_step.output = step_output

        # Start next step if there is one
        next_idx = current_idx + 1
        if next_idx < len(sprint.steps):
            sprint.steps[next_idx].status = StepStatus.IN_PROGRESS
            sprint.steps[next_idx].started_at = _now()

        # Update state file
        state = _read_state(self._kanban_dir, sprint_id) or {}
        state["steps"] = [
            {"id": s.id, "name": s.name, "status": s.status.value}
            for s in sprint.steps
        ]
        _write_state(self._kanban_dir, sprint_id, state)

        return sprint

    async def complete_sprint(self, sprint_id: str) -> Sprint:
        path = _find_sprint_file(self._kanban_dir, sprint_id)
        if not path:
            raise KeyError(f"Sprint not found: {sprint_id}")

        sprint = self._parse_sprint(path, sprint_id)
        previous_status = sprint.status
        validate_transition(sprint_id, sprint.status, SprintStatus.DONE)

        # Verify all steps done or skipped
        terminal = {StepStatus.DONE, StepStatus.SKIPPED}
        if sprint.steps and not all(s.status in terminal for s in sprint.steps):
            raise ValueError(f"Not all steps are done for sprint {sprint_id}")

        sprint.status = SprintStatus.DONE
        sprint.transitions.append(SprintTransition(
            from_status=previous_status,
            to_status=SprintStatus.DONE,
            timestamp=_now(),
        ))

        # Update filesystem
        _update_yaml(path, status="done", completed=_now_iso())
        path = _add_suffix(path, "done")

        in_epic, _ = _is_in_epic(path)
        if not in_epic:
            path = _move_to_column(path, self._kanban_dir, "4-done")

        # Update state file
        state = _read_state(self._kanban_dir, sprint_id) or {}
        state["status"] = "done"
        state["completed_at"] = _now_iso()
        _write_state(self._kanban_dir, sprint_id, state)

        return sprint

    async def move_to_review(self, sprint_id: str) -> Sprint:
        path = _find_sprint_file(self._kanban_dir, sprint_id)
        if not path:
            raise KeyError(f"Sprint not found: {sprint_id}")

        sprint = self._parse_sprint(path, sprint_id)
        validate_transition(sprint_id, sprint.status, SprintStatus.REVIEW)

        # Verify all steps done or skipped
        terminal = {StepStatus.DONE, StepStatus.SKIPPED}
        if sprint.steps and not all(s.status in terminal for s in sprint.steps):
            raise ValueError(f"Not all steps are done for sprint {sprint_id}")

        sprint.status = SprintStatus.REVIEW
        sprint.transitions.append(SprintTransition(
            from_status=SprintStatus.IN_PROGRESS,
            to_status=SprintStatus.REVIEW,
            timestamp=_now(),
        ))

        # Update filesystem
        _update_yaml(path, status="review")
        col = _column_of(path)
        if col != "3-review":
            path = _move_to_column(path, self._kanban_dir, "3-review")

        # Update state file
        state = _read_state(self._kanban_dir, sprint_id) or {}
        state["status"] = "review"
        _write_state(self._kanban_dir, sprint_id, state)

        return sprint

    async def reject_sprint(self, sprint_id: str, reason: str) -> Sprint:
        path = _find_sprint_file(self._kanban_dir, sprint_id)
        if not path:
            raise KeyError(f"Sprint not found: {sprint_id}")

        sprint = self._parse_sprint(path, sprint_id)
        validate_transition(sprint_id, sprint.status, SprintStatus.IN_PROGRESS)

        sprint.status = SprintStatus.IN_PROGRESS
        sprint.transitions.append(SprintTransition(
            from_status=SprintStatus.REVIEW,
            to_status=SprintStatus.IN_PROGRESS,
            timestamp=_now(),
            reason=reason,
        ))

        # Update filesystem
        _update_yaml(path, status="in-progress", rejection_reason=reason, rejected_at=_now_iso())
        col = _column_of(path)
        if col != "2-in-progress":
            path = _move_to_column(path, self._kanban_dir, "2-in-progress")

        # Update state file with rejection feedback
        state = _read_state(self._kanban_dir, sprint_id) or {}
        state["status"] = "in_progress"
        state["rejection_reason"] = reason
        state.setdefault("rejection_history", []).append({
            "reason": reason,
            "timestamp": _now_iso(),
        })
        _write_state(self._kanban_dir, sprint_id, state)

        return sprint

    async def block_sprint(self, sprint_id: str, reason: str) -> Sprint:
        path = _find_sprint_file(self._kanban_dir, sprint_id)
        if not path:
            raise KeyError(f"Sprint not found: {sprint_id}")

        sprint = self._parse_sprint(path, sprint_id)
        validate_transition(sprint_id, sprint.status, SprintStatus.BLOCKED)

        sprint.status = SprintStatus.BLOCKED
        sprint.transitions.append(SprintTransition(
            from_status=SprintStatus.IN_PROGRESS,
            to_status=SprintStatus.BLOCKED,
            timestamp=_now(),
            reason=reason,
        ))

        # Update filesystem
        _update_yaml(path, status="blocked", blocked_at=_now_iso(), blocker=reason)
        _add_suffix(path, "blocked")

        # Update state file
        state = _read_state(self._kanban_dir, sprint_id) or {}
        state["status"] = "blocked"
        state["blocker"] = reason
        _write_state(self._kanban_dir, sprint_id, state)

        return sprint

    async def get_step_status(self, sprint_id: str) -> dict:
        path = _find_sprint_file(self._kanban_dir, sprint_id)
        if not path:
            raise KeyError(f"Sprint not found: {sprint_id}")

        sprint = self._parse_sprint(path, sprint_id)

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

    # --- Parsing helpers ---

    def _parse_epic(self, epic_dir: Path) -> Epic:
        """Parse an epic from its directory."""
        m = re.match(r"epic-(\d+)_", epic_dir.name)
        num = int(m.group(1)) if m else 0
        epic_id = f"e-{num}"

        epic_file = epic_dir / "_epic.md"
        if epic_file.exists():
            yaml = _read_yaml(epic_file)
            title = yaml.get("title", epic_dir.name)
            description = yaml.get("description", "")
        else:
            title = epic_dir.name
            description = ""

        col = _column_of(epic_dir)
        status = COLUMN_TO_EPIC_STATUS.get(col, EpicStatus.DRAFT)

        # Collect sprint IDs
        sprint_ids = []
        for md in epic_dir.glob("**/sprint-*_*.md"):
            if any(s in md.name for s in ["_postmortem", "_quality", "_contracts", "_deferred"]):
                continue
            sm = re.match(r"sprint-(\d+)_", md.name)
            if sm:
                sprint_ids.append(f"s-{int(sm.group(1))}")

        return Epic(
            id=epic_id,
            title=title,
            description=description or "",
            status=status,
            sprint_ids=sprint_ids,
        )

    def _parse_sprint(self, path: Path, sprint_id: str) -> Sprint:
        """Parse a sprint from its markdown file + state file."""
        yaml = _read_yaml(path)
        goal = yaml.get("title", "")
        status = _sprint_status_from_path(path)

        # Check YAML status for more precise state
        yaml_status = yaml.get("status")
        if yaml_status == "in-progress" and status == SprintStatus.TODO:
            status = SprintStatus.IN_PROGRESS
        elif yaml_status == "review" and status != SprintStatus.REVIEW:
            status = SprintStatus.REVIEW

        in_epic, epic_id = _is_in_epic(path)
        if not epic_id:
            epic_id = yaml.get("epic", "")
            if epic_id and epic_id != "null":
                epic_id = f"e-{epic_id}" if not str(epic_id).startswith("e-") else epic_id
            else:
                epic_id = ""

        # Parse tasks from markdown checkboxes
        tasks = []
        deliverables = []
        content = path.read_text()
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("- [ ] ") or stripped.startswith("- [x] "):
                task_name = stripped[6:].strip()
                tasks.append({"name": task_name})

        # Load steps from state file
        steps = []
        state = _read_state(self._kanban_dir, sprint_id)
        if state and "steps" in state:
            for s in state["steps"]:
                steps.append(Step(
                    id=s["id"],
                    name=s["name"],
                    status=StepStatus(s["status"]),
                ))

        return Sprint(
            id=sprint_id,
            goal=goal,
            status=status,
            epic_id=epic_id,
            tasks=tasks,
            deliverables=deliverables,
            steps=steps,
        )
