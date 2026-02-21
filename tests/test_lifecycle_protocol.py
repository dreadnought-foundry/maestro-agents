"""TDD tests for Sprint 10: Lifecycle Protocol Methods."""

import pytest

from src.workflow.exceptions import InvalidTransitionError
from src.workflow.models import SprintStatus
from src.workflow.transitions import VALID_TRANSITIONS, validate_transition


# ---------------------------------------------------------------------------
# InvalidTransitionError tests
# ---------------------------------------------------------------------------


class TestInvalidTransitionError:
    """Tests for the InvalidTransitionError exception."""

    def test_is_exception(self):
        err = InvalidTransitionError("s1", SprintStatus.TODO, SprintStatus.DONE)
        assert isinstance(err, Exception)

    def test_attributes(self):
        err = InvalidTransitionError("s1", SprintStatus.TODO, SprintStatus.DONE)
        assert err.sprint_id == "s1"
        assert err.from_status == SprintStatus.TODO
        assert err.to_status == SprintStatus.DONE

    def test_message_format(self):
        err = InvalidTransitionError("sprint-42", SprintStatus.DONE, SprintStatus.IN_PROGRESS)
        msg = str(err)
        assert "sprint-42" in msg
        assert "done" in msg
        assert "in_progress" in msg


# ---------------------------------------------------------------------------
# Transition data-structure tests
# ---------------------------------------------------------------------------


class TestTransitionDataStructure:
    """Ensure transitions are defined as data, not logic."""

    def test_is_set_or_frozenset(self):
        assert isinstance(VALID_TRANSITIONS, (set, frozenset))

    def test_contains_tuples_of_sprint_status(self):
        for from_s, to_s in VALID_TRANSITIONS:
            assert isinstance(from_s, SprintStatus)
            assert isinstance(to_s, SprintStatus)

    def test_expected_count(self):
        # 11 valid transitions: original 8 + 3 REVIEW transitions
        assert len(VALID_TRANSITIONS) == 11


# ---------------------------------------------------------------------------
# Valid transitions
# ---------------------------------------------------------------------------


class TestValidTransitions:
    """Each valid pair should not raise."""

    @pytest.mark.parametrize(
        "from_status, to_status",
        [
            (SprintStatus.TODO, SprintStatus.IN_PROGRESS),
            (SprintStatus.IN_PROGRESS, SprintStatus.DONE),
            (SprintStatus.IN_PROGRESS, SprintStatus.BLOCKED),
            (SprintStatus.BLOCKED, SprintStatus.IN_PROGRESS),
            (SprintStatus.BACKLOG, SprintStatus.TODO),
            (SprintStatus.TODO, SprintStatus.BACKLOG),
            (SprintStatus.DONE, SprintStatus.ARCHIVED),
            (SprintStatus.ABANDONED, SprintStatus.ARCHIVED),
            (SprintStatus.IN_PROGRESS, SprintStatus.REVIEW),
            (SprintStatus.REVIEW, SprintStatus.DONE),
            (SprintStatus.REVIEW, SprintStatus.IN_PROGRESS),
        ],
    )
    def test_valid_transition_does_not_raise(self, from_status, to_status):
        # Should not raise
        validate_transition("s1", from_status, to_status)


# ---------------------------------------------------------------------------
# Invalid transitions
# ---------------------------------------------------------------------------


class TestInvalidTransitions:
    """Invalid pairs must raise InvalidTransitionError."""

    @pytest.mark.parametrize(
        "from_status, to_status",
        [
            (SprintStatus.DONE, SprintStatus.IN_PROGRESS),
            (SprintStatus.TODO, SprintStatus.DONE),
            (SprintStatus.TODO, SprintStatus.BLOCKED),
            (SprintStatus.BACKLOG, SprintStatus.DONE),
            (SprintStatus.ARCHIVED, SprintStatus.TODO),
            (SprintStatus.BLOCKED, SprintStatus.DONE),
        ],
    )
    def test_invalid_transition_raises(self, from_status, to_status):
        with pytest.raises(InvalidTransitionError) as exc_info:
            validate_transition("s1", from_status, to_status)
        assert exc_info.value.from_status == from_status
        assert exc_info.value.to_status == to_status


# ---------------------------------------------------------------------------
# Protocol has new methods
# ---------------------------------------------------------------------------


class TestProtocolNewMethods:
    """Verify WorkflowBackend protocol exposes the new lifecycle methods."""

    def test_has_start_sprint(self):
        from src.workflow.interface import WorkflowBackend

        assert hasattr(WorkflowBackend, "start_sprint")

    def test_has_advance_step(self):
        from src.workflow.interface import WorkflowBackend

        assert hasattr(WorkflowBackend, "advance_step")

    def test_has_complete_sprint(self):
        from src.workflow.interface import WorkflowBackend

        assert hasattr(WorkflowBackend, "complete_sprint")

    def test_has_block_sprint(self):
        from src.workflow.interface import WorkflowBackend

        assert hasattr(WorkflowBackend, "block_sprint")

    def test_has_get_step_status(self):
        from src.workflow.interface import WorkflowBackend

        assert hasattr(WorkflowBackend, "get_step_status")
