"""Validation execution agent — runs comprehensive validation beyond unit tests.

Validates:
- Full test suite (unit + integration)
- Acceptance criteria from sprint spec
- Service health checks
- API endpoint verification against contracts
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.agents.execution.types import AgentResult, StepContext

if TYPE_CHECKING:
    from src.agents.execution.claude_code import ClaudeCodeExecutor


class ValidationAgent:
    """Execution agent that runs comprehensive validation for the VALIDATE phase.

    Goes beyond pytest to verify acceptance criteria, service health,
    and API contracts. Produces structured test_results for downstream gates.
    """

    name: str = "validation_agent"
    description: str = "Runs full validation: tests, acceptance criteria, service health"

    ALLOWED_TOOLS = [
        "Bash", "Read", "Glob", "Grep",
    ]

    def __init__(
        self,
        test_command: str = "pytest",
        executor: ClaudeCodeExecutor | None = None,
    ) -> None:
        self._test_command = test_command
        self._executor = executor

    async def execute(self, context: StepContext) -> AgentResult:
        try:
            prompt = self._build_prompt(context)
            result = await self._run_validation(prompt, context.project_root)
            return result
        except Exception as e:
            return AgentResult(
                success=False,
                output=f"Validation failed: {e}",
            )

    def _build_prompt(self, context: StepContext) -> str:
        """Build validation prompt including acceptance criteria and contracts."""
        parts = [
            "# Validation Phase",
            f"\nSprint goal: {context.sprint.goal}",
            f"Epic: {context.epic.title}",
            "\n## Instructions",
            "",
            "Perform comprehensive validation of the sprint work:",
            "",
            "### 1. Run Full Test Suite",
            f"Run: {self._test_command} -v --tb=short",
            "Report all results including coverage.",
            "",
            "### 2. Check Acceptance Criteria",
            "Verify each acceptance criterion from the sprint spec is met.",
            "For each criterion, report PASS or FAIL with evidence.",
        ]

        # Include acceptance criteria from sprint tasks
        if context.sprint.tasks:
            parts.append("\n### Acceptance Criteria to Verify:\n")
            for task in context.sprint.tasks:
                name = task.get("name", "Unknown")
                parts.append(f"- [ ] {name}")

        if context.sprint.deliverables:
            parts.append(f"\n### Expected Deliverables:\n")
            for d in context.sprint.deliverables:
                parts.append(f"- {d}")

        # Include previous outputs for context
        if context.previous_outputs:
            parts.append(f"\n### Previous Phase Results ({len(context.previous_outputs)}):\n")
            for i, output in enumerate(context.previous_outputs):
                status = "PASS" if output.success else "FAIL"
                parts.append(f"Phase {i + 1}: {status} - {output.output[:200]}")

        # Include planning artifacts if available
        if context.cumulative_deferred:
            parts.append(
                "\n### Deferred Items (check if addressed):\n"
                f"{context.cumulative_deferred}"
            )

        parts.append(
            "\n### Output Format\n"
            "End your response with a structured summary:\n"
            "```\n"
            "VALIDATION_RESULT: PASS or FAIL\n"
            "TESTS_PASSED: <number>\n"
            "TESTS_FAILED: <number>\n"
            "COVERAGE: <percentage>\n"
            "CRITERIA_MET: <number>/<total>\n"
            "```"
        )

        return "\n".join(parts)

    async def _run_validation(self, prompt: str, project_root: object) -> AgentResult:
        """Run validation via claude-agent-sdk."""
        if self._executor is None:
            raise RuntimeError(
                "No ClaudeCodeExecutor provided. "
                "Pass executor= to the constructor for real execution."
            )
        result = await self._executor.run(
            prompt=prompt,
            working_dir=project_root,
            allowed_tools=self.ALLOWED_TOOLS,
        )
        return result
