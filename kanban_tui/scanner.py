"""Scan the kanban directory structure and parse frontmatter from markdown files."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class SprintInfo:
    number: int
    title: str
    status: str
    sprint_type: str
    epic_number: int | None
    path: Path  # the .md file
    movable_path: Path  # the folder or file to move
    is_folder: bool
    raw_frontmatter: dict = field(default_factory=dict)


@dataclass
class EpicInfo:
    number: int
    title: str
    status: str
    path: Path  # the epic directory
    sprints: list[SprintInfo] = field(default_factory=list)
    raw_frontmatter: dict = field(default_factory=dict)


@dataclass
class ColumnInfo:
    name: str
    display_name: str
    path: Path
    epics: list[EpicInfo] = field(default_factory=list)
    standalone_sprints: list[SprintInfo] = field(default_factory=list)


def parse_frontmatter(filepath: Path) -> dict:
    """Extract YAML frontmatter from a markdown file."""
    try:
        text = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}

    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}

    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}


def _number_from_filename(name: str) -> int | None:
    """Extract sprint number from a filename like 'sprint-09_step-models.md'."""
    m = re.match(r"sprint-(\d+)", name)
    return int(m.group(1)) if m else None


def _title_from_filename(name: str) -> str:
    """Derive a human title from a filename like 'sprint-01_workflow-models-and-interface.md'."""
    stem = Path(name).stem
    # Remove 'sprint-NN_' prefix
    cleaned = re.sub(r"^sprint-\d+_?", "", stem)
    return cleaned.replace("-", " ").replace("_", " ").strip().title() or stem


def _parse_sprint_md(md_path: Path, movable_path: Path, is_folder: bool) -> SprintInfo | None:
    fm = parse_frontmatter(md_path)
    number = fm.get("sprint")
    # Fallback: parse sprint number from filename
    if number is None:
        number = _number_from_filename(md_path.name)
    if number is None:
        return None
    return SprintInfo(
        number=int(number),
        title=fm.get("title", _title_from_filename(md_path.name)),
        status=fm.get("status", "unknown"),
        sprint_type=fm.get("type", ""),
        epic_number=fm.get("epic"),
        path=md_path,
        movable_path=movable_path,
        is_folder=is_folder,
        raw_frontmatter=fm,
    )


COLUMN_ORDER = [
    "0-backlog",
    "1-todo",
    "2-in-progress",
    "3-done",
    "4-blocked",
    "5-abandoned",
    "6-archived",
]

COLUMN_DISPLAY = {
    "0-backlog": "Backlog",
    "1-todo": "Todo",
    "2-in-progress": "In Progress",
    "3-done": "Done",
    "4-blocked": "Blocked",
    "5-abandoned": "Abandoned",
    "6-archived": "Archived",
}


def scan_kanban(kanban_dir: Path) -> list[ColumnInfo]:
    """Scan the kanban directory and return structured column data."""
    columns: list[ColumnInfo] = []

    for col_name in COLUMN_ORDER:
        col_path = kanban_dir / col_name
        if not col_path.is_dir():
            continue

        column = ColumnInfo(
            name=col_name,
            display_name=COLUMN_DISPLAY.get(col_name, col_name),
            path=col_path,
        )

        for entry in sorted(col_path.iterdir()):
            if entry.name.startswith("."):
                continue

            # Epic directory
            if entry.is_dir() and entry.name.startswith("epic-"):
                epic = _scan_epic(entry)
                if epic:
                    column.epics.append(epic)

            # Standalone sprint directory
            elif entry.is_dir() and entry.name.startswith("sprint-"):
                md_files = list(entry.glob("*.md"))
                if md_files:
                    sprint = _parse_sprint_md(md_files[0], movable_path=entry, is_folder=True)
                    if sprint:
                        column.standalone_sprints.append(sprint)

            # Standalone sprint flat file
            elif entry.is_file() and entry.name.startswith("sprint-") and entry.suffix == ".md":
                sprint = _parse_sprint_md(entry, movable_path=entry, is_folder=False)
                if sprint:
                    column.standalone_sprints.append(sprint)

        # Sort epics and sprints by number
        column.epics.sort(key=lambda e: e.number)
        column.standalone_sprints.sort(key=lambda s: s.number)
        columns.append(column)

    return columns


def _scan_epic(epic_dir: Path) -> EpicInfo | None:
    """Scan an epic directory for its metadata and sprints."""
    epic_md = epic_dir / "_epic.md"
    fm = parse_frontmatter(epic_md) if epic_md.exists() else {}

    number_match = re.match(r"epic-(\d+)", epic_dir.name)
    if not number_match:
        return None

    epic = EpicInfo(
        number=int(number_match.group(1)),
        title=fm.get("title", epic_dir.name),
        status=fm.get("status", "unknown"),
        path=epic_dir,
        raw_frontmatter=fm,
    )

    for entry in sorted(epic_dir.iterdir()):
        if entry.name.startswith(".") or entry.name == "_epic.md":
            continue

        # Sprint as subfolder
        if entry.is_dir() and entry.name.startswith("sprint-"):
            md_files = list(entry.glob("*.md"))
            if md_files:
                sprint = _parse_sprint_md(md_files[0], movable_path=entry, is_folder=True)
                if sprint:
                    epic.sprints.append(sprint)

        # Sprint as flat file inside epic
        elif entry.is_file() and entry.name.startswith("sprint-") and entry.suffix == ".md":
            sprint = _parse_sprint_md(entry, movable_path=entry, is_folder=False)
            if sprint:
                epic.sprints.append(sprint)

    epic.sprints.sort(key=lambda s: s.number)
    return epic
