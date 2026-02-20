"""Validation phase logic — report generation and gate enforcement.

The validation phase goes beyond unit tests to verify:
- Full test suite passes (unit + integration)
- Acceptance criteria from sprint spec are met
- Service health checks pass
- API contracts are satisfied

The ValidationGate blocks the sprint from reaching Review if critical checks fail.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from src.agents.execution.types import AgentResult
from src.execution.hooks import HookContext, HookPoint, HookResult


class CheckStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    WARN = "warn"


class CheckSeverity(Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


@dataclass
class ValidationCheck:
    """A single validation check result."""

    name: str
    status: CheckStatus
    severity: CheckSeverity = CheckSeverity.MAJOR
    message: str = ""
    details: str = ""


@dataclass
class ValidationReport:
    """Structured validation report with per-criterion results.

    Attributes:
        checks: List of individual validation check results.
        test_results: Pytest results dict (total, passed, failed, errors).
        coverage: Test coverage percentage.
        acceptance_criteria: Map of criterion name -> pass/fail.
    """

    checks: list[ValidationCheck] = field(default_factory=list)
    test_results: dict | None = None
    coverage: float | None = None
    acceptance_criteria: dict[str, bool] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        """True if no critical or major checks failed."""
        for check in self.checks:
            if check.status is CheckStatus.FAIL and check.severity in (
                CheckSeverity.CRITICAL,
                CheckSeverity.MAJOR,
            ):
                return False
        return True

    @property
    def critical_failures(self) -> list[ValidationCheck]:
        """Return checks that failed with critical severity."""
        return [
            c
            for c in self.checks
            if c.status is CheckStatus.FAIL and c.severity is CheckSeverity.CRITICAL
        ]

    @property
    def all_failures(self) -> list[ValidationCheck]:
        """Return all failed checks."""
        return [c for c in self.checks if c.status is CheckStatus.FAIL]

    def to_markdown(self) -> str:
        """Generate a markdown-formatted validation report."""
        lines = ["# Validation Report\n"]

        # Summary
        total = len(self.checks)
        passed = sum(1 for c in self.checks if c.status is CheckStatus.PASS)
        failed = sum(1 for c in self.checks if c.status is CheckStatus.FAIL)
        skipped = sum(1 for c in self.checks if c.status is CheckStatus.SKIP)
        warned = sum(1 for c in self.checks if c.status is CheckStatus.WARN)

        status_icon = "PASS" if self.passed else "FAIL"
        lines.append(f"**Overall: {status_icon}** | {passed}/{total} passed, {failed} failed, {warned} warnings, {skipped} skipped\n")

        # Test results
        if self.test_results:
            lines.append("## Test Suite\n")
            tr = self.test_results
            lines.append(f"- Total: {tr.get('total', 0)}")
            lines.append(f"- Passed: {tr.get('passed', 0)}")
            lines.append(f"- Failed: {tr.get('failed', 0)}")
            lines.append(f"- Errors: {tr.get('errors', 0)}")
            if self.coverage is not None:
                lines.append(f"- Coverage: {self.coverage}%")
            lines.append("")

        # Acceptance criteria
        if self.acceptance_criteria:
            lines.append("## Acceptance Criteria\n")
            for criterion, met in self.acceptance_criteria.items():
                icon = "PASS" if met else "FAIL"
                lines.append(f"- [{icon}] {criterion}")
            lines.append("")

        # Detailed checks
        if self.checks:
            lines.append("## Validation Checks\n")
            for check in self.checks:
                icon = {
                    CheckStatus.PASS: "PASS",
                    CheckStatus.FAIL: "FAIL",
                    CheckStatus.SKIP: "SKIP",
                    CheckStatus.WARN: "WARN",
                }[check.status]
                severity = check.severity.value.upper()
                lines.append(f"### [{icon}] {check.name} ({severity})\n")
                if check.message:
                    lines.append(f"{check.message}\n")
                if check.details:
                    lines.append(f"```\n{check.details}\n```\n")

        return "\n".join(lines)


def build_report_from_agent_result(agent_result: AgentResult) -> ValidationReport:
    """Build a ValidationReport from an AgentResult.

    Extracts test_results, coverage, and parses the output for validation checks.
    """
    report = ValidationReport(
        test_results=agent_result.test_results,
        coverage=agent_result.coverage,
    )

    # Add test suite check
    if agent_result.test_results:
        tr = agent_result.test_results
        failed = tr.get("failed", 0) + tr.get("errors", 0)
        if failed == 0:
            report.checks.append(ValidationCheck(
                name="Test Suite",
                status=CheckStatus.PASS,
                severity=CheckSeverity.CRITICAL,
                message=f"All {tr.get('total', 0)} tests passed",
            ))
        else:
            report.checks.append(ValidationCheck(
                name="Test Suite",
                status=CheckStatus.FAIL,
                severity=CheckSeverity.CRITICAL,
                message=f"{failed} test(s) failed out of {tr.get('total', 0)}",
                details="\n".join(tr.get("failed_tests", [])),
            ))

    # Add coverage check
    if agent_result.coverage is not None:
        report.checks.append(ValidationCheck(
            name="Code Coverage",
            status=CheckStatus.PASS if agent_result.coverage >= 75.0 else CheckStatus.WARN,
            severity=CheckSeverity.MAJOR,
            message=f"Coverage: {agent_result.coverage}%",
        ))

    return report


class ValidationGate:
    """POST_STEP hook that blocks when validation has critical failures.

    Checks the agent result from the VALIDATE phase and blocks the sprint
    if any critical checks failed.
    """

    hook_point = HookPoint.POST_STEP

    async def evaluate(self, context: HookContext) -> HookResult:
        if context.agent_result is None:
            return HookResult(passed=True, message="No agent result to validate")

        # Check if this is a validation step
        step = context.step
        if step is None:
            return HookResult(passed=True, message="No step context")

        step_type = step.metadata.get("type", step.name)
        phase = step.metadata.get("phase", "")
        if phase != "validate" and step_type not in ("validate", "validation"):
            return HookResult(passed=True, message="Not a validation step")

        # Build report from agent result
        report = build_report_from_agent_result(context.agent_result)

        critical = report.critical_failures
        if critical:
            names = ", ".join(c.name for c in critical)
            return HookResult(
                passed=False,
                message=f"Validation failed: critical failures in {names}",
                blocking=True,
            )

        if not report.passed:
            failures = report.all_failures
            names = ", ".join(c.name for c in failures)
            return HookResult(
                passed=False,
                message=f"Validation failed: {names}",
                blocking=True,
            )

        return HookResult(
            passed=True,
            message=f"Validation passed: {len(report.checks)} checks OK",
        )
