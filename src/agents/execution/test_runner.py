"""Test runner execution agent that runs pytest and reports results."""

from __future__ import annotations

import re
from pathlib import Path

from src.agents.execution.types import AgentResult, StepContext


class TestRunnerAgent:
    """Execution agent that runs pytest and reports results."""

    name: str = "test_runner"
    description: str = "Runs pytest and reports test results with coverage"

    def __init__(self, test_command: str = "pytest") -> None:
        self._test_command = test_command

    async def execute(self, context: StepContext) -> AgentResult:
        try:
            result = await self._run_tests(context.project_root)
            return result
        except Exception as e:
            return AgentResult(
                success=False,
                output=f"Test execution failed: {e}",
            )

    def _build_command(self, project_root: Path) -> str:
        """Build the pytest command with appropriate flags."""
        return f"{self._test_command} {project_root} -v --tb=short"

    def _parse_results(self, stdout: str, returncode: int) -> AgentResult:
        """Parse pytest output into structured AgentResult."""
        test_results: dict = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "failed_tests": [],
        }

        lines = stdout.strip().split("\n")
        for line in lines:
            # Parse summary line like "5 passed" or "3 passed, 2 failed in 0.55s"
            if "passed" in line and ("failed" in line or "error" in line or "=" in line):
                passed_match = re.search(r"(\d+) passed", line)
                failed_match = re.search(r"(\d+) failed", line)
                error_match = re.search(r"(\d+) error", line)
                if passed_match:
                    test_results["passed"] = int(passed_match.group(1))
                if failed_match:
                    test_results["failed"] = int(failed_match.group(1))
                if error_match:
                    test_results["errors"] = int(error_match.group(1))

            # Parse "FAILED test_name" lines
            if line.strip().startswith("FAILED"):
                test_name = line.strip().replace("FAILED ", "").split(" ")[0]
                test_results["failed_tests"].append(test_name)

        test_results["total"] = (
            test_results["passed"] + test_results["failed"] + test_results["errors"]
        )

        # Parse coverage if present
        coverage: float | None = None
        for line in lines:
            if "TOTAL" in line and "%" in line:
                cov_match = re.search(r"(\d+)%", line)
                if cov_match:
                    coverage = float(cov_match.group(1))

        success = returncode == 0

        return AgentResult(
            success=success,
            output=stdout,
            test_results=test_results,
            coverage=coverage,
        )

    async def _run_tests(self, project_root: Path) -> AgentResult:
        """Run pytest. Separated for testability."""
        raise NotImplementedError("Real test execution requires subprocess access")
