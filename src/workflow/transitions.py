"""Sprint state-machine transitions defined as data."""

from .exceptions import InvalidTransitionError
from .models import SprintStatus

VALID_TRANSITIONS: frozenset[tuple[SprintStatus, SprintStatus]] = frozenset(
    {
        (SprintStatus.TODO, SprintStatus.IN_PROGRESS),       # start
        (SprintStatus.IN_PROGRESS, SprintStatus.REVIEW),     # submit for review
        (SprintStatus.IN_PROGRESS, SprintStatus.DONE),       # complete (direct)
        (SprintStatus.REVIEW, SprintStatus.DONE),             # approve from review
        (SprintStatus.REVIEW, SprintStatus.IN_PROGRESS),     # reject from review
        (SprintStatus.IN_PROGRESS, SprintStatus.BLOCKED),    # block
        (SprintStatus.BLOCKED, SprintStatus.IN_PROGRESS),    # resume
        (SprintStatus.BACKLOG, SprintStatus.TODO),            # schedule
        (SprintStatus.TODO, SprintStatus.BACKLOG),            # deschedule
        (SprintStatus.DONE, SprintStatus.ARCHIVED),           # archive
        (SprintStatus.ABANDONED, SprintStatus.ARCHIVED),      # archive
    }
)


def validate_transition(
    sprint_id: str,
    from_status: SprintStatus,
    to_status: SprintStatus,
) -> None:
    """Raise InvalidTransitionError if the transition is not allowed."""
    if (from_status, to_status) not in VALID_TRANSITIONS:
        raise InvalidTransitionError(sprint_id, from_status, to_status)
