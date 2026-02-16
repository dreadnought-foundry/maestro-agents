"""Quality Engineer execution agent for code review and acceptance validation."""

from __future__ import annotations

from src.agents.execution.types import AgentResult, StepContext


class QualityEngineerAgent:
    """Execution agent that reviews code and validates against acceptance criteria."""

    name: str = "quality_engineer"
    description: str = "Reviews code changes and validates against acceptance criteria"

    def __init__(self, model: str = "sonnet") -> None:
        self._model = model

    async def execute(self, context: StepContext) -> AgentResult:
        try:
            prompt = self._build_prompt(context)
            result = await self._run_review(prompt, context.project_root)
            return result
        except Exception as e:
            return AgentResult(
                success=False,
                output=f"Quality review failed: {e}",
                review_verdict="error",
            )

    def _build_prompt(self, context: StepContext) -> str:
        """Build review prompt from context."""
        parts = [
            f"Review the work done for: {context.sprint.goal}",
            f"Current step: {context.step.name}",
            f"Epic: {context.epic.title}",
        ]

        # Include previous step results for review
        if context.previous_outputs:
            parts.append(
                f"\nPrevious step results ({len(context.previous_outputs)}):"
            )
            for i, output in enumerate(context.previous_outputs):
                parts.append(
                    f"  Step {i + 1}: {'PASS' if output.success else 'FAIL'}"
                    f" - {output.output[:100]}"
                )
                if output.files_created:
                    parts.append(
                        f"    Files created: {', '.join(output.files_created)}"
                    )
                if output.files_modified:
                    parts.append(
                        f"    Files modified: {', '.join(output.files_modified)}"
                    )

        if context.sprint.deliverables:
            parts.append(
                f"\nExpected deliverables: {', '.join(context.sprint.deliverables)}"
            )

        if context.cumulative_deferred:
            parts.append(
                "\n## Deferred Items (from prior sprints)\n"
                "Check if any deferred items were addressed in this sprint. "
                "Flag any that remain relevant.\n\n"
                f"{context.cumulative_deferred}"
            )
        if context.cumulative_postmortem:
            parts.append(
                "\n## Lessons Learned (from prior sprints)\n"
                "Verify this sprint follows past lessons. "
                "Flag violations of established patterns.\n\n"
                f"{context.cumulative_postmortem}"
            )

        parts.append("\nProvide verdict: 'approve' or 'request_changes'")
        parts.append(
            "List any deferred items or improvements for future sprints."
        )

        return "\n".join(parts)

    async def _run_review(self, prompt: str, project_root: object) -> AgentResult:
        """Run Claude SDK for review. Separated for testability."""
        raise NotImplementedError("Real review requires API access")
