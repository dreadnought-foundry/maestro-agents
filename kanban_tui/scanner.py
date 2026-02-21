"""Scan the kanban directory structure and parse frontmatter from markdown files."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
    history: list[dict] = field(default_factory=list)


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


def _find_sprint_md(sprint_dir: Path) -> Path | None:
    """Find the primary sprint .md file in a sprint folder.

    Prefers the file whose name matches the folder name (ignoring --done/--blocked
    suffixes). Falls back to a file starting with the sprint prefix (e.g. sprint-29_).
    Skips artifact files like _contracts.md, _quality.md, _postmortem.md, _deferred.md.
    """
    folder_stem = re.sub(r"--(done|blocked)$", "", sprint_dir.name)
    md_files = list(sprint_dir.glob("*.md"))
    if not md_files:
        return None

    # Best match: filename stem matches folder name (with or without suffix)
    for md in md_files:
        md_stem = re.sub(r"--(done|blocked)$", "", md.stem)
        if md_stem == folder_stem:
            return md

    # Fallback: file starting with the sprint prefix (sprint-NN_)
    prefix_match = re.match(r"(sprint-\d+_)", sprint_dir.name)
    if prefix_match:
        prefix = prefix_match.group(1)
        for md in md_files:
            if md.name.startswith(prefix) and "_planning_" not in md.stem and not any(
                md.stem.endswith(suffix)
                for suffix in ("_contracts", "_quality", "_postmortem", "_deferred")
            ):
                return md

    # Last resort: first .md file
    return md_files[0]


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


def _parse_sprint_md(
    md_path: Path, movable_path: Path, is_folder: bool, column: str | None = None,
) -> SprintInfo | None:
    fm = parse_frontmatter(md_path)
    number = fm.get("sprint")
    # Fallback: parse sprint number from filename
    if number is None:
        number = _number_from_filename(md_path.name)
    if number is None:
        return None

    # Derive status: path suffix > YAML > column directory > unknown
    status = (
        _status_from_name(movable_path.name)
        or fm.get("status")
        or COLUMN_TO_STATUS.get(column or "", "unknown")
    )

    return SprintInfo(
        number=int(number),
        title=fm.get("title", _title_from_filename(md_path.name)),
        status=status,
        sprint_type=fm.get("type", ""),
        epic_number=fm.get("epic"),
        path=md_path,
        movable_path=movable_path,
        is_folder=is_folder,
        raw_frontmatter=fm,
        history=fm.get("history", []),
    )


COLUMN_ORDER = [
    "0-backlog",
    "1-todo",
    "2-in-progress",
    "3-review",
    "4-done",
    "5-blocked",
    "6-abandoned",
    "7-archived",
]

COLUMN_DISPLAY = {
    "0-backlog": "Backlog",
    "1-todo": "Todo",
    "2-in-progress": "In Progress",
    "3-review": "Review",
    "4-done": "Done",
    "5-blocked": "Blocked",
    "6-abandoned": "Abandoned",
    "7-archived": "Archived",
}

# Maps sprint status values to display column names
STATUS_TO_COLUMN: dict[str, str] = {
    "planning": "1-todo",
    "todo": "1-todo",
    "in-progress": "2-in-progress",
    "review": "3-review",
    "done": "4-done",
    "blocked": "5-blocked",
    "aborted": "6-abandoned",
    "abandoned": "6-abandoned",
    "archived": "7-archived",
}

# Reverse mapping: column directory name → sprint status string
COLUMN_TO_STATUS: dict[str, str] = {
    "0-backlog": "backlog",
    "1-todo": "todo",
    "2-in-progress": "in-progress",
    "3-review": "review",
    "4-done": "done",
    "5-blocked": "blocked",
    "6-abandoned": "abandoned",
    "7-archived": "archived",
}


def _status_from_name(name: str) -> str | None:
    """Detect explicit status from --done or --blocked suffix in a path name."""
    if "--done" in name:
        return "done"
    if "--blocked" in name:
        return "blocked"
    return None


def write_history_entry(md_path: Path, column: str) -> None:
    """Append a column-transition entry to YAML frontmatter history."""
    text = md_path.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return

    fm = yaml.safe_load(match.group(1)) or {}
    history = fm.get("history", [])
    history.append({
        "column": column,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    fm["history"] = history

    # Remove status field if present (superseded by history)
    fm.pop("status", None)

    new_yaml = yaml.dump(fm, default_flow_style=False, sort_keys=False).rstrip("\n")
    new_text = f"---\n{new_yaml}\n---{text[match.end():]}"
    md_path.write_text(new_text, encoding="utf-8")


def _sprint_display_column(sprint: SprintInfo, physical_col: str) -> str:
    """Determine which display column a sprint should appear in.

    The filesystem is the source of truth:
    1. --done / --blocked suffix on the movable path overrides the column
    2. Physical column directory (where the file lives)

    YAML status is informational only — it does not affect column placement.
    """
    suffix_status = _status_from_name(sprint.movable_path.name)
    if suffix_status:
        return STATUS_TO_COLUMN.get(suffix_status, physical_col)
    return physical_col


def scan_kanban(kanban_dir: Path) -> list[ColumnInfo]:
    """Scan the kanban directory and return structured column data.

    Sprints are placed in columns based on their actual status (YAML frontmatter
    and path suffixes), not their filesystem location. An epic whose sprints have
    different statuses will appear in multiple columns, each showing only the
    sprints belonging to that status.
    """
    # Initialize column infos for every existing column directory
    columns: dict[str, ColumnInfo] = {}
    for col_name in COLUMN_ORDER:
        col_path = kanban_dir / col_name
        if col_path.is_dir():
            columns[col_name] = ColumnInfo(
                name=col_name,
                display_name=COLUMN_DISPLAY.get(col_name, col_name),
                path=col_path,
            )

    # First pass: collect all epics (with all their sprints) and standalone sprints,
    # recording the physical column each item was found in for fallback purposes.
    all_epics: dict[int, tuple[EpicInfo, str]] = {}  # epic_number -> (EpicInfo, physical_col)
    all_standalone: list[tuple[SprintInfo, str]] = []  # (sprint, physical_col)

    for col_name in COLUMN_ORDER:
        col_path = kanban_dir / col_name
        if not col_path.is_dir():
            continue

        for entry in sorted(col_path.iterdir()):
            if entry.name.startswith("."):
                continue

            if entry.is_dir() and entry.name.startswith("epic-"):
                epic = _scan_epic(entry, column=col_name)
                if epic and epic.number not in all_epics:
                    all_epics[epic.number] = (epic, col_name)

            elif entry.is_dir() and entry.name.startswith("sprint-"):
                md_file = _find_sprint_md(entry)
                if md_file:
                    sprint = _parse_sprint_md(md_file, movable_path=entry, is_folder=True, column=col_name)
                    if sprint:
                        all_standalone.append((sprint, col_name))

            elif entry.is_file() and entry.name.startswith("sprint-") and entry.suffix == ".md":
                sprint = _parse_sprint_md(entry, movable_path=entry, is_folder=False, column=col_name)
                if sprint:
                    all_standalone.append((sprint, col_name))

    # Second pass: distribute each epic's sprints into their target display columns.
    # The same epic may appear in multiple columns with different sprint subsets.
    # If an epic has no sprints in a column, it won't appear there (no empty epics).
    for epic_number in sorted(all_epics):
        epic, physical_col = all_epics[epic_number]

        sprints_by_col: dict[str, list[SprintInfo]] = {}
        for sprint in epic.sprints:
            target_col = _sprint_display_column(sprint, physical_col)
            if target_col not in columns:
                target_col = physical_col  # fallback if column doesn't exist on disk
            sprints_by_col.setdefault(target_col, []).append(sprint)

        # If the epic has no sprints at all, place it in its physical column
        if not sprints_by_col:
            if physical_col in columns:
                col_epic = EpicInfo(
                    number=epic.number,
                    title=epic.title,
                    status=epic.status,
                    path=epic.path,
                    sprints=[],
                    raw_frontmatter=epic.raw_frontmatter,
                )
                columns[physical_col].epics.append(col_epic)
        else:
            for target_col, sprints in sprints_by_col.items():
                if target_col in columns:
                    col_epic = EpicInfo(
                        number=epic.number,
                        title=epic.title,
                        status=epic.status,
                        path=epic.path,
                        sprints=sorted(sprints, key=lambda s: s.number),
                        raw_frontmatter=epic.raw_frontmatter,
                    )
                    columns[target_col].epics.append(col_epic)


    # Distribute standalone sprints into their target display columns.
    for sprint, physical_col in all_standalone:
        target_col = _sprint_display_column(sprint, physical_col)
        if target_col not in columns:
            target_col = physical_col
        if target_col in columns:
            columns[target_col].standalone_sprints.append(sprint)

    # Sort and return columns in canonical order
    result = []
    for col_name in COLUMN_ORDER:
        if col_name in columns:
            col = columns[col_name]
            col.epics.sort(key=lambda e: e.number)
            col.standalone_sprints.sort(key=lambda s: s.number)
            result.append(col)

    return result


def _scan_epic(epic_dir: Path, column: str | None = None) -> EpicInfo | None:
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
            md_file = _find_sprint_md(entry)
            if md_file:
                sprint = _parse_sprint_md(md_file, movable_path=entry, is_folder=True, column=column)
                if sprint:
                    epic.sprints.append(sprint)

        # Sprint as flat file inside epic
        elif entry.is_file() and entry.name.startswith("sprint-") and entry.suffix == ".md":
            sprint = _parse_sprint_md(entry, movable_path=entry, is_folder=False, column=column)
            if sprint:
                epic.sprints.append(sprint)

    epic.sprints.sort(key=lambda s: s.number)
    return epic
