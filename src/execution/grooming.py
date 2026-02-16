"""Backlog grooming agent — proposes next epics/sprints from deferred items."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path

from src.kanban.scanner import is_epic_complete, scan_board

GROOMING_PROMPT = """\
You are a backlog grooming agent for a software project. Your job is to analyze \
the accumulated deferred items and postmortem lessons, then propose the next \
body of work.

Rules:
1. Prioritize 🔴 High importance items first, then 🟡 Medium.
2. Group related deferred items into coherent epics (2-5 sprints each).
3. Each proposed sprint should have:
   - A clear goal (one sentence)
   - 3-7 concrete tasks
   - Dependencies on other proposed sprints (if any)
   - Expected deliverables
4. Cross-reference postmortem lessons — avoid proposing work that repeats \
   past mistakes. Apply architectural patterns that worked.
5. Flag items that should remain deferred (too low priority, too speculative, \
   or dependent on external factors).
6. Consider the current board state — don't propose work that duplicates \
   active or completed sprints.
7. Output structured markdown with clear epic and sprint headings.
8. Output ONLY the proposal markdown — no commentary, no code fences.
"""

MID_EPIC_PROMPT = """\
You are a backlog grooming agent for a software project. A sprint just \
completed within an active epic, and new deferred items have surfaced. Your \
job is to propose additional sprints to close out this epic cleanly.

Rules:
1. Focus on deferred items that are directly relevant to this epic's scope.
2. Propose 1-3 additional sprints that would address the most important \
   gaps before the epic can be considered complete.
3. Each proposed sprint should have:
   - A clear goal (one sentence)
   - 3-7 concrete tasks
   - Dependencies on existing sprints in this epic
   - Expected deliverables
4. Apply lessons from the postmortem — don't repeat past mistakes.
5. Keep scope tight — only propose what's needed to close out this epic, \
   not everything in the backlog.
6. Flag items that belong in a future epic instead.
7. Output structured markdown with sprint headings.
8. Output ONLY the proposal markdown — no commentary, no code fences.
"""


@dataclass
class GroomingProposal:
    """Result of a grooming agent run."""

    raw_markdown: str
    proposal_path: Path
    board_state_summary: str


class GroomingAgent:
    """Proposes next epic/sprint breakdown from deferred items and postmortems."""

    def __init__(self, model: str = "sonnet"):
        self._model = model

    async def propose(
        self,
        kanban_dir: Path,
        epic_num: int | None = None,
    ) -> GroomingProposal:
        """Analyze backlog and propose next work.

        Args:
            kanban_dir: Path to the kanban directory.
            epic_num: If set, scope grooming to this epic. If the epic is not
                      yet complete, uses mid-epic mode (propose additional sprints).
                      If complete or None, uses full grooming (propose next epic).
        """
        deferred = self._read_file(kanban_dir / "deferred.md")
        postmortem = self._read_file(kanban_dir / "postmortem.md")
        board_state = scan_board(kanban_dir)

        board_summary = self._summarize_board(board_state)
        content = self._build_content(
            deferred, postmortem, board_summary, epic_num, kanban_dir,
        )
        prompt = self._select_prompt(epic_num, kanban_dir)

        result = await self._call_claude(prompt, content)

        proposal_path = kanban_dir / "grooming_proposal.md"
        proposal_path.write_text(result)

        return GroomingProposal(
            raw_markdown=result,
            proposal_path=proposal_path,
            board_state_summary=board_summary,
        )

    def _select_prompt(self, epic_num: int | None, kanban_dir: Path) -> str:
        """Choose system prompt based on grooming mode."""
        if epic_num is not None and not is_epic_complete(epic_num, kanban_dir):
            return MID_EPIC_PROMPT
        return GROOMING_PROMPT

    def _build_content(
        self,
        deferred: str,
        postmortem: str,
        board_summary: str,
        epic_num: int | None,
        kanban_dir: Path,
    ) -> str:
        """Assemble the content payload for the LLM."""
        parts = [f"## Current Board State\n\n{board_summary}"]

        if epic_num is not None:
            epic = scan_board(kanban_dir).epics.get(epic_num)
            if epic is not None:
                status = "complete" if is_epic_complete(epic_num, kanban_dir) else "in progress"
                parts.append(
                    f"\n## Current Epic: {epic.title} (#{epic_num}, {status})\n"
                    f"Sprints: {epic.completed_sprints}/{epic.total_sprints} complete"
                )

        if deferred:
            parts.append(f"\n## Deferred Items\n\n{deferred}")
        else:
            parts.append("\n## Deferred Items\n\nNo deferred items found.")

        if postmortem:
            parts.append(f"\n## Postmortem Lessons\n\n{postmortem}")

        return "\n".join(parts)

    def _summarize_board(self, board_state) -> str:
        """Create a compact summary of the board state."""
        lines = []
        for num, epic in sorted(board_state.epics.items()):
            lines.append(
                f"- Epic {num}: {epic.title} [{epic.status}] "
                f"({epic.completed_sprints}/{epic.total_sprints} sprints done)"
            )
        if not lines:
            return "No epics on the board."
        return "\n".join(lines)

    def _read_file(self, path: Path) -> str:
        """Read a file, returning empty string if missing or empty."""
        if not path.exists():
            return ""
        content = path.read_text().strip()
        return content

    async def _call_claude(self, system_prompt: str, content: str) -> str:
        prompt = f"{system_prompt}\n\n---\n\n{content}"
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        proc = await asyncio.create_subprocess_exec(
            "claude",
            "--print",
            "--model", self._model,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await proc.communicate(input=prompt.encode())
        if proc.returncode != 0:
            raise RuntimeError(
                f"claude CLI failed (exit {proc.returncode}): {stderr.decode()}"
            )
        return stdout.decode().strip()


class MockGroomingAgent:
    """Test double that returns a canned proposal."""

    def __init__(self, proposal_text: str | None = None):
        self._text = proposal_text or (
            "# Grooming Proposal\n\n"
            "## Proposed Epic: Production Readiness\n\n"
            "### Sprint 1: SDK Integration\n"
            "- Integrate production Claude SDK\n"
            "- Replace mock agents with real implementations\n"
        )
        self.call_count = 0
        self.last_epic_num: int | None = None

    async def propose(
        self,
        kanban_dir: Path,
        epic_num: int | None = None,
    ) -> GroomingProposal:
        self.call_count += 1
        self.last_epic_num = epic_num
        path = kanban_dir / "grooming_proposal.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._text)
        return GroomingProposal(
            raw_markdown=self._text,
            proposal_path=path,
            board_state_summary="mock board state",
        )
