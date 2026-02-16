"""POST_COMPLETION hook that triggers backlog grooming."""

from __future__ import annotations

import re
from pathlib import Path

from src.execution.hooks import HookContext, HookPoint, HookResult
from src.kanban.scanner import is_epic_complete


class GroomingHook:
    """Triggers grooming after a sprint completes.

    - If the epic is complete → full grooming (propose next epic)
    - If the epic is still in progress → mid-epic grooming (propose additional sprints)
    """

    hook_point = HookPoint.POST_COMPLETION

    def __init__(self, kanban_dir: Path, grooming_agent=None):
        self._kanban_dir = kanban_dir
        self._grooming = grooming_agent

    async def evaluate(self, context: HookContext) -> HookResult:
        if self._grooming is None:
            return HookResult(
                passed=True,
                message="No grooming agent configured",
                blocking=False,
            )

        epic_num = _parse_epic_number(context.sprint.epic_id)
        if epic_num is None:
            return HookResult(
                passed=True,
                message=f"Could not parse epic number from '{context.sprint.epic_id}'",
                blocking=False,
            )

        if is_epic_complete(epic_num, self._kanban_dir):
            # Epic is done — full grooming, propose next epic
            proposal = await self._grooming.propose(self._kanban_dir, epic_num=None)
            return HookResult(
                passed=True,
                message=(
                    f"Epic {epic_num} complete. "
                    f"Grooming proposal: {proposal.proposal_path}"
                ),
                blocking=False,
            )
        else:
            # Epic still in progress — mid-epic grooming
            proposal = await self._grooming.propose(
                self._kanban_dir, epic_num=epic_num,
            )
            return HookResult(
                passed=True,
                message=(
                    f"Sprint complete in epic {epic_num}. "
                    f"Mid-epic grooming proposal: {proposal.proposal_path}"
                ),
                blocking=False,
            )


def _parse_epic_number(epic_id: str) -> int | None:
    """Extract epic number from an epic_id like 'e-3' or 'epic-03'."""
    match = re.search(r"(\d+)", epic_id)
    if match:
        return int(match.group(1))
    return None
