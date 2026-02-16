"""Example 2: Custom tools via MCP.

Define your own tools that Claude can call. This is how you'd expose
workflow capabilities (sprint status, epic management, etc.) to an agent.
"""

import asyncio
import os
from typing import Any

os.environ.pop("CLAUDECODE", None)

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    create_sdk_mcp_server,
    tool,
)


# --- Core logic (testable without the SDK) ---


async def get_team_members_handler(args: dict[str, Any]) -> dict[str, Any]:
    """Return list of team members and their roles."""
    # In a real integration, this would pull from your team database
    members = [
        {"name": "Alice", "role": "backend"},
        {"name": "Bob", "role": "frontend"},
        {"name": "Carol", "role": "devops"},
    ]
    return {"content": [{"type": "text", "text": str(members)}]}


async def assign_task_handler(args: dict[str, Any]) -> dict[str, Any]:
    """Assign a task to a team member."""
    member = args["member"]
    task = args["task"]
    priority = args.get("priority", "medium")
    return {
        "content": [
            {
                "type": "text",
                "text": f"Assigned '{task}' to {member} (priority: {priority})",
            }
        ]
    }


# --- Tool wrappers (these register the handlers with the SDK) ---

get_team_members = tool(
    "get_team_members", "Get list of team members and their roles", {}
)(get_team_members_handler)

assign_task = tool(
    "assign_task",
    "Assign a task to a team member",
    {"member": str, "task": str, "priority": str},
)(assign_task_handler)


async def main():
    server = create_sdk_mcp_server(
        name="team_tools",
        version="0.1.0",
        tools=[get_team_members, assign_task],
    )

    options = ClaudeAgentOptions(
        mcp_servers={"team": server},
        allowed_tools=[
            "mcp__team__get_team_members",
            "mcp__team__assign_task",
        ],
        permission_mode="acceptEdits",
        max_turns=5,
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(
            "Get the team members and assign code review of the auth module "
            "to the backend developer with high priority."
        )

        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if hasattr(block, "text"):
                        print(block.text)
                    elif hasattr(block, "name"):
                        print(f"  [tool: {block.name}]")


if __name__ == "__main__":
    asyncio.run(main())
