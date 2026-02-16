"""Tests for the backlog grooming agent and hook (Sprint 28)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters.memory import InMemoryAdapter
from src.agents.execution.mocks import MockProductEngineerAgent
from src.agents.execution.registry import AgentRegistry
from src.execution.grooming import (
    GROOMING_PROMPT,
    MID_EPIC_PROMPT,
    GroomingAgent,
    GroomingProposal,
    MockGroomingAgent,
)
from src.execution.grooming_hook import GroomingHook, _parse_epic_number
from src.execution.hooks import HookContext, HookPoint, HookRegistry, HookResult
from src.execution.runner import SprintRunner
from src.kanban.scanner import is_epic_complete
from src.workflow.models import (
    Epic,
    EpicStatus,
    Sprint,
    SprintStatus,
    Step,
    StepStatus,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_epic_dir(tmp_path: Path, epic_num: int, sprints: list[tuple[int, str]]):
    """Create a minimal epic directory with sprints in status folders.

    sprints: list of (sprint_num, status) where status is a kanban folder name
    like "3-done" or "2-in-progress".
    """
    for sprint_num, status_folder in sprints:
        sprint_dir = tmp_path / status_folder / f"epic-{epic_num:02d}_test" / f"sprint-{sprint_num:02d}_s"
        sprint_dir.mkdir(parents=True, exist_ok=True)
        spec = sprint_dir / f"sprint-{sprint_num:02d}_s.md"
        spec.write_text(f"---\ntitle: Sprint {sprint_num}\nepic: {epic_num}\n---\n")

    epic_dir = tmp_path / status_folder / f"epic-{epic_num:02d}_test"
    epic_file = epic_dir / "_epic.md"
    if not epic_file.exists():
        epic_file.write_text(f"---\ntitle: Test Epic {epic_num}\n---\n")


def _make_kanban(tmp_path: Path, deferred: str = "", postmortem: str = ""):
    """Write deferred.md and postmortem.md to a kanban dir."""
    if deferred:
        (tmp_path / "deferred.md").write_text(deferred)
    if postmortem:
        (tmp_path / "postmortem.md").write_text(postmortem)


# ---------------------------------------------------------------------------
# MockGroomingAgent tests
# ---------------------------------------------------------------------------


class TestMockGroomingAgent:
    @pytest.mark.asyncio
    async def test_returns_canned_proposal(self, tmp_path):
        agent = MockGroomingAgent()
        proposal = await agent.propose(tmp_path)
        assert isinstance(proposal, GroomingProposal)
        assert "Grooming Proposal" in proposal.raw_markdown
        assert proposal.proposal_path == tmp_path / "grooming_proposal.md"

    @pytest.mark.asyncio
    async def test_tracks_call_count(self, tmp_path):
        agent = MockGroomingAgent()
        assert agent.call_count == 0
        await agent.propose(tmp_path)
        await agent.propose(tmp_path, epic_num=3)
        assert agent.call_count == 2
        assert agent.last_epic_num == 3

    @pytest.mark.asyncio
    async def test_writes_proposal_file(self, tmp_path):
        agent = MockGroomingAgent(proposal_text="# Custom Proposal\nStuff")
        await agent.propose(tmp_path)
        written = (tmp_path / "grooming_proposal.md").read_text()
        assert written == "# Custom Proposal\nStuff"


# ---------------------------------------------------------------------------
# GroomingAgent prompt building tests
# ---------------------------------------------------------------------------


class TestGroomingAgentPromptBuilding:
    def test_builds_content_with_deferred(self, tmp_path):
        _make_kanban(tmp_path, deferred="## Items\n- Fix bug")
        agent = GroomingAgent()
        content = agent._build_content(
            deferred="## Items\n- Fix bug",
            postmortem="",
            board_summary="No epics on the board.",
            epic_num=None,
            kanban_dir=tmp_path,
        )
        assert "## Deferred Items" in content
        assert "Fix bug" in content

    def test_builds_content_with_postmortem(self, tmp_path):
        agent = GroomingAgent()
        content = agent._build_content(
            deferred="",
            postmortem="## Lessons\n- Use protocols",
            board_summary="No epics on the board.",
            epic_num=None,
            kanban_dir=tmp_path,
        )
        assert "## Postmortem Lessons" in content
        assert "Use protocols" in content

    def test_builds_content_with_board_state(self, tmp_path):
        agent = GroomingAgent()
        content = agent._build_content(
            deferred="",
            postmortem="",
            board_summary="- Epic 1: Foo [done] (3/3 sprints done)",
            epic_num=None,
            kanban_dir=tmp_path,
        )
        assert "## Current Board State" in content
        assert "Epic 1: Foo" in content

    def test_handles_empty_deferred(self, tmp_path):
        agent = GroomingAgent()
        content = agent._build_content(
            deferred="",
            postmortem="",
            board_summary="No epics.",
            epic_num=None,
            kanban_dir=tmp_path,
        )
        assert "No deferred items found" in content

    def test_selects_full_prompt_when_no_epic(self, tmp_path):
        agent = GroomingAgent()
        prompt = agent._select_prompt(epic_num=None, kanban_dir=tmp_path)
        assert prompt == GROOMING_PROMPT

    def test_selects_mid_epic_prompt_when_epic_incomplete(self, tmp_path):
        """Mid-epic mode when epic has incomplete sprints."""
        _make_epic_dir(tmp_path, epic_num=5, sprints=[
            (20, "3-done"),
            (21, "2-in-progress"),
        ])
        agent = GroomingAgent()
        prompt = agent._select_prompt(epic_num=5, kanban_dir=tmp_path)
        assert prompt == MID_EPIC_PROMPT

    def test_selects_full_prompt_when_epic_complete(self, tmp_path):
        """Full grooming mode when epic is fully done."""
        _make_epic_dir(tmp_path, epic_num=5, sprints=[
            (20, "3-done"),
            (21, "3-done"),
        ])
        agent = GroomingAgent()
        prompt = agent._select_prompt(epic_num=5, kanban_dir=tmp_path)
        assert prompt == GROOMING_PROMPT


# ---------------------------------------------------------------------------
# is_epic_complete tests
# ---------------------------------------------------------------------------


class TestIsEpicComplete:
    def test_true_when_all_sprints_done(self, tmp_path):
        _make_epic_dir(tmp_path, epic_num=3, sprints=[
            (10, "3-done"),
            (11, "3-done"),
            (12, "3-done"),
        ])
        assert is_epic_complete(3, tmp_path) is True

    def test_false_when_some_pending(self, tmp_path):
        _make_epic_dir(tmp_path, epic_num=3, sprints=[
            (10, "3-done"),
            (11, "2-in-progress"),
        ])
        assert is_epic_complete(3, tmp_path) is False

    def test_false_for_nonexistent_epic(self, tmp_path):
        assert is_epic_complete(999, tmp_path) is False


# ---------------------------------------------------------------------------
# GroomingHook tests
# ---------------------------------------------------------------------------


class TestGroomingHook:
    @pytest.mark.asyncio
    async def test_triggers_full_grooming_when_epic_complete(self, tmp_path):
        _make_epic_dir(tmp_path, epic_num=5, sprints=[
            (20, "3-done"),
            (21, "3-done"),
        ])
        mock_agent = MockGroomingAgent()
        hook = GroomingHook(kanban_dir=tmp_path, grooming_agent=mock_agent)

        sprint = Sprint(
            id="s-21", epic_id="e-5", goal="test",
            status=SprintStatus.DONE, steps=[],
        )
        ctx = HookContext(sprint=sprint)
        result = await hook.evaluate(ctx)

        assert result.passed is True
        assert result.blocking is False
        assert mock_agent.call_count == 1
        assert mock_agent.last_epic_num is None  # full grooming
        assert "complete" in result.message.lower()

    @pytest.mark.asyncio
    async def test_triggers_mid_epic_grooming_when_not_complete(self, tmp_path):
        _make_epic_dir(tmp_path, epic_num=5, sprints=[
            (20, "3-done"),
            (21, "2-in-progress"),
        ])
        mock_agent = MockGroomingAgent()
        hook = GroomingHook(kanban_dir=tmp_path, grooming_agent=mock_agent)

        sprint = Sprint(
            id="s-20", epic_id="e-5", goal="test",
            status=SprintStatus.DONE, steps=[],
        )
        ctx = HookContext(sprint=sprint)
        result = await hook.evaluate(ctx)

        assert result.passed is True
        assert result.blocking is False
        assert mock_agent.call_count == 1
        assert mock_agent.last_epic_num == 5  # mid-epic grooming
        assert "mid-epic" in result.message.lower()

    @pytest.mark.asyncio
    async def test_always_nonblocking(self, tmp_path):
        hook = GroomingHook(kanban_dir=tmp_path, grooming_agent=None)
        sprint = Sprint(
            id="s-1", epic_id="e-1", goal="test",
            status=SprintStatus.DONE, steps=[],
        )
        ctx = HookContext(sprint=sprint)
        result = await hook.evaluate(ctx)
        assert result.blocking is False

    @pytest.mark.asyncio
    async def test_skips_when_no_agent_configured(self, tmp_path):
        hook = GroomingHook(kanban_dir=tmp_path, grooming_agent=None)
        sprint = Sprint(
            id="s-1", epic_id="e-1", goal="test",
            status=SprintStatus.DONE, steps=[],
        )
        ctx = HookContext(sprint=sprint)
        result = await hook.evaluate(ctx)
        assert result.passed is True
        assert "no grooming agent" in result.message.lower()


# ---------------------------------------------------------------------------
# _parse_epic_number tests
# ---------------------------------------------------------------------------


class TestParseEpicNumber:
    def test_parses_e_dash_number(self):
        assert _parse_epic_number("e-3") == 3

    def test_parses_epic_dash_number(self):
        assert _parse_epic_number("epic-03") == 3

    def test_returns_none_for_no_number(self):
        assert _parse_epic_number("no-number-here") is None


# ---------------------------------------------------------------------------
# Runner integration: POST_COMPLETION hook fires
# ---------------------------------------------------------------------------


class TestPostCompletionHookFires:
    @pytest.mark.asyncio
    async def test_post_completion_hook_fires_after_success(self):
        backend = InMemoryAdapter(project_name="test")
        epic = await backend.create_epic("Test Epic", "desc")
        sprint = await backend.create_sprint(
            epic.id, "Test sprint", tasks=[{"name": "implement"}],
        )

        registry = AgentRegistry()
        registry.register("implement", MockProductEngineerAgent())

        # Track POST_COMPLETION hook calls
        class TrackingHook:
            hook_point = HookPoint.POST_COMPLETION

            def __init__(self):
                self.call_count = 0

            async def evaluate(self, context):
                self.call_count += 1
                return HookResult(passed=True, message="tracked", blocking=False)

        tracker = TrackingHook()
        hook_registry = HookRegistry()
        hook_registry.register(tracker)

        runner = SprintRunner(
            backend=backend,
            agent_registry=registry,
            hook_registry=hook_registry,
        )
        result = await runner.run("s-1")

        assert result.success is True
        assert tracker.call_count == 1
