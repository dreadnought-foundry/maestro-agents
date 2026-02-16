"""Claude Code executor — runs prompts via the claude-agent-sdk."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

# Allow nested invocation from within a Claude Code session.
# The SDK spawns claude CLI which checks for this env var.
# Same pattern as src/agents/orchestrator.py.
os.environ.pop("CLAUDECODE", None)

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

from src.agents.execution.types import AgentResult


class ClaudeCodeExecutor:
    """Executes prompts via the claude-agent-sdk.

    Uses the SDK's query() function which handles subprocess management,
    streaming, error handling, and message parsing internally.
    """

    def __init__(
        self,
        model: str = "sonnet",
        permission_mode: str = "acceptEdits",
        max_turns: int = 25,
    ) -> None:
        self._model = model
        self._permission_mode = permission_mode
        self._max_turns = max_turns

    async def run(
        self,
        prompt: str,
        working_dir: Path,
        timeout: int = 300,
        allowed_tools: list[str] | None = None,
    ) -> AgentResult:
        """Run a prompt through the claude-agent-sdk and return structured result."""
        options = ClaudeAgentOptions(
            model=self._model,
            cwd=working_dir,
            allowed_tools=allowed_tools or [],
            permission_mode=self._permission_mode,
            max_turns=self._max_turns,
        )

        text_parts: list[str] = []
        files_created: list[str] = []
        files_modified: list[str] = []
        is_error = False

        try:
            async with asyncio.timeout(timeout):
                async for message in query(prompt=prompt, options=options):
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                text_parts.append(block.text)
                            elif isinstance(block, ToolUseBlock):
                                self._track_file_ops(
                                    block, files_created, files_modified,
                                )
                    elif isinstance(message, ResultMessage):
                        is_error = message.is_error
                        if message.result:
                            text_parts.append(message.result)

        except TimeoutError:
            return AgentResult(
                success=False,
                output=f"Claude execution timed out after {timeout}s",
            )
        except Exception as e:
            return AgentResult(
                success=False,
                output=f"Claude execution failed: {e}",
            )

        output = "\n".join(text_parts).strip()

        return AgentResult(
            success=not is_error,
            output=output or "(no output)",
            files_created=files_created,
            files_modified=files_modified,
        )

    @staticmethod
    def _track_file_ops(
        block: ToolUseBlock,
        files_created: list[str],
        files_modified: list[str],
    ) -> None:
        """Extract file create/modify info from tool use blocks."""
        tool_input = block.input or {}
        file_path = tool_input.get("file_path", "")
        if not file_path:
            return
        if block.name == "Write" and file_path not in files_created:
            files_created.append(file_path)
        elif block.name == "Edit" and file_path not in files_modified:
            files_modified.append(file_path)
