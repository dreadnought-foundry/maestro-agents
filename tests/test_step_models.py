"""Tests for step-level models (Sprint 01: Step Models and Status Tracking).

TDD: these tests are written BEFORE the implementation.
"""

from datetime import datetime

import pytest

from src.workflow.models import (
    Sprint,
    SprintStatus,
    SprintTransition,
    Step,
    StepStatus,
)


class TestStepStatus:
    def test_all_values(self):
        assert StepStatus.TODO.value == "todo"
        assert StepStatus.IN_PROGRESS.value == "in_progress"
        assert StepStatus.DONE.value == "done"
        assert StepStatus.BLOCKED.value == "blocked"
        assert StepStatus.FAILED.value == "failed"
        assert StepStatus.SKIPPED.value == "skipped"

    def test_from_value(self):
        assert StepStatus("todo") is StepStatus.TODO
        assert StepStatus("failed") is StepStatus.FAILED

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            StepStatus("nonexistent")


class TestStep:
    def test_required_fields(self):
        step = Step(id="step-1", name="Write tests")
        assert step.id == "step-1"
        assert step.name == "Write tests"

    def test_defaults(self):
        step = Step(id="step-1", name="Write tests")
        assert step.status is StepStatus.TODO
        assert step.agent is None
        assert step.output is None
        assert step.started_at is None
        assert step.completed_at is None
        assert step.metadata == {}

    def test_with_all_fields(self):
        now = datetime.now()
        step = Step(
            id="step-1",
            name="Run pytest",
            status=StepStatus.DONE,
            agent="test_runner",
            output={"passed": 10, "failed": 0},
            started_at=now,
            completed_at=now,
            metadata={"retries": 0},
        )
        assert step.status is StepStatus.DONE
        assert step.agent == "test_runner"
        assert step.output["passed"] == 10
        assert step.started_at == now
        assert step.metadata["retries"] == 0

    def test_output_is_none_by_default_not_shared(self):
        """Ensure metadata default factory creates independent dicts."""
        s1 = Step(id="s1", name="a")
        s2 = Step(id="s2", name="b")
        s1.metadata["key"] = "val"
        assert "key" not in s2.metadata


class TestSprintTransition:
    def test_required_fields(self):
        now = datetime.now()
        t = SprintTransition(
            from_status=SprintStatus.TODO,
            to_status=SprintStatus.IN_PROGRESS,
            timestamp=now,
        )
        assert t.from_status is SprintStatus.TODO
        assert t.to_status is SprintStatus.IN_PROGRESS
        assert t.timestamp == now

    def test_reason_default(self):
        t = SprintTransition(
            from_status=SprintStatus.TODO,
            to_status=SprintStatus.IN_PROGRESS,
            timestamp=datetime.now(),
        )
        assert t.reason is None

    def test_with_reason(self):
        t = SprintTransition(
            from_status=SprintStatus.IN_PROGRESS,
            to_status=SprintStatus.BLOCKED,
            timestamp=datetime.now(),
            reason="Waiting for API access",
        )
        assert t.reason == "Waiting for API access"


class TestSprintWithSteps:
    def test_steps_default_empty(self):
        s = Sprint(id="s-1", goal="x", status=SprintStatus.TODO, epic_id="e-1")
        assert s.steps == []

    def test_transitions_default_empty(self):
        s = Sprint(id="s-1", goal="x", status=SprintStatus.TODO, epic_id="e-1")
        assert s.transitions == []

    def test_sprint_with_steps(self):
        steps = [
            Step(id="step-1", name="Write tests"),
            Step(id="step-2", name="Implement", agent="product_engineer"),
        ]
        s = Sprint(
            id="s-1", goal="Build auth", status=SprintStatus.IN_PROGRESS,
            epic_id="e-1", steps=steps,
        )
        assert len(s.steps) == 2
        assert s.steps[0].name == "Write tests"
        assert s.steps[1].agent == "product_engineer"

    def test_sprint_with_transitions(self):
        now = datetime.now()
        transitions = [
            SprintTransition(
                from_status=SprintStatus.TODO,
                to_status=SprintStatus.IN_PROGRESS,
                timestamp=now,
            ),
        ]
        s = Sprint(
            id="s-1", goal="x", status=SprintStatus.IN_PROGRESS,
            epic_id="e-1", transitions=transitions,
        )
        assert len(s.transitions) == 1
        assert s.transitions[0].to_status is SprintStatus.IN_PROGRESS

    def test_backward_compatible_no_steps(self):
        """Existing Sprint creation without steps/transitions still works."""
        s = Sprint(
            id="s-1", goal="Build auth", status=SprintStatus.TODO,
            epic_id="e-1", tasks=[{"name": "Design schema"}],
            dependencies=["s-0"], deliverables=["auth module"],
            metadata={"type": "backend"},
        )
        assert s.tasks == [{"name": "Design schema"}]
        assert s.steps == []
        assert s.transitions == []
