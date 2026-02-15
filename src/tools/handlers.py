"""Pure handler functions for workflow MCP tools.

Each handler takes (args, backend) and returns MCP result format.
No SDK dependency — testable with InMemoryAdapter.
"""

import json
from dataclasses import asdict
from typing import Any

from ..workflow.interface import WorkflowBackend


def _text_result(text: str) -> dict[str, Any]:
    """Build MCP tool result with a text content block."""
    return {"content": [{"type": "text", "text": text}]}


def _json_result(data: Any) -> dict[str, Any]:
    """Build MCP tool result with JSON-serialized content."""
    return _text_result(json.dumps(data, indent=2, default=str))


async def get_project_status_handler(
    args: dict[str, Any], backend: WorkflowBackend
) -> dict[str, Any]:
    """Get overall project status summary."""
    summary = await backend.get_status_summary()
    return _json_result(summary)


async def list_epics_handler(
    args: dict[str, Any], backend: WorkflowBackend
) -> dict[str, Any]:
    """List all epics in the project."""
    epics = await backend.list_epics()
    data = [asdict(e) for e in epics]
    return _json_result(data)


async def get_epic_handler(
    args: dict[str, Any], backend: WorkflowBackend
) -> dict[str, Any]:
    """Get details of a specific epic."""
    epic_id = args["epic_id"]
    try:
        epic = await backend.get_epic(epic_id)
    except KeyError:
        return _text_result(f"Error: Epic not found: {epic_id}")
    return _json_result(asdict(epic))


async def list_sprints_handler(
    args: dict[str, Any], backend: WorkflowBackend
) -> dict[str, Any]:
    """List sprints, optionally filtered by epic_id."""
    epic_id = args.get("epic_id")
    sprints = await backend.list_sprints(epic_id=epic_id)
    data = [asdict(s) for s in sprints]
    return _json_result(data)


async def get_sprint_handler(
    args: dict[str, Any], backend: WorkflowBackend
) -> dict[str, Any]:
    """Get full sprint specification."""
    sprint_id = args["sprint_id"]
    try:
        sprint = await backend.get_sprint(sprint_id)
    except KeyError:
        return _text_result(f"Error: Sprint not found: {sprint_id}")
    return _json_result(asdict(sprint))


async def create_epic_handler(
    args: dict[str, Any], backend: WorkflowBackend
) -> dict[str, Any]:
    """Create a new epic from title and description."""
    title = args["title"]
    description = args["description"]
    epic = await backend.create_epic(title, description)
    return _json_result({"created": asdict(epic)})


async def create_sprint_handler(
    args: dict[str, Any], backend: WorkflowBackend
) -> dict[str, Any]:
    """Create a new sprint within an epic.

    Tasks, dependencies, and deliverables are passed as JSON strings
    to work within MCP's simple schema system.
    """
    epic_id = args["epic_id"]
    goal = args["goal"]

    # Parse JSON strings for complex fields
    tasks_raw = args.get("tasks", "[]")
    deps_raw = args.get("dependencies", "[]")
    deliverables_raw = args.get("deliverables", "[]")

    try:
        tasks = json.loads(tasks_raw) if isinstance(tasks_raw, str) else tasks_raw
    except json.JSONDecodeError:
        tasks = [{"name": tasks_raw}]

    try:
        dependencies = json.loads(deps_raw) if isinstance(deps_raw, str) else deps_raw
    except json.JSONDecodeError:
        dependencies = []

    try:
        deliverables = json.loads(deliverables_raw) if isinstance(deliverables_raw, str) else deliverables_raw
    except json.JSONDecodeError:
        deliverables = [deliverables_raw]

    try:
        sprint = await backend.create_sprint(
            epic_id=epic_id,
            goal=goal,
            tasks=tasks,
            dependencies=dependencies,
            deliverables=deliverables,
        )
    except KeyError:
        return _text_result(f"Error: Epic not found: {epic_id}")

    return _json_result({"created": asdict(sprint)})
