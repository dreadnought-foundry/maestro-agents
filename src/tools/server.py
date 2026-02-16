"""MCP server factory binding handlers to a workflow backend."""

from pathlib import Path
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from ..kanban import handlers as kanban_handlers
from ..workflow.interface import WorkflowBackend
from . import handlers


def create_workflow_server(backend: WorkflowBackend, kanban_dir: Path | None = None):
    """Create an MCP server with workflow + kanban tools.

    Each handler is bound to its dependency via closure so the @tool wrappers
    are clean single-argument async functions as the SDK expects.
    """

    # --- Workflow tools (backend-powered) ---

    @tool(
        "get_project_status",
        "Get overall project status: epic count, sprint count, progress percentage",
        {},
    )
    async def get_project_status(args: dict[str, Any]) -> dict[str, Any]:
        return await handlers.get_project_status_handler(args, backend)

    @tool(
        "list_epics",
        "List all epics in the project with their status and sprint IDs",
        {},
    )
    async def list_epics(args: dict[str, Any]) -> dict[str, Any]:
        return await handlers.list_epics_handler(args, backend)

    @tool(
        "get_epic",
        "Get details of a specific epic by ID",
        {"epic_id": str},
    )
    async def get_epic(args: dict[str, Any]) -> dict[str, Any]:
        return await handlers.get_epic_handler(args, backend)

    @tool(
        "list_sprints",
        "List sprints, optionally filtered by epic_id. Omit epic_id to list all.",
        {"epic_id": str},
    )
    async def list_sprints(args: dict[str, Any]) -> dict[str, Any]:
        return await handlers.list_sprints_handler(args, backend)

    @tool(
        "get_sprint",
        "Get full sprint specification including tasks, dependencies, and deliverables",
        {"sprint_id": str},
    )
    async def get_sprint(args: dict[str, Any]) -> dict[str, Any]:
        return await handlers.get_sprint_handler(args, backend)

    @tool(
        "create_epic",
        "Create a new epic with a title and description",
        {"title": str, "description": str},
    )
    async def create_epic(args: dict[str, Any]) -> dict[str, Any]:
        return await handlers.create_epic_handler(args, backend)

    @tool(
        "create_sprint",
        "Create a new sprint within an epic. Tasks, dependencies, and deliverables are JSON strings.",
        {"epic_id": str, "goal": str, "tasks": str, "dependencies": str, "deliverables": str},
    )
    async def create_sprint(args: dict[str, Any]) -> dict[str, Any]:
        return await handlers.create_sprint_handler(args, backend)

    # --- Kanban board tools (filesystem-powered) ---

    all_tools = [
        get_project_status,
        list_epics,
        get_epic,
        list_sprints,
        get_sprint,
        create_epic,
        create_sprint,
    ]

    if kanban_dir:
        @tool(
            "get_board_status",
            "Get kanban board overview: all epics with sprint counts, status breakdown, next IDs",
            {},
        )
        async def get_board_status(args: dict[str, Any]) -> dict[str, Any]:
            return await kanban_handlers.get_board_status_handler(args, kanban_dir)

        @tool(
            "get_board_epic",
            "Get epic detail from the kanban board with all its sprints",
            {"epic_number": str},
        )
        async def get_board_epic(args: dict[str, Any]) -> dict[str, Any]:
            return await kanban_handlers.get_board_epic_handler(args, kanban_dir)

        @tool(
            "get_board_sprint",
            "Get sprint detail from the kanban board including the full spec content",
            {"sprint_number": str},
        )
        async def get_board_sprint(args: dict[str, Any]) -> dict[str, Any]:
            return await kanban_handlers.get_board_sprint_handler(args, kanban_dir)

        @tool(
            "list_board_sprints",
            "List sprints from the kanban board. Filter by status (todo, in-progress, done, blocked) and/or epic_number.",
            {"status": str, "epic_number": str},
        )
        async def list_board_sprints(args: dict[str, Any]) -> dict[str, Any]:
            return await kanban_handlers.list_board_sprints_handler(args, kanban_dir)

        all_tools.extend([
            get_board_status,
            get_board_epic,
            get_board_sprint,
            list_board_sprints,
        ])

    return create_sdk_mcp_server(
        name="maestro_workflow",
        version="0.2.0",
        tools=all_tools,
    )
