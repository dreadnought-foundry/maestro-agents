#!/usr/bin/env python3
"""Sprint & epic lifecycle CLI.

Backs all workflow skills (/sprint-start, /epic-new, etc.) with
deterministic filesystem operations. No agents, no context cost.

Usage:
    python3 scripts/sprint_lifecycle.py <command> [args]

Commands:
    create-sprint <num> <title> [--type TYPE] [--epic NUM]
    start-sprint <num>
    complete-sprint <num>
    review-sprint <num>
    reject-sprint <num> <reason>
    block-sprint <num> <reason>
    resume-sprint <num>
    abort-sprint <num> [reason]

    create-epic <num> <title>
    start-epic <num>
    complete-epic <num>
    archive-epic <num>
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COLUMNS = [
    "0-backlog", "1-todo", "2-in-progress", "3-review",
    "4-done", "5-blocked", "6-abandoned", "7-archived",
]

SPRINT_TYPES = [
    "fullstack", "backend", "frontend", "research", "spike", "infrastructure",
    "integration",
]


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------

def project_root() -> Path:
    """Walk up from this script to find the project root (has kanban/)."""
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "kanban").is_dir():
            return p
        p = p.parent
    sys.exit("Error: Could not find project root (no kanban/ directory)")


def kanban_root() -> Path:
    return project_root() / "kanban"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slugify(title: str) -> str:
    s = title.lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    return s.strip("-")


# --- Find ---

def find_sprint(num: int) -> Path | None:
    """Find a sprint .md file by number across all columns."""
    pattern = f"**/sprint-{num:02d}_*.md"
    for col in COLUMNS:
        col_dir = kanban_root() / col
        if not col_dir.exists():
            continue
        matches = [
            f for f in col_dir.glob(pattern)
            if not any(s in f.name for s in ["_postmortem", "_quality", "_contracts", "_deferred"])
        ]
        if matches:
            return matches[0]
    return None


def find_epic(num: int) -> Path | None:
    """Find an epic folder by number across all columns."""
    pattern = f"epic-{num:02d}_*"
    for col in COLUMNS:
        col_dir = kanban_root() / col
        if not col_dir.exists():
            continue
        for d in col_dir.glob(pattern):
            if d.is_dir():
                return d
    return None


def sprint_column(sprint_path: Path) -> str:
    """Get which column a sprint is in (e.g., '2-in-progress')."""
    for part in sprint_path.parts:
        if part in COLUMNS:
            return part
    return "unknown"


def sprint_status(path: Path) -> str:
    """Infer sprint status from filename suffixes and column."""
    name = path.name + " " + path.parent.name  # check both
    if "--done" in name:
        return "done"
    if "--aborted" in name:
        return "aborted"
    if "--blocked" in name:
        return "blocked"
    col = sprint_column(path)
    if col == "2-in-progress":
        return "in-progress"
    if col == "3-review":
        return "review"
    if col == "4-done":
        return "done"
    if col == "6-abandoned":
        return "aborted"
    if col == "7-archived":
        return "archived"
    return "planning"


def is_nested_in_epic(sprint_path: Path) -> tuple[bool, int | None]:
    """Check if a sprint lives inside an epic folder. Return (is_nested, epic_num)."""
    for parent in sprint_path.parents:
        if parent.name.startswith("epic-"):
            m = re.match(r"epic-(\d+)_", parent.name)
            return True, int(m.group(1)) if m else None
    return False, None


# --- YAML ---

def read_yaml(path: Path) -> dict:
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
            if val == "null" or val == "":
                val = None
            result[key.strip()] = val
    return result


def update_yaml(path: Path, **fields) -> None:
    """Update YAML frontmatter fields in a markdown file."""
    content = path.read_text()
    m = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not m:
        # No frontmatter — prepend it
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


# --- Move ---

def move_to_column(path: Path, target_col: str) -> Path:
    """Move a file or folder to a target column. Returns new path.

    If the path is inside an epic folder, moves the entire epic.
    """
    target_dir = kanban_root() / target_col
    target_dir.mkdir(parents=True, exist_ok=True)

    nested, _ = is_nested_in_epic(path)
    if nested:
        # Find the epic folder and move the whole thing
        epic_dir = path
        while not epic_dir.name.startswith("epic-"):
            epic_dir = epic_dir.parent
        new_epic_dir = target_dir / epic_dir.name
        if new_epic_dir.exists():
            # Epic already in target — just return the equivalent path
            rel = path.relative_to(epic_dir)
            return new_epic_dir / rel
        shutil.move(str(epic_dir), str(new_epic_dir))
        rel = path.relative_to(epic_dir)
        return new_epic_dir / rel
    else:
        # Standalone sprint — move its folder or file
        if path.is_dir():
            new_path = target_dir / path.name
            shutil.move(str(path), str(new_path))
            return new_path
        elif path.parent.name.startswith("sprint-"):
            # Sprint in its own subfolder
            new_dir = target_dir / path.parent.name
            shutil.move(str(path.parent), str(new_dir))
            return new_dir / path.name
        else:
            new_path = target_dir / path.name
            shutil.move(str(path), str(new_path))
            return new_path


# --- Suffix ---

def add_suffix(path: Path, suffix: str) -> Path:
    """Add a suffix like --done or --blocked to a sprint file and its parent dir."""
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


def remove_suffix(path: Path, suffix: str) -> Path:
    """Remove a suffix like --blocked from a sprint file and its parent dir."""
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


# --- State file ---

def state_path(num: int) -> Path:
    return project_root() / ".claude" / f"sprint-{num}-state.json"


def create_state(num: int, sprint_path: Path, title: str) -> None:
    """Create .claude/sprint-N-state.json."""
    root = project_root()
    sp = state_path(num)
    sp.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "sprint_number": num,
        "sprint_file": str(sprint_path.relative_to(root)),
        "sprint_title": title,
        "status": "in_progress",
        "current_phase": 1,
        "current_step": "1.1",
        "started_at": now_iso(),
        "completed_steps": [],
    }
    sp.write_text(json.dumps(state, indent=2) + "\n")


def update_state(num: int, **fields) -> None:
    """Update fields in the state file."""
    sp = state_path(num)
    if not sp.exists():
        return
    state = json.loads(sp.read_text())
    state.update(fields)
    sp.write_text(json.dumps(state, indent=2) + "\n")


# ---------------------------------------------------------------------------
# Sprint commands
# ---------------------------------------------------------------------------

def cmd_create_sprint(args) -> None:
    num, title = args.num, args.title
    slug = slugify(title)
    sprint_type = args.type

    if args.epic:
        epic_dir = find_epic(args.epic)
        if not epic_dir:
            sys.exit(f"Error: Epic {args.epic} not found. Create it first.")
        parent = epic_dir
    else:
        parent = kanban_root() / "0-backlog"
        parent.mkdir(parents=True, exist_ok=True)

    sprint_dir = parent / f"sprint-{num:02d}_{slug}"
    sprint_file = sprint_dir / f"sprint-{num:02d}_{slug}.md"
    sprint_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    content = f"""---
sprint: {num}
title: "{title}"
type: {sprint_type}
epic: {args.epic or 'null'}
status: planning
created: {now_iso()}
started: null
completed: null
hours: null
---

# Sprint {num}: {title}

## Overview

| Field | Value |
|-------|-------|
| Sprint | {num} |
| Title | {title} |
| Type | {sprint_type} |
| Epic | {args.epic or 'None'} |
| Status | Planning |
| Created | {today} |

## Goal

_To be defined_

## Tasks

### Phase 1: Planning
- [ ] Review requirements
- [ ] Design approach

### Phase 2: Implementation
- [ ] Implement feature
- [ ] Write tests

### Phase 3: Validation
- [ ] Quality review

## Acceptance Criteria

- [ ] All tests passing
- [ ] Code reviewed
"""
    sprint_file.write_text(content)
    print(f"Created sprint {num}: {title}")
    print(f"  File: {sprint_file.relative_to(project_root())}")


def cmd_start_sprint(args) -> None:
    num = args.num
    path = find_sprint(num)
    if not path:
        sys.exit(f"Error: Sprint {num} not found")

    status = sprint_status(path)
    if status == "done":
        sys.exit(f"Error: Sprint {num} is already done")
    if status == "aborted":
        sys.exit(f"Error: Sprint {num} is aborted")
    if status == "blocked":
        sys.exit(f"Error: Sprint {num} is blocked. Use resume-sprint first.")

    # A sprint in 2-in-progress (because its epic was moved) but with
    # YAML status still "planning" hasn't been individually started yet.
    yaml = read_yaml(path)
    yaml_status = yaml.get("status", "planning")
    if status == "in-progress" and yaml_status not in ("planning", "null", None):
        sys.exit(f"Error: Sprint {num} is already in progress")

    title = yaml.get("title", f"Sprint {num}")

    update_yaml(path, status="in-progress", started=now_iso())

    col = sprint_column(path)
    if col != "2-in-progress":
        path = move_to_column(path, "2-in-progress")

    create_state(num, path, title)

    print(f"Sprint {num}: {title} — STARTED")
    print(f"  File: {path.relative_to(project_root())}")
    print(f"  State: {state_path(num).name}")


def cmd_complete_sprint(args) -> None:
    num = args.num
    path = find_sprint(num)
    if not path:
        sys.exit(f"Error: Sprint {num} not found")

    status = sprint_status(path)
    if status == "done":
        sys.exit(f"Error: Sprint {num} is already done")
    if status == "aborted":
        sys.exit(f"Error: Sprint {num} is aborted — cannot complete")
    if status == "blocked":
        sys.exit(f"Error: Sprint {num} is blocked. Use resume-sprint first.")
    if status not in ("in-progress", "review"):
        sys.exit(f"Error: Sprint {num} is not in progress or review (status: {status})")

    yaml = read_yaml(path)
    title = yaml.get("title", f"Sprint {num}")

    # Calculate hours
    hours = None
    started = yaml.get("started")
    if started and started != "null":
        try:
            start_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
            hours = round((datetime.now(timezone.utc) - start_dt).total_seconds() / 3600, 1)
        except ValueError:
            pass

    update_yaml(path, status="done", completed=now_iso(), **({} if hours is None else {"hours": hours}))
    path = add_suffix(path, "done")

    nested, _ = is_nested_in_epic(path)
    if not nested:
        path = move_to_column(path, "4-done")

    update_state(num, status="done", completed_at=now_iso())

    print(f"Sprint {num}: {title} — COMPLETE")
    print(f"  File: {path.relative_to(project_root())}")
    if hours:
        print(f"  Hours: {hours}")


def cmd_review_sprint(args) -> None:
    num = args.num
    path = find_sprint(num)
    if not path:
        sys.exit(f"Error: Sprint {num} not found")

    status = sprint_status(path)
    if status == "review":
        sys.exit(f"Error: Sprint {num} is already in review")
    if status == "done":
        sys.exit(f"Error: Sprint {num} is already done")
    if status == "aborted":
        sys.exit(f"Error: Sprint {num} is aborted — cannot review")
    if status == "blocked":
        sys.exit(f"Error: Sprint {num} is blocked. Use resume-sprint first.")
    if status == "planning":
        sys.exit(f"Error: Sprint {num} hasn't been started yet")

    yaml = read_yaml(path)
    title = yaml.get("title", f"Sprint {num}")

    update_yaml(path, status="review")

    col = sprint_column(path)
    if col != "3-review":
        path = move_to_column(path, "3-review")

    update_state(num, status="review")

    print(f"Sprint {num}: {title} — IN REVIEW")
    print(f"  File: {path.relative_to(project_root())}")
    print(f"  Complete: python3 scripts/sprint_lifecycle.py complete-sprint {num}")
    print(f"  Reject:   python3 scripts/sprint_lifecycle.py reject-sprint {num} \"reason\"")


def cmd_reject_sprint(args) -> None:
    num, reason = args.num, args.reason
    path = find_sprint(num)
    if not path:
        sys.exit(f"Error: Sprint {num} not found")

    status = sprint_status(path)
    if status != "review":
        sys.exit(f"Error: Sprint {num} is not in review (status: {status})")

    yaml = read_yaml(path)
    title = yaml.get("title", f"Sprint {num}")

    update_yaml(path, status="in-progress", rejection_reason=reason, rejected_at=now_iso())

    col = sprint_column(path)
    if col != "2-in-progress":
        path = move_to_column(path, "2-in-progress")

    update_state(num, status="in_progress", rejection_reason=reason, rejected_at=now_iso())

    print(f"Sprint {num}: {title} — REJECTED")
    print(f"  Reason: {reason}")
    print(f"  File: {path.relative_to(project_root())}")
    print(f"  Sprint moved back to In Progress for rework.")


def cmd_block_sprint(args) -> None:
    num, reason = args.num, args.reason
    path = find_sprint(num)
    if not path:
        sys.exit(f"Error: Sprint {num} not found")

    status = sprint_status(path)
    if status == "blocked":
        sys.exit(f"Error: Sprint {num} is already blocked")
    if status == "done":
        sys.exit(f"Error: Sprint {num} is done — cannot block")
    if status == "aborted":
        sys.exit(f"Error: Sprint {num} is aborted — cannot block")
    if status == "planning":
        sys.exit(f"Error: Sprint {num} hasn't been started yet")

    yaml = read_yaml(path)
    title = yaml.get("title", f"Sprint {num}")

    update_yaml(path, status="blocked", blocked_at=now_iso(), blocker=reason)
    path = add_suffix(path, "blocked")
    update_state(num, status="blocked", blocked_at=now_iso(), blocker=reason)

    print(f"Sprint {num}: {title} — BLOCKED")
    print(f"  Reason: {reason}")
    print(f"  Resume: python3 scripts/sprint_lifecycle.py resume-sprint {num}")


def cmd_resume_sprint(args) -> None:
    num = args.num
    path = find_sprint(num)
    if not path:
        sys.exit(f"Error: Sprint {num} not found")

    status = sprint_status(path)
    if status != "blocked":
        sys.exit(f"Error: Sprint {num} is not blocked (status: {status})")

    yaml = read_yaml(path)
    title = yaml.get("title", f"Sprint {num}")
    blocker = yaml.get("blocker", "unknown")

    update_yaml(path, status="in-progress", resumed_at=now_iso(), previous_blocker=blocker)
    path = remove_suffix(path, "blocked")
    update_state(num, status="in_progress", resumed_at=now_iso(), previous_blocker=blocker)

    print(f"Sprint {num}: {title} — RESUMED")
    print(f"  Was blocked by: {blocker}")


def cmd_abort_sprint(args) -> None:
    num = args.num
    reason = args.reason or "No reason given"
    path = find_sprint(num)
    if not path:
        sys.exit(f"Error: Sprint {num} not found")

    status = sprint_status(path)
    if status == "aborted":
        sys.exit(f"Error: Sprint {num} is already aborted")
    if status == "done":
        sys.exit(f"Error: Sprint {num} is done — cannot abort")

    yaml = read_yaml(path)
    title = yaml.get("title", f"Sprint {num}")

    update_yaml(path, status="aborted", aborted_at=now_iso(), abort_reason=reason)
    path = add_suffix(path, "aborted")
    update_state(num, status="aborted", aborted_at=now_iso(), abort_reason=reason)

    print(f"Sprint {num}: {title} — ABORTED")
    print(f"  Reason: {reason}")


# ---------------------------------------------------------------------------
# Epic commands
# ---------------------------------------------------------------------------

def cmd_create_epic(args) -> None:
    num, title = args.num, args.title
    slug = slugify(title)

    epic_dir = kanban_root() / "1-todo" / f"epic-{num:02d}_{slug}"
    epic_file = epic_dir / "_epic.md"
    epic_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    content = f"""---
epic: {num}
title: "{title}"
status: planning
created: {today}
started: null
completed: null
---

# Epic {num:02d}: {title}

## Overview

_To be defined_

## Sprints

| Sprint | Title | Status |
|--------|-------|--------|
| -- | TBD | planned |

## Success Criteria

- [ ] _Define measurable outcomes_
"""
    epic_file.write_text(content)
    print(f"Created epic {num}: {title}")
    print(f"  Folder: {epic_dir.relative_to(project_root())}")


def cmd_start_epic(args) -> None:
    num = args.num
    epic_dir = find_epic(num)
    if not epic_dir:
        sys.exit(f"Error: Epic {num} not found")

    col = None
    for part in epic_dir.parts:
        if part in COLUMNS:
            col = part
    if col == "2-in-progress":
        sys.exit(f"Epic {num} is already in progress")

    epic_file = epic_dir / "_epic.md"
    if not epic_file.exists():
        sys.exit(f"Error: Epic {num} has no _epic.md")

    yaml = read_yaml(epic_file)
    title = yaml.get("title", f"Epic {num}")

    update_yaml(epic_file, status="in-progress", started=now_iso())

    # Move entire epic folder to in-progress
    target = kanban_root() / "2-in-progress"
    target.mkdir(parents=True, exist_ok=True)
    new_dir = target / epic_dir.name
    shutil.move(str(epic_dir), str(new_dir))

    sprint_count = len(list(new_dir.glob("**/sprint-*.md")))

    print(f"Epic {num}: {title} — STARTED")
    print(f"  Location: {new_dir.relative_to(project_root())}")
    print(f"  Sprints: {sprint_count}")


def cmd_complete_epic(args) -> None:
    num = args.num
    epic_dir = find_epic(num)
    if not epic_dir:
        sys.exit(f"Error: Epic {num} not found")

    epic_file = epic_dir / "_epic.md"
    if not epic_file.exists():
        sys.exit(f"Error: Epic {num} has no _epic.md")

    # Check all sprints are done or aborted
    sprint_files = [
        f for f in epic_dir.glob("**/sprint-*.md")
        if not any(s in f.name for s in ["_postmortem", "_quality", "_contracts", "_deferred"])
    ]
    unfinished = [
        f.name for f in sprint_files
        if "--done" not in f.name and "--aborted" not in f.name
        and "--done" not in f.parent.name and "--aborted" not in f.parent.name
    ]
    if unfinished:
        print(f"Error: Epic {num} has unfinished sprints:")
        for name in unfinished:
            print(f"  - {name}")
        sys.exit(1)

    yaml = read_yaml(epic_file)
    title = yaml.get("title", f"Epic {num}")

    update_yaml(epic_file, status="done", completed=now_iso())

    # Move to 4-done
    target = kanban_root() / "4-done"
    target.mkdir(parents=True, exist_ok=True)
    new_dir = target / epic_dir.name
    shutil.move(str(epic_dir), str(new_dir))

    print(f"Epic {num}: {title} — COMPLETE")
    print(f"  Location: {new_dir.relative_to(project_root())}")


def cmd_archive_epic(args) -> None:
    num = args.num
    epic_dir = find_epic(num)
    if not epic_dir:
        sys.exit(f"Error: Epic {num} not found")

    epic_file = epic_dir / "_epic.md"
    yaml = read_yaml(epic_file) if epic_file.exists() else {}
    title = yaml.get("title", f"Epic {num}")

    if epic_file.exists():
        update_yaml(epic_file, status="archived", archived_at=now_iso())

    target = kanban_root() / "7-archived"
    target.mkdir(parents=True, exist_ok=True)
    new_dir = target / epic_dir.name
    shutil.move(str(epic_dir), str(new_dir))

    print(f"Epic {num}: {title} — ARCHIVED")
    print(f"  Location: {new_dir.relative_to(project_root())}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sprint & epic lifecycle operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # Sprint commands
    p = sub.add_parser("create-sprint", help="Create a new sprint")
    p.add_argument("num", type=int)
    p.add_argument("title")
    p.add_argument("--type", default="fullstack", choices=SPRINT_TYPES)
    p.add_argument("--epic", type=int, default=None)
    p.set_defaults(func=cmd_create_sprint)

    p = sub.add_parser("start-sprint", help="Start a sprint")
    p.add_argument("num", type=int)
    p.set_defaults(func=cmd_start_sprint)

    p = sub.add_parser("complete-sprint", help="Complete a sprint")
    p.add_argument("num", type=int)
    p.set_defaults(func=cmd_complete_sprint)

    p = sub.add_parser("review-sprint", help="Move a sprint to review")
    p.add_argument("num", type=int)
    p.set_defaults(func=cmd_review_sprint)

    p = sub.add_parser("reject-sprint", help="Reject a sprint from review")
    p.add_argument("num", type=int)
    p.add_argument("reason")
    p.set_defaults(func=cmd_reject_sprint)

    p = sub.add_parser("block-sprint", help="Block a sprint")
    p.add_argument("num", type=int)
    p.add_argument("reason")
    p.set_defaults(func=cmd_block_sprint)

    p = sub.add_parser("resume-sprint", help="Resume a blocked sprint")
    p.add_argument("num", type=int)
    p.set_defaults(func=cmd_resume_sprint)

    p = sub.add_parser("abort-sprint", help="Abort a sprint")
    p.add_argument("num", type=int)
    p.add_argument("reason", nargs="?", default=None)
    p.set_defaults(func=cmd_abort_sprint)

    # Epic commands
    p = sub.add_parser("create-epic", help="Create a new epic")
    p.add_argument("num", type=int)
    p.add_argument("title")
    p.set_defaults(func=cmd_create_epic)

    p = sub.add_parser("start-epic", help="Start an epic")
    p.add_argument("num", type=int)
    p.set_defaults(func=cmd_start_epic)

    p = sub.add_parser("complete-epic", help="Complete an epic")
    p.add_argument("num", type=int)
    p.set_defaults(func=cmd_complete_epic)

    p = sub.add_parser("archive-epic", help="Archive a completed epic")
    p.add_argument("num", type=int)
    p.set_defaults(func=cmd_archive_epic)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
