"""Pure handler functions for kanban board MCP tools.

Each handler takes (args, kanban_dir) and returns MCP result format.
No SDK dependency — testable with a tmp_path kanban directory.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .scanner import scan_board, get_sprints_for_epic


def _text_result(text: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}]}


def _json_result(data: Any) -> dict[str, Any]:
    return _text_result(json.dumps(data, indent=2, default=str))


async def get_board_status_handler(
    args: dict[str, Any], kanban_dir: Path
) -> dict[str, Any]:
    """Get full kanban board overview: all epics, sprint counts, status breakdown."""
    state = scan_board(kanban_dir)

    status_counts: dict[str, int] = {}
    for s in state.sprints.values():
        status_counts[s.status] = status_counts.get(s.status, 0) + 1

    return _json_result({
        "epics": {
            str(k): {
                "title": v.title,
                "status": v.status,
                "sprints": f"{v.completed_sprints}/{v.total_sprints}",
            }
            for k, v in sorted(state.epics.items())
        },
        "sprint_count": len(state.sprints),
        "by_status": status_counts,
        "next_epic": state.next_epic,
        "next_sprint": state.next_sprint,
    })


async def get_board_epic_handler(
    args: dict[str, Any], kanban_dir: Path
) -> dict[str, Any]:
    """Get epic detail with all its sprints."""
    epic_num = int(args["epic_number"])
    state = scan_board(kanban_dir)
    epic = state.epics.get(epic_num)

    if not epic:
        return _text_result(f"Error: Epic {epic_num} not found")

    sprints = get_sprints_for_epic(epic_num, kanban_dir)

    return _json_result({
        "epic": asdict(epic),
        "sprints": [asdict(s) for s in sprints],
    })


async def get_board_sprint_handler(
    args: dict[str, Any], kanban_dir: Path
) -> dict[str, Any]:
    """Get sprint detail including spec file content."""
    sprint_num = int(args["sprint_number"])
    state = scan_board(kanban_dir)
    sprint = state.sprints.get(sprint_num)

    if not sprint:
        return _text_result(f"Error: Sprint {sprint_num} not found")

    # Read the spec file content
    sprint_dir = Path(sprint.path)
    spec_files = list(sprint_dir.glob(f"sprint-{sprint_num:02d}_*.md"))
    if not spec_files:
        spec_files = list(sprint_dir.glob("*.md"))

    spec_content = spec_files[0].read_text() if spec_files else ""

    return _json_result({
        "sprint": asdict(sprint),
        "spec": spec_content,
    })


async def list_board_sprints_handler(
    args: dict[str, Any], kanban_dir: Path
) -> dict[str, Any]:
    """List sprints filtered by status and/or epic."""
    state = scan_board(kanban_dir)
    sprints = list(state.sprints.values())

    status_filter = args.get("status")
    if status_filter:
        sprints = [s for s in sprints if s.status == status_filter]

    epic_filter = args.get("epic_number")
    if epic_filter:
        epic_num = int(epic_filter)
        sprints = [s for s in sprints if s.epic == epic_num]

    sprints.sort(key=lambda s: s.number)
    return _json_result([asdict(s) for s in sprints])
