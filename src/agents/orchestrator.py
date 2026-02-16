"""Maestro v2 orchestrator — entry point for the agent system."""

import asyncio
import os
import sys
from pathlib import Path

os.environ.pop("CLAUDECODE", None)

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient

from ..adapters.maestro import MaestroAdapter
from ..tools.server import create_workflow_server
from .definitions import ALL_AGENTS, ALL_TOOLS


async def run_orchestrator(
    user_request: str,
    project_root: str | Path | None = None,
):
    """Run the maestro orchestrator on a user request.

    Args:
        user_request: What the user wants done.
        project_root: Path to the project. Defaults to cwd.
    """
    root = Path(project_root) if project_root else Path.cwd()
    backend = MaestroAdapter(root)
    kanban_dir = root / "kanban"
    workflow_server = create_workflow_server(
        backend, kanban_dir=kanban_dir if kanban_dir.exists() else None
    )

    options = ClaudeAgentOptions(
        system_prompt=(
            "You are Maestro, a universal project workflow assistant. "
            "You help plan and manage projects of any type — coding, research, "
            "marketing, design, devops, business analysis.\n\n"
            "You have four specialized agents you can delegate to:\n"
            "- epic_breakdown: Break big ideas into epics and sprints\n"
            "- sprint_spec: Write detailed sprint specifications\n"
            "- research: Conduct market or technical research\n"
            "- status_report: Generate project progress reports\n\n"
            "Analyze the user's request and delegate to the right agent. "
            "If the request spans multiple agents, use them in sequence. "
            "You can also use the workflow tools directly for simple queries."
        ),
        agents=ALL_AGENTS,
        mcp_servers={"maestro": workflow_server},
        allowed_tools=[*ALL_TOOLS, "Task", "Read", "Glob"],
        permission_mode="acceptEdits",
        max_turns=15,
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(user_request)
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if hasattr(block, "text"):
                        print(block.text)
                    elif hasattr(block, "name"):
                        print(f"  [agent/tool: {block.name}]")


def main():
    """CLI entry point."""
    if len(sys.argv) > 1:
        request = " ".join(sys.argv[1:])
    else:
        request = "What's the current project status?"
    asyncio.run(run_orchestrator(request))


if __name__ == "__main__":
    main()
