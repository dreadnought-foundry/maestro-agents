"""Filesystem scanner that derives board state from the kanban directory.

No static registry to maintain. The filesystem IS the database:
- Folder location = status (which kanban lane)
- YAML frontmatter = metadata (title, type, epic, dates, hours)
- Epic folders contain their sprints = relationships
"""

from __future__ import annotations

import re
from pathlib import Path

from .models import BoardState, EpicEntry, SprintEntry

STATUS_FOLDERS = [
    "0-backlog",
    "1-todo",
    "2-in-progress",
    "3-done",
    "4-blocked",
    "5-abandoned",
    "6-archived",
]

_STATUS_MAP = {
    "0-backlog": "backlog",
    "1-todo": "todo",
    "2-in-progress": "in-progress",
    "3-done": "done",
    "4-blocked": "blocked",
    "5-abandoned": "abandoned",
    "6-archived": "archived",
}


def parse_yaml_frontmatter(filepath: Path) -> dict:
    """Extract YAML frontmatter from a markdown file."""
    try:
        text = filepath.read_text()
    except (OSError, UnicodeDecodeError):
        return {}

    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}

    result = {}
    for line in match.group(1).splitlines():
        kv = line.split(":", 1)
        if len(kv) == 2:
            key = kv[0].strip()
            val = kv[1].strip().strip('"').strip("'")
            if val in ("null", ""):
                val = None
            result[key] = val
    return result


def _extract_number(name: str, prefix: str) -> int | None:
    """Extract number from 'epic-01_foo' or 'sprint-13_bar'."""
    match = re.match(rf"{prefix}-(\d+)", name)
    return int(match.group(1)) if match else None


def scan_board(kanban_dir: Path) -> BoardState:
    """Scan the kanban board directory and return full project state."""
    state = BoardState()

    for status_folder in STATUS_FOLDERS:
        status_path = kanban_dir / status_folder
        if not status_path.exists():
            continue

        status = _STATUS_MAP.get(status_folder, status_folder)

        for item in sorted(status_path.iterdir()):
            if not item.is_dir():
                continue

            epic_num = _extract_number(item.name, "epic")
            if epic_num is not None:
                state.epics[epic_num] = _scan_epic(item, epic_num, status)

                for sprint_dir in sorted(item.iterdir()):
                    if not sprint_dir.is_dir():
                        continue
                    sprint_num = _extract_number(sprint_dir.name, "sprint")
                    if sprint_num is not None:
                        state.sprints[sprint_num] = _scan_sprint(
                            sprint_dir, sprint_num, status, epic_num
                        )
                continue

            sprint_num = _extract_number(item.name, "sprint")
            if sprint_num is not None:
                state.sprints[sprint_num] = _scan_sprint(
                    item, sprint_num, status, epic=None
                )

    # Derive counters
    if state.epics:
        state.next_epic = max(state.epics.keys()) + 1
    if state.sprints:
        state.next_sprint = max(state.sprints.keys()) + 1

    # Update epic sprint counts from scanned sprints
    for epic_num, epic in state.epics.items():
        epic_sprints = [s for s in state.sprints.values() if s.epic == epic_num]
        epic.total_sprints = len(epic_sprints)
        epic.completed_sprints = sum(1 for s in epic_sprints if s.status == "done")
        epic.sprint_numbers = sorted(s.number for s in epic_sprints)

    return state


def _scan_epic(epic_dir: Path, epic_num: int, status: str) -> EpicEntry:
    epic_file = epic_dir / "_epic.md"
    meta = parse_yaml_frontmatter(epic_file) if epic_file.exists() else {}

    return EpicEntry(
        number=epic_num,
        title=meta.get("title", epic_dir.name),
        status=status,
        created=meta.get("created"),
        started=meta.get("started"),
        completed=meta.get("completed"),
        path=str(epic_dir),
    )


def _scan_sprint(
    sprint_dir: Path, sprint_num: int, status: str, epic: int | None
) -> SprintEntry:
    spec_files = list(sprint_dir.glob(f"sprint-{sprint_num:02d}_*.md"))
    if not spec_files:
        spec_files = list(sprint_dir.glob("*.md"))

    meta = parse_yaml_frontmatter(spec_files[0]) if spec_files else {}

    yaml_epic = meta.get("epic")
    if yaml_epic and yaml_epic != "null":
        try:
            epic = int(yaml_epic)
        except (ValueError, TypeError):
            pass

    hours = meta.get("hours")
    if hours:
        try:
            hours = float(hours)
        except (ValueError, TypeError):
            hours = None

    return SprintEntry(
        number=sprint_num,
        title=meta.get("title", sprint_dir.name),
        status=status,
        sprint_type=meta.get("type"),
        epic=epic,
        created=meta.get("created"),
        started=meta.get("started"),
        completed=meta.get("completed"),
        hours=hours,
        path=str(sprint_dir),
    )


# --- Query helpers ---


def get_sprint(num: int, kanban_dir: Path | None = None) -> SprintEntry | None:
    if kanban_dir is None:
        raise ValueError("kanban_dir is required")
    return scan_board(kanban_dir).sprints.get(num)


def get_epic(num: int, kanban_dir: Path | None = None) -> EpicEntry | None:
    if kanban_dir is None:
        raise ValueError("kanban_dir is required")
    return scan_board(kanban_dir).epics.get(num)


def get_sprints_by_status(status: str, kanban_dir: Path | None = None) -> list[SprintEntry]:
    if kanban_dir is None:
        raise ValueError("kanban_dir is required")
    return [s for s in scan_board(kanban_dir).sprints.values() if s.status == status]


def get_sprints_for_epic(epic_num: int, kanban_dir: Path | None = None) -> list[SprintEntry]:
    if kanban_dir is None:
        raise ValueError("kanban_dir is required")
    return sorted(
        [s for s in scan_board(kanban_dir).sprints.values() if s.epic == epic_num],
        key=lambda s: s.number,
    )
