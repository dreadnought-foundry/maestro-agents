"""Workflow exception types."""


class InvalidTransitionError(Exception):
    """Raised when an invalid sprint state transition is attempted."""

    def __init__(self, sprint_id: str, from_status, to_status):
        self.sprint_id = sprint_id
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(
            f"Invalid transition for sprint {sprint_id}: "
            f"{from_status.value} \u2192 {to_status.value}"
        )
