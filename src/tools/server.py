"""MCP server factory binding handlers to a workflow backend."""

from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from ..workflow.interface import WorkflowBackend
from . import handlers


def create_workflow_server(backend: WorkflowBackend):
    """Create an MCP server with all workflow tools bound to the given backend.

    Each handler is bound to the backend via closure so the @tool wrappers
    are clean single-argument async functions as the SDK expects.
    """

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

    return create_sdk_mcp_server(
        name="maestro_workflow",
        version="0.1.0",
        tools=[
            get_project_status,
            list_epics,
            get_epic,
            list_sprints,
            get_sprint,
            create_epic,
            create_sprint,
        ],
    )
