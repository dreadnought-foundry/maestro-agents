"""Example 3: Multi-agent workflow.

Define specialized subagents that the orchestrator can delegate to.
This pattern maps directly to maestro's agent architecture — each agent
in maestro/agents/ could become an AgentDefinition here.
"""

import asyncio
import os

os.environ.pop("CLAUDECODE", None)

from claude_agent_sdk import AgentDefinition, AssistantMessage, ClaudeAgentOptions, query


async def main():
    agents = {
        "code_reviewer": AgentDefinition(
            description="Reviews Python code for bugs, style issues, and security concerns",
            prompt=(
                "You are an expert Python code reviewer. "
                "Read the requested files and provide a concise review "
                "focusing on correctness, security, and readability."
            ),
            tools=["Read", "Grep", "Glob"],
            model="sonnet",
        ),
        "test_writer": AgentDefinition(
            description="Writes pytest tests for Python code",
            prompt=(
                "You are a test automation expert. "
                "Write focused pytest tests for the code you're asked about. "
                "Use pytest-asyncio for async code."
            ),
            tools=["Read", "Write", "Glob"],
            model="sonnet",
        ),
    }

    options = ClaudeAgentOptions(
        agents=agents,
        allowed_tools=["Task", "Read", "Glob"],
        permission_mode="acceptEdits",
        max_turns=10,
    )

    print("--- Multi-agent: review + test the examples ---\n")

    async for message in query(
        prompt=(
            "1. Use the code_reviewer agent to review examples/01_simple_query.py\n"
            "2. Use the test_writer agent to write a basic test for the custom tools "
            "in examples/02_custom_tools.py (just test the tool functions directly)"
        ),
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
