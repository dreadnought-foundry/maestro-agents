"""DAG-based step scheduler for parallel execution within phases.

Steps declare dependencies on other steps via `depends_on`. The scheduler
determines which steps are ready to run (all dependencies met) and tracks
completion, enabling concurrent execution of independent steps.
"""

from __future__ import annotations

from src.workflow.models import Step, StepStatus


class CyclicDependencyError(Exception):
    """Raised when step dependencies form a cycle."""


class Scheduler:
    """DAG scheduler that tracks step dependencies and readiness.

    Usage:
        scheduler = Scheduler(steps)
        while not scheduler.is_done():
            ready = scheduler.get_ready_steps()
            # Execute ready steps concurrently
            for step in ready:
                scheduler.mark_in_progress(step.id)
            # ... await results ...
            scheduler.mark_complete(step_id)  # or mark_failed(step_id)
    """

    def __init__(self, steps: list[Step]) -> None:
        self._steps = {s.id: s for s in steps}
        self._completed: set[str] = set()
        self._failed: set[str] = set()
        self._in_progress: set[str] = set()
        self._validate_no_cycles()

    def _validate_no_cycles(self) -> None:
        """Detect cycles using DFS."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {sid: WHITE for sid in self._steps}

        def dfs(sid: str) -> None:
            color[sid] = GRAY
            step = self._steps[sid]
            for dep_id in step.depends_on:
                if dep_id not in self._steps:
                    continue
                if color[dep_id] == GRAY:
                    raise CyclicDependencyError(
                        f"Cycle detected involving steps: {sid} -> {dep_id}"
                    )
                if color[dep_id] == WHITE:
                    dfs(dep_id)
            color[sid] = BLACK

        for sid in self._steps:
            if color[sid] == WHITE:
                dfs(sid)

    def get_ready_steps(self) -> list[Step]:
        """Return steps whose dependencies are all met and aren't started/done."""
        ready = []
        for sid, step in self._steps.items():
            if sid in self._completed or sid in self._in_progress or sid in self._failed:
                continue
            deps_met = all(
                dep_id in self._completed
                for dep_id in step.depends_on
                if dep_id in self._steps
            )
            if deps_met:
                ready.append(step)
        return ready

    def mark_in_progress(self, step_id: str) -> None:
        """Mark a step as currently executing."""
        if step_id not in self._steps:
            raise KeyError(f"Unknown step: {step_id}")
        self._in_progress.add(step_id)

    def mark_complete(self, step_id: str) -> None:
        """Mark a step as completed, unlocking dependents."""
        if step_id not in self._steps:
            raise KeyError(f"Unknown step: {step_id}")
        self._in_progress.discard(step_id)
        self._completed.add(step_id)

    def mark_failed(self, step_id: str) -> None:
        """Mark a step as failed. Dependents will never become ready."""
        if step_id not in self._steps:
            raise KeyError(f"Unknown step: {step_id}")
        self._in_progress.discard(step_id)
        self._failed.add(step_id)

    def is_done(self) -> bool:
        """True when no more progress can be made.

        This is when all steps are completed/failed, OR when the only remaining
        steps have unmet dependencies (due to upstream failures).
        """
        if len(self._completed) + len(self._failed) == len(self._steps):
            return True
        # Check if any remaining steps could ever become ready
        return len(self.get_ready_steps()) == 0 and len(self._in_progress) == 0

    def has_failures(self) -> bool:
        """True if any step has failed or is blocked (unreachable due to upstream failure)."""
        if self._failed:
            return True
        # Also check for blocked steps (deps failed, so they'll never run)
        remaining = set(self._steps.keys()) - self._completed - self._failed - self._in_progress
        for sid in remaining:
            step = self._steps[sid]
            if any(dep_id in self._failed for dep_id in step.depends_on if dep_id in self._steps):
                return True
        return False

    @property
    def completed_ids(self) -> set[str]:
        return set(self._completed)

    @property
    def failed_ids(self) -> set[str]:
        return set(self._failed)


def steps_to_sequential(steps: list[Step]) -> list[Step]:
    """Add linear dependencies to steps that have none, making them sequential.

    This is the backwards-compatible default: steps without explicit depends_on
    are chained so each depends on the previous one.
    """
    has_any_deps = any(step.depends_on for step in steps)
    if has_any_deps:
        return steps

    for i in range(1, len(steps)):
        steps[i].depends_on = [steps[i - 1].id]
    return steps
