"""Tests for concrete enforcement gates (Sprint 20 — TDD)."""

from __future__ import annotations

import pytest

from src.agents.execution.types import AgentResult
from src.execution.gates import (
    COVERAGE_THRESHOLDS,
    CoverageGate,
    QualityReviewGate,
    RequiredStepsGate,
    StepOrderingGate,
    create_default_hooks,
)
from src.execution.hooks import HookContext, HookPoint
from src.workflow.models import Sprint, SprintStatus, Step, StepStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sprint(steps: list[Step] | None = None) -> Sprint:
    return Sprint(
        id="sp-1",
        goal="Test sprint",
        status=SprintStatus.IN_PROGRESS,
        epic_id="epic-1",
        steps=steps or [],
    )


def _step(id: str = "step-1", name: str = "Step 1", status: StepStatus = StepStatus.TODO) -> Step:
    return Step(id=id, name=name, status=status)


def _agent_result(
    coverage: float | None = None,
    review_verdict: str | None = None,
) -> AgentResult:
    return AgentResult(
        success=True,
        output="ok",
        coverage=coverage,
        review_verdict=review_verdict,
    )


# ===========================================================================
# CoverageGate
# ===========================================================================


class TestCoverageGate:
    async def test_passes_above_threshold(self) -> None:
        gate = CoverageGate(threshold=80.0)
        ctx = HookContext(
            sprint=_sprint(),
            agent_result=_agent_result(coverage=90.0),
        )
        result = await gate.evaluate(ctx)
        assert result.passed is True
        assert "90" in result.message

    async def test_fails_below_threshold(self) -> None:
        gate = CoverageGate(threshold=80.0)
        ctx = HookContext(
            sprint=_sprint(),
            agent_result=_agent_result(coverage=60.0),
        )
        result = await gate.evaluate(ctx)
        assert result.passed is False
        assert result.blocking is True
        assert "60" in result.message

    async def test_passes_no_coverage_data(self) -> None:
        gate = CoverageGate(threshold=80.0)
        ctx = HookContext(
            sprint=_sprint(),
            agent_result=_agent_result(coverage=None),
        )
        result = await gate.evaluate(ctx)
        assert result.passed is True

    async def test_passes_no_agent_result(self) -> None:
        gate = CoverageGate(threshold=80.0)
        ctx = HookContext(sprint=_sprint(), agent_result=None)
        result = await gate.evaluate(ctx)
        assert result.passed is True


# ===========================================================================
# QualityReviewGate
# ===========================================================================


class TestQualityReviewGate:
    async def test_passes_with_approval(self) -> None:
        gate = QualityReviewGate()
        ctx = HookContext(
            sprint=_sprint(),
            run_state={
                "agent_results": [_agent_result(review_verdict="approve")],
            },
        )
        result = await gate.evaluate(ctx)
        assert result.passed is True
        assert "approved" in result.message.lower()

    async def test_fails_with_request_changes(self) -> None:
        gate = QualityReviewGate()
        ctx = HookContext(
            sprint=_sprint(),
            run_state={
                "agent_results": [_agent_result(review_verdict="request_changes")],
            },
        )
        result = await gate.evaluate(ctx)
        assert result.passed is False
        assert result.blocking is True
        assert "request_changes" in result.message

    async def test_fails_with_no_review(self) -> None:
        gate = QualityReviewGate()
        ctx = HookContext(
            sprint=_sprint(),
            run_state={"agent_results": []},
        )
        result = await gate.evaluate(ctx)
        assert result.passed is False
        assert result.blocking is True


# ===========================================================================
# StepOrderingGate
# ===========================================================================


class TestStepOrderingGate:
    async def test_passes_first_step(self) -> None:
        step1 = _step("s1", "First", StepStatus.TODO)
        sprint = _sprint(steps=[step1, _step("s2", "Second")])
        gate = StepOrderingGate()
        ctx = HookContext(sprint=sprint, step=step1)
        result = await gate.evaluate(ctx)
        assert result.passed is True

    async def test_passes_after_done_steps(self) -> None:
        step1 = _step("s1", "First", StepStatus.DONE)
        step2 = _step("s2", "Second", StepStatus.TODO)
        sprint = _sprint(steps=[step1, step2])
        gate = StepOrderingGate()
        ctx = HookContext(sprint=sprint, step=step2)
        result = await gate.evaluate(ctx)
        assert result.passed is True

    async def test_fails_with_incomplete_preceding(self) -> None:
        step1 = _step("s1", "First", StepStatus.TODO)
        step2 = _step("s2", "Second", StepStatus.TODO)
        sprint = _sprint(steps=[step1, step2])
        gate = StepOrderingGate()
        ctx = HookContext(sprint=sprint, step=step2)
        result = await gate.evaluate(ctx)
        assert result.passed is False
        assert result.blocking is True
        assert "First" in result.message


# ===========================================================================
# RequiredStepsGate
# ===========================================================================


class TestRequiredStepsGate:
    async def test_passes_all_done(self) -> None:
        steps = [
            _step("s1", "Build", StepStatus.DONE),
            _step("s2", "Test", StepStatus.DONE),
        ]
        gate = RequiredStepsGate()
        ctx = HookContext(sprint=_sprint(steps=steps))
        result = await gate.evaluate(ctx)
        assert result.passed is True

    async def test_fails_with_missing(self) -> None:
        steps = [
            _step("s1", "Build", StepStatus.DONE),
            _step("s2", "Test", StepStatus.TODO),
        ]
        gate = RequiredStepsGate()
        ctx = HookContext(sprint=_sprint(steps=steps))
        result = await gate.evaluate(ctx)
        assert result.passed is False
        assert "Test" in result.message
        assert len(result.deferred_items) == 1

    async def test_custom_required_list(self) -> None:
        steps = [
            _step("s1", "Build", StepStatus.DONE),
            _step("s2", "Test", StepStatus.TODO),
            _step("s3", "Deploy", StepStatus.TODO),
        ]
        gate = RequiredStepsGate(required_step_names=["Build"])
        ctx = HookContext(sprint=_sprint(steps=steps))
        result = await gate.evaluate(ctx)
        assert result.passed is True


# ===========================================================================
# create_default_hooks
# ===========================================================================


class TestCreateDefaultHooks:
    def test_returns_four_hooks(self) -> None:
        hooks = create_default_hooks()
        assert len(hooks) == 4

    def test_backend_threshold(self) -> None:
        hooks = create_default_hooks("backend")
        coverage_gate = [h for h in hooks if isinstance(h, CoverageGate)][0]
        assert coverage_gate.threshold == 85.0

    def test_research_threshold(self) -> None:
        hooks = create_default_hooks("research")
        coverage_gate = [h for h in hooks if isinstance(h, CoverageGate)][0]
        assert coverage_gate.threshold == 0.0
