"""Concrete enforcement gates implementing the Hook protocol."""

from __future__ import annotations

from src.agents.execution.types import AgentResult
from src.execution.hooks import Hook, HookContext, HookPoint, HookResult
from src.workflow.models import Sprint, Step, StepStatus


# Coverage thresholds by sprint type
COVERAGE_THRESHOLDS: dict[str, float] = {
    "backend": 85.0,
    "frontend": 70.0,
    "fullstack": 75.0,
    "infrastructure": 60.0,
    "research": 0.0,
}


class CoverageGate:
    """POST_STEP hook -- checks AgentResult.coverage >= threshold."""

    hook_point = HookPoint.POST_STEP

    def __init__(self, threshold: float = 80.0):
        self.threshold = threshold

    async def evaluate(self, context: HookContext) -> HookResult:
        if context.agent_result is None:
            return HookResult(passed=True, message="No agent result to check")

        coverage = context.agent_result.coverage
        if coverage is None:
            # No coverage data -- pass (test runner may not have been the step)
            return HookResult(passed=True, message="No coverage data reported")

        if coverage >= self.threshold:
            return HookResult(
                passed=True,
                message=f"Coverage {coverage}% meets threshold {self.threshold}%",
            )
        return HookResult(
            passed=False,
            message=f"Coverage {coverage}% below threshold {self.threshold}%",
            blocking=True,
        )


class QualityReviewGate:
    """PRE_COMPLETION hook -- checks that a quality review approved the work."""

    hook_point = HookPoint.PRE_COMPLETION

    async def evaluate(self, context: HookContext) -> HookResult:
        # Look through run_state for review verdicts
        # The runner should store agent results in run_state["agent_results"]
        agent_results = context.run_state.get("agent_results", [])

        # Find the latest review verdict
        review_verdict = None
        for result in agent_results:
            if isinstance(result, AgentResult) and result.review_verdict:
                review_verdict = result.review_verdict

        if review_verdict is None:
            return HookResult(
                passed=False,
                message="No quality review found",
                blocking=True,
            )

        if review_verdict == "approve":
            return HookResult(passed=True, message="Quality review approved")

        return HookResult(
            passed=False,
            message=f"Quality review verdict: {review_verdict}",
            blocking=True,
        )


class StepOrderingGate:
    """PRE_STEP hook -- validates that preceding steps are complete."""

    hook_point = HookPoint.PRE_STEP

    async def evaluate(self, context: HookContext) -> HookResult:
        if context.step is None:
            return HookResult(passed=True, message="No step to validate")

        sprint = context.sprint
        for step in sprint.steps:
            if step.id == context.step.id:
                # All preceding steps are done
                return HookResult(passed=True, message="Step ordering valid")
            if step.status not in (StepStatus.DONE, StepStatus.SKIPPED):
                return HookResult(
                    passed=False,
                    message=f"Preceding step '{step.name}' not complete (status: {step.status.value})",
                    blocking=True,
                )

        return HookResult(passed=False, message="Step not found in sprint", blocking=True)


class RequiredStepsGate:
    """PRE_COMPLETION hook -- validates all required steps are done."""

    hook_point = HookPoint.PRE_COMPLETION

    def __init__(self, required_step_names: list[str] | None = None):
        self._required = required_step_names  # None means ALL steps required

    async def evaluate(self, context: HookContext) -> HookResult:
        sprint = context.sprint
        missing = []

        for step in sprint.steps:
            if self._required is not None and step.name not in self._required:
                continue
            if step.status not in (StepStatus.DONE, StepStatus.SKIPPED):
                missing.append(step.name)

        if not missing:
            return HookResult(passed=True, message="All required steps complete")

        return HookResult(
            passed=False,
            message=f"Incomplete steps: {', '.join(missing)}",
            blocking=True,
            deferred_items=[f"Complete step: {name}" for name in missing],
        )


def create_default_hooks(sprint_type: str = "backend") -> list:
    """Create a sensible set of default hooks for a sprint type.

    Returns a list of hook instances ready to register.
    """
    threshold = COVERAGE_THRESHOLDS.get(sprint_type, 80.0)
    hooks = [
        CoverageGate(threshold=threshold),
        QualityReviewGate(),
        StepOrderingGate(),
        RequiredStepsGate(),
    ]
    return hooks
