"""Example 1: Simple one-shot query.

The simplest way to use the Agent SDK — send a prompt, stream the response.
"""

import asyncio
import os

# Allow running from inside a Claude Code session (e.g. during development).
# The SDK blocks nested sessions by default — this unsets the guard variable.
os.environ.pop("CLAUDECODE", None)

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, query


async def main():
    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Glob"],
        permission_mode="acceptEdits",
        max_turns=6,
    )

    print("--- Asking Claude to list Python files in this project ---\n")

    async for message in query(
        prompt="List all Python files in this project (exclude .venv/) and briefly describe what each one does.",
        options=options,
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text"):
                    print(block.text)
                elif hasattr(block, "name"):
                    print(f"  [tool: {block.name}]")


if __name__ == "__main__":
    asyncio.run(main())
