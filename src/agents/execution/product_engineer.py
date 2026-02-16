"""Product engineer execution agent using claude-agent-sdk."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from src.agents.execution.types import AgentResult, StepContext

if TYPE_CHECKING:
    from src.agents.execution.claude_code import ClaudeCodeExecutor


class ProductEngineerAgent:
    """Execution agent that writes and modifies code via claude-agent-sdk."""

    name: str = "product_engineer"
    description: str = "Writes and modifies code based on step requirements"

    ALLOWED_TOOLS = [
        "Read", "Write", "Edit", "Bash", "Glob", "Grep",
    ]

    def __init__(
        self,
        model: str = "sonnet",
        executor: ClaudeCodeExecutor | None = None,
    ) -> None:
        self._model = model
        self._executor = executor

    async def execute(self, context: StepContext) -> AgentResult:
        prompt = self._build_prompt(context)
        try:
            result = await self._run_claude(prompt, context.project_root)
            return result
        except Exception as e:
            return AgentResult(
                success=False,
                output=f"Agent execution failed: {e}",
            )

    def _build_prompt(self, context: StepContext) -> str:
        """Build a focused prompt from the step context."""
        parts = [
            f"You are working on: {context.sprint.goal}",
            f"Current step: {context.step.name}",
            f"Epic: {context.epic.title} - {context.epic.description}",
        ]
        if context.previous_outputs:
            parts.append(f"Previous steps completed: {len(context.previous_outputs)}")
        if context.sprint.deliverables:
            parts.append(f"Expected deliverables: {', '.join(context.sprint.deliverables)}")
        if context.cumulative_deferred:
            parts.append(
                "\n## Deferred Items (from prior sprints)\n"
                "Check if any of these overlap with your current work. "
                "If you can address any, do so. Otherwise note them as still deferred.\n\n"
                f"{context.cumulative_deferred}"
            )
        if context.cumulative_postmortem:
            parts.append(
                "\n## Lessons Learned (from prior sprints)\n"
                "Apply these lessons to your current work. "
                "Avoid repeating past mistakes.\n\n"
                f"{context.cumulative_postmortem}"
            )
        return "\n".join(parts)

    async def _run_claude(self, prompt: str, project_root: Path) -> AgentResult:
        """Run via claude-agent-sdk. Separated for testability."""
        if self._executor is None:
            raise RuntimeError(
                "No ClaudeCodeExecutor provided. "
                "Pass executor= to the constructor for real execution."
            )
        return await self._executor.run(
            prompt=prompt,
            working_dir=project_root,
            allowed_tools=self.ALLOWED_TOOLS,
        )
