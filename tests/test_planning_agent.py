"""Tests for PlanningAgent, PlanningArtifacts, and MockPlanningAgent."""

import re

import pytest
from pathlib import Path

from src.agents.execution.mocks import MockPlanningAgent
from src.agents.execution.planning_agent import PlanningAgent, _parse_artifacts
from src.agents.execution.types import AgentResult, StepContext
from src.execution.planning_artifacts import ARTIFACT_NAMES, PlanningArtifacts
from src.workflow.models import Epic, EpicStatus, Sprint, SprintStatus, Step, StepStatus

# Canonical regex for sprint-prefixed planning artifact filenames
_PLANNING_FILENAME_RE = re.compile(r"^sprint-\d{2,}_planning_[a-z_]+\.md$")


def _make_context(tmp_path: Path) -> StepContext:
    """Build a minimal StepContext for testing."""
    return StepContext(
        step=Step(id="phase-plan", name="plan", status=StepStatus.IN_PROGRESS),
        sprint=Sprint(
            id="s-1",
            goal="Build a widget factory",
            status=SprintStatus.IN_PROGRESS,
            epic_id="e-1",
            tasks=[{"name": "Design"}, {"name": "Build"}, {"name": "Test"}],
            deliverables=["widget_factory.py", "tests/test_widget.py"],
        ),
        epic=Epic(
            id="e-1",
            title="Widget System",
            description="Build the widget subsystem",
            status=EpicStatus.ACTIVE,
        ),
        project_root=tmp_path,
    )


# ---------------------------------------------------------------------------
# PlanningArtifacts
# ---------------------------------------------------------------------------
class TestPlanningArtifacts:
    def test_is_complete_when_all_populated(self):
        artifacts = PlanningArtifacts(
            contracts="c", team_plan="t", tdd_strategy="d",
            coding_strategy="s", context_brief="b",
        )
        assert artifacts.is_complete()

    def test_is_not_complete_when_empty(self):
        artifacts = PlanningArtifacts(contracts="c")
        assert not artifacts.is_complete()

    def test_missing_returns_empty_fields(self):
        artifacts = PlanningArtifacts(contracts="c", team_plan="t")
        missing = artifacts.missing()
        assert "tdd_strategy" in missing
        assert "coding_strategy" in missing
        assert "context_brief" in missing
        assert "contracts" not in missing

    def test_write_and_read_roundtrip(self, tmp_path):
        artifacts = PlanningArtifacts(
            contracts="interface Foo",
            team_plan="2 agents",
            tdd_strategy="test all",
            coding_strategy="use protocols",
            context_brief="python project",
        )
        paths = artifacts.write_to_dir(tmp_path)
        assert len(paths) == 5
        for p in paths:
            assert p.exists()

        loaded = PlanningArtifacts.read_from_dir(tmp_path)
        assert loaded is not None
        assert loaded.contracts == "interface Foo"
        assert loaded.team_plan == "2 agents"
        assert loaded.context_brief == "python project"

    def test_read_from_dir_returns_none_if_missing(self, tmp_path):
        assert PlanningArtifacts.read_from_dir(tmp_path) is None

    def test_write_and_read_roundtrip_with_sprint_prefix(self, tmp_path):
        artifacts = PlanningArtifacts(
            contracts="interface Foo",
            team_plan="2 agents",
            tdd_strategy="test all",
            coding_strategy="use protocols",
            context_brief="python project",
        )
        paths = artifacts.write_to_dir(tmp_path, sprint_prefix="sprint-37")
        assert len(paths) == 5
        for p in paths:
            assert p.exists()
            assert p.name.startswith("sprint-37_planning_")

        loaded = PlanningArtifacts.read_from_dir(tmp_path, sprint_prefix="sprint-37")
        assert loaded is not None
        assert loaded.contracts == "interface Foo"
        assert loaded.team_plan == "2 agents"

    def test_read_from_dir_falls_back_to_legacy(self, tmp_path):
        """read_from_dir with sprint_prefix still finds legacy _planning_*.md files."""
        artifacts = PlanningArtifacts(
            contracts="c", team_plan="t", tdd_strategy="d",
            coding_strategy="s", context_brief="b",
        )
        # Write with legacy naming (no prefix)
        artifacts.write_to_dir(tmp_path)
        # Read with sprint_prefix — should fall back to legacy files
        loaded = PlanningArtifacts.read_from_dir(tmp_path, sprint_prefix="sprint-99")
        assert loaded is not None
        assert loaded.contracts == "c"

    def test_to_context_string(self):
        artifacts = PlanningArtifacts(
            contracts="interface A",
            team_plan="1 agent",
            tdd_strategy="test it",
            coding_strategy="clean code",
            context_brief="context here",
        )
        ctx = artifacts.to_context_string()
        assert "API Contracts" in ctx
        assert "interface A" in ctx
        assert "Team Plan" in ctx
        assert "TDD Strategy" in ctx

    def test_artifact_names_constant(self):
        assert len(ARTIFACT_NAMES) == 5
        assert "contracts" in ARTIFACT_NAMES
        assert "context_brief" in ARTIFACT_NAMES


# ---------------------------------------------------------------------------
# Naming convention enforcement
# ---------------------------------------------------------------------------
class TestPlanningArtifactNamingConvention:
    """Every planning artifact filename must match sprint-NN_planning_{name}.md."""

    _FULL_ARTIFACTS = PlanningArtifacts(
        contracts="c", team_plan="t", tdd_strategy="d",
        coding_strategy="s", context_brief="b",
    )

    @pytest.mark.parametrize("sprint_prefix", [
        "sprint-01", "sprint-09", "sprint-37", "sprint-100",
    ])
    def test_write_to_dir_filenames_match_convention(self, tmp_path, sprint_prefix):
        paths = self._FULL_ARTIFACTS.write_to_dir(tmp_path, sprint_prefix=sprint_prefix)
        for p in paths:
            assert _PLANNING_FILENAME_RE.match(p.name), (
                f"Filename {p.name!r} does not match convention "
                f"sprint-NN_planning_{{name}}.md"
            )

    @pytest.mark.parametrize("artifact_name", ARTIFACT_NAMES)
    def test_each_artifact_name_produces_valid_filename(self, tmp_path, artifact_name):
        expected = f"sprint-37_planning_{artifact_name}.md"
        paths = self._FULL_ARTIFACTS.write_to_dir(tmp_path, sprint_prefix="sprint-37")
        names = [p.name for p in paths]
        assert expected in names, f"Expected {expected!r} in {names}"
        assert _PLANNING_FILENAME_RE.match(expected)

    async def test_mock_agent_filenames_match_convention(self, tmp_path):
        """MockPlanningAgent.files_created must follow the naming convention."""
        agent = MockPlanningAgent()
        context = _make_context(tmp_path)
        result = await agent.execute(context)
        for filename in result.files_created:
            assert _PLANNING_FILENAME_RE.match(filename), (
                f"Mock filename {filename!r} does not match convention"
            )


# ---------------------------------------------------------------------------
# _parse_artifacts
# ---------------------------------------------------------------------------
class TestParseArtifacts:
    def test_parses_all_sections(self):
        output = (
            "### CONTRACTS\ninterface Foo\n\n"
            "### TEAM_PLAN\n2 agents\n\n"
            "### TDD_STRATEGY\ntest everything\n\n"
            "### CODING_STRATEGY\nuse protocols\n\n"
            "### CONTEXT_BRIEF\npython project"
        )
        artifacts = _parse_artifacts(output)
        assert artifacts.contracts == "interface Foo"
        assert artifacts.team_plan == "2 agents"
        assert artifacts.tdd_strategy == "test everything"
        assert artifacts.coding_strategy == "use protocols"
        assert artifacts.context_brief == "python project"
        assert artifacts.is_complete()

    def test_handles_missing_sections(self):
        output = "### CONTRACTS\nsome contracts\n\n### TEAM_PLAN\na plan"
        artifacts = _parse_artifacts(output)
        assert artifacts.contracts == "some contracts"
        assert artifacts.team_plan == "a plan"
        assert not artifacts.is_complete()
        assert "tdd_strategy" in artifacts.missing()

    def test_handles_empty_output(self):
        artifacts = _parse_artifacts("")
        assert not artifacts.is_complete()
        assert len(artifacts.missing()) == 5

    def test_handles_multiline_sections(self):
        output = (
            "### CONTRACTS\nline 1\nline 2\nline 3\n\n"
            "### TEAM_PLAN\nagent list\n\n"
            "### TDD_STRATEGY\ntests\n\n"
            "### CODING_STRATEGY\npatterns\n\n"
            "### CONTEXT_BRIEF\ncontext"
        )
        artifacts = _parse_artifacts(output)
        assert "line 1\nline 2\nline 3" in artifacts.contracts


# ---------------------------------------------------------------------------
# MockPlanningAgent
# ---------------------------------------------------------------------------
class TestMockPlanningAgent:
    async def test_returns_success(self, tmp_path):
        agent = MockPlanningAgent()
        context = _make_context(tmp_path)
        result = await agent.execute(context)
        assert result.success
        assert len(result.files_created) == 5
        # Sprint id "s-1" → files should use "sprint-01_planning_" prefix
        for f in result.files_created:
            assert f.startswith("sprint-01_planning_"), f"unexpected filename: {f}"

    async def test_output_is_parseable(self, tmp_path):
        agent = MockPlanningAgent()
        context = _make_context(tmp_path)
        result = await agent.execute(context)
        artifacts = _parse_artifacts(result.output)
        assert artifacts.is_complete()

    async def test_tracks_calls(self, tmp_path):
        agent = MockPlanningAgent()
        context = _make_context(tmp_path)
        await agent.execute(context)
        await agent.execute(context)
        assert agent.call_count == 2
        assert agent.last_context is context

    async def test_custom_artifacts(self, tmp_path):
        custom = PlanningArtifacts(
            contracts="custom contracts",
            team_plan="custom plan",
            tdd_strategy="custom tdd",
            coding_strategy="custom coding",
            context_brief="custom context",
        )
        agent = MockPlanningAgent(artifacts=custom)
        result = await agent.execute(_make_context(tmp_path))
        artifacts = _parse_artifacts(result.output)
        assert artifacts.contracts == "custom contracts"


# ---------------------------------------------------------------------------
# PlanningAgent (unit tests — no executor)
# ---------------------------------------------------------------------------
class TestPlanningAgent:
    def test_build_prompt_includes_sprint_info(self, tmp_path):
        agent = PlanningAgent()
        context = _make_context(tmp_path)
        prompt = agent._build_prompt(context)
        assert "Build a widget factory" in prompt
        assert "Widget System" in prompt
        assert "Design" in prompt

    def test_build_prompt_includes_deliverables(self, tmp_path):
        agent = PlanningAgent()
        context = _make_context(tmp_path)
        prompt = agent._build_prompt(context)
        assert "widget_factory.py" in prompt

    def test_build_prompt_includes_deferred(self, tmp_path):
        context = _make_context(tmp_path)
        context.cumulative_deferred = "Fix the flaky test"
        agent = PlanningAgent()
        prompt = agent._build_prompt(context)
        assert "Fix the flaky test" in prompt

    def test_build_prompt_includes_postmortem(self, tmp_path):
        context = _make_context(tmp_path)
        context.cumulative_postmortem = "Subprocess calls are slow"
        agent = PlanningAgent()
        prompt = agent._build_prompt(context)
        assert "Subprocess calls are slow" in prompt

    async def test_raises_without_executor(self, tmp_path):
        agent = PlanningAgent()
        context = _make_context(tmp_path)
        result = await agent.execute(context)
        assert not result.success
        assert "failed" in result.output.lower()


# ---------------------------------------------------------------------------
# Planning artifacts flow to StepContext
# ---------------------------------------------------------------------------
class TestStepContextPlanningArtifacts:
    def test_step_context_accepts_planning_artifacts(self, tmp_path):
        artifacts = PlanningArtifacts(
            contracts="c", team_plan="t", tdd_strategy="d",
            coding_strategy="s", context_brief="b",
        )
        context = _make_context(tmp_path)
        context.planning_artifacts = artifacts
        assert context.planning_artifacts.contracts == "c"

    def test_step_context_default_none(self, tmp_path):
        context = _make_context(tmp_path)
        assert context.planning_artifacts is None


# ---------------------------------------------------------------------------
# PLAN phase gate: blocks if artifacts are incomplete
# ---------------------------------------------------------------------------
class TestPlanPhaseGate:
    async def test_complete_artifacts_pass_gate(self):
        """Verify that _parse_artifacts on MockPlanningAgent output produces complete artifacts."""
        agent = MockPlanningAgent()
        context = _make_context(Path("/tmp"))
        result = await agent.execute(context)
        artifacts = _parse_artifacts(result.output)
        assert artifacts.is_complete()
        assert len(artifacts.missing()) == 0

    async def test_incomplete_artifacts_detected(self):
        """Verify that incomplete artifacts are detected."""
        artifacts = PlanningArtifacts(contracts="only contracts")
        assert not artifacts.is_complete()
        assert len(artifacts.missing()) == 4
