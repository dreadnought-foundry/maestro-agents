"""TDD tests for Sprint 25: Sprint Completion Artifacts."""

from __future__ import annotations

import pytest
from pathlib import Path

from src.agents.execution.types import AgentResult
from src.execution.artifacts import ArtifactGenerator, SprintArtifacts
from src.execution.hooks import HookPoint, HookResult
from src.execution.runner import RunResult
from src.workflow.models import Sprint, SprintStatus, Step, StepStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_sprint():
    return Sprint(
        id="s-22",
        goal="Wire dependencies, hooks, and retry into SprintRunner",
        status=SprintStatus.DONE,
        epic_id="e-6",
        deliverables=["Updated runner.py", "Updated resume.py"],
        steps=[
            Step(id="step-1", name="implement", status=StepStatus.DONE),
            Step(id="step-2", name="test", status=StepStatus.DONE),
        ],
    )


@pytest.fixture
def sample_run_result():
    return RunResult(
        sprint_id="s-22",
        success=True,
        steps_completed=2,
        steps_total=2,
        agent_results=[
            AgentResult(
                success=True,
                output="Implementation complete",
                files_modified=["src/execution/runner.py"],
                files_created=["src/execution/artifacts.py"],
                deferred_items=["Custom hook creation API"],
            ),
            AgentResult(
                success=True,
                output="All tests passing",
                test_results={"passed": 12, "failed": 0},
                coverage=92.5,
                review_verdict="approve",
                deferred_items=["Hook metrics dashboard"],
            ),
        ],
        deferred_items=["Custom hook creation API", "Hook metrics dashboard"],
        duration_seconds=4.88,
        hook_results={
            "POST_STEP": [
                HookResult(passed=True, message="Coverage 92.5% meets threshold 80.0%"),
            ],
            "PRE_COMPLETION": [
                HookResult(passed=True, message="Quality review approved"),
                HookResult(passed=True, message="All required steps complete"),
            ],
        },
    )


@pytest.fixture
def generator(sample_sprint, sample_run_result):
    return ArtifactGenerator(
        sprint=sample_sprint,
        run_result=sample_run_result,
    )


@pytest.fixture
def empty_result():
    return RunResult(
        sprint_id="s-99",
        success=True,
        steps_completed=0,
        steps_total=0,
        agent_results=[],
        deferred_items=[],
        duration_seconds=0.1,
    )


@pytest.fixture
def empty_sprint():
    return Sprint(
        id="s-99",
        goal="Empty sprint",
        status=SprintStatus.DONE,
        epic_id="e-1",
    )


# ---------------------------------------------------------------------------
# generate_deferred (2 tests)
# ---------------------------------------------------------------------------

class TestGenerateDeferred:
    def test_produces_markdown_with_items(self, generator):
        md = generator.generate_deferred()
        assert "# Deferred Items" in md
        assert "Custom hook creation API" in md
        assert "Hook metrics dashboard" in md
        # Items should be checkbox format
        assert "- [ ]" in md

    def test_no_items_produces_none_message(self, empty_sprint, empty_result):
        gen = ArtifactGenerator(sprint=empty_sprint, run_result=empty_result)
        md = gen.generate_deferred()
        assert "No deferred items" in md


# ---------------------------------------------------------------------------
# generate_postmortem (2 tests)
# ---------------------------------------------------------------------------

class TestGeneratePostmortem:
    def test_includes_sprint_metadata(self, generator):
        md = generator.generate_postmortem()
        assert "s-22" in md
        assert "Wire dependencies" in md
        assert "4.88" in md
        assert "2/2" in md or ("2" in md and "steps" in md.lower())

    def test_includes_per_step_summaries(self, generator):
        md = generator.generate_postmortem()
        assert "implement" in md
        assert "test" in md
        assert "Implementation complete" in md


# ---------------------------------------------------------------------------
# generate_quality_report (3 tests)
# ---------------------------------------------------------------------------

class TestGenerateQualityReport:
    def test_includes_coverage(self, generator):
        md = generator.generate_quality_report()
        assert "92.5" in md
        assert "coverage" in md.lower()

    def test_includes_review_verdict(self, generator):
        md = generator.generate_quality_report()
        assert "approve" in md

    def test_includes_hook_results(self, generator):
        md = generator.generate_quality_report()
        assert "Coverage 92.5% meets threshold" in md


# ---------------------------------------------------------------------------
# generate_contracts (2 tests)
# ---------------------------------------------------------------------------

class TestGenerateContracts:
    def test_includes_files(self, generator):
        md = generator.generate_contracts()
        assert "src/execution/runner.py" in md
        assert "src/execution/artifacts.py" in md

    def test_no_files_produces_empty_sections(self, empty_sprint, empty_result):
        gen = ArtifactGenerator(sprint=empty_sprint, run_result=empty_result)
        md = gen.generate_contracts()
        assert "Contracts" in md
        assert "No files" in md or "None" in md


# ---------------------------------------------------------------------------
# generate_all (1 test)
# ---------------------------------------------------------------------------

class TestGenerateAll:
    def test_returns_sprint_artifacts(self, generator):
        artifacts = generator.generate_all()
        assert isinstance(artifacts, SprintArtifacts)
        assert len(artifacts.deferred) > 0
        assert len(artifacts.postmortem) > 0
        assert len(artifacts.quality) > 0
        assert len(artifacts.contracts) > 0


# ---------------------------------------------------------------------------
# File writing (4 tests)
# ---------------------------------------------------------------------------

class TestFileWriting:
    def test_write_sprint_artifacts_creates_files(self, generator, tmp_path):
        paths = generator.write_sprint_artifacts(tmp_path)
        assert len(paths) == 4
        for p in paths:
            assert p.exists()
            assert p.suffix == ".md"

    def test_append_cumulative_deferred_creates_if_missing(self, generator, tmp_path):
        path = generator.append_to_cumulative_deferred(tmp_path)
        assert path.exists()
        content = path.read_text()
        assert "Deferred Items" in content
        assert "Custom hook creation API" in content

    def test_append_cumulative_deferred_appends_to_existing(self, generator, tmp_path):
        # First append
        generator.append_to_cumulative_deferred(tmp_path)
        # Second append with different sprint
        sprint2 = Sprint(
            id="s-23", goal="Second sprint", status=SprintStatus.DONE, epic_id="e-6",
        )
        result2 = RunResult(
            sprint_id="s-23", success=True, steps_completed=1, steps_total=1,
            deferred_items=["New deferred item"],
            duration_seconds=1.0,
        )
        gen2 = ArtifactGenerator(sprint=sprint2, run_result=result2)
        gen2.append_to_cumulative_deferred(tmp_path)

        content = (tmp_path / "deferred.md").read_text()
        assert "s-22" in content
        assert "s-23" in content
        assert "Custom hook creation API" in content
        assert "New deferred item" in content

    def test_append_cumulative_postmortem_creates_and_appends(self, generator, tmp_path):
        path = generator.append_to_cumulative_postmortem(tmp_path)
        assert path.exists()
        content = path.read_text()
        assert "Postmortem" in content
        assert "s-22" in content
        assert "Wire dependencies" in content


# ---------------------------------------------------------------------------
# Integration with runner (2 tests)
# ---------------------------------------------------------------------------

class TestRunnerIntegration:
    async def test_runner_generates_artifacts_on_success(self, tmp_path):
        from src.adapters.memory import InMemoryAdapter
        from src.agents.execution.mocks import MockProductEngineerAgent
        from src.agents.execution.registry import AgentRegistry
        from src.execution.runner import SprintRunner

        backend = InMemoryAdapter()
        epic = await backend.create_epic("E", "desc")
        sprint = await backend.create_sprint(epic.id, "Test", tasks=[{"name": "implement"}])

        registry = AgentRegistry()
        registry.register("implement", MockProductEngineerAgent())

        sprint_dir = tmp_path / "sprint"
        sprint_dir.mkdir()
        kanban_dir = tmp_path / "kanban"
        kanban_dir.mkdir()

        runner = SprintRunner(
            backend=backend,
            agent_registry=registry,
            artifact_dir=sprint_dir,
            kanban_dir=kanban_dir,
        )
        result = await runner.run(sprint.id)
        assert result.success is True

        # Check per-sprint artifacts were created
        sprint_files = list(sprint_dir.glob("*.md"))
        assert len(sprint_files) == 4

        # Check cumulative files were created
        assert (kanban_dir / "deferred.md").exists()
        assert (kanban_dir / "postmortem.md").exists()

    async def test_runner_generates_artifacts_on_failure(self, tmp_path):
        from src.adapters.memory import InMemoryAdapter
        from src.agents.execution.mocks import MockProductEngineerAgent
        from src.agents.execution.registry import AgentRegistry
        from src.execution.config import RunConfig
        from src.execution.runner import SprintRunner

        backend = InMemoryAdapter()
        epic = await backend.create_epic("E", "desc")
        sprint = await backend.create_sprint(epic.id, "Test", tasks=[{"name": "implement"}])

        failing = MockProductEngineerAgent(
            result=AgentResult(success=False, output="Broke")
        )
        registry = AgentRegistry()
        registry.register("implement", failing)

        sprint_dir = tmp_path / "sprint"
        sprint_dir.mkdir()
        kanban_dir = tmp_path / "kanban"
        kanban_dir.mkdir()

        runner = SprintRunner(
            backend=backend,
            agent_registry=registry,
            artifact_dir=sprint_dir,
            kanban_dir=kanban_dir,
            config=RunConfig(max_retries=0),
        )
        result = await runner.run(sprint.id)
        assert result.success is False

        # Artifacts should still be generated on failure
        sprint_files = list(sprint_dir.glob("*.md"))
        assert len(sprint_files) == 4
        assert (kanban_dir / "postmortem.md").exists()
