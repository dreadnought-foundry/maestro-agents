"""Tests for Sprint 26: LLM-Based Synthesis for Cumulative Artifacts."""

from __future__ import annotations

import pytest
from pathlib import Path

from src.agents.execution.types import AgentResult
from src.execution.artifacts import ArtifactGenerator
from src.execution.runner import RunResult
from src.execution.synthesizer import MockSynthesizer, Synthesizer
from src.workflow.models import Sprint, SprintStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_sprint():
    return Sprint(
        id="s-26",
        goal="LLM-Based Synthesis",
        status=SprintStatus.DONE,
        epic_id="e-7",
    )


@pytest.fixture
def sample_result():
    return RunResult(
        sprint_id="s-26",
        success=True,
        steps_completed=2,
        steps_total=2,
        agent_results=[
            AgentResult(
                success=True,
                output="Done",
                deferred_items=["Widget API redesign"],
            ),
        ],
        deferred_items=["Widget API redesign"],
        duration_seconds=3.0,
    )


@pytest.fixture
def generator(sample_sprint, sample_result):
    return ArtifactGenerator(sprint=sample_sprint, run_result=sample_result)


# ---------------------------------------------------------------------------
# MockSynthesizer (3 tests)
# ---------------------------------------------------------------------------

class TestMockSynthesizer:
    @pytest.mark.asyncio
    async def test_passthrough_unchanged(self, tmp_path):
        path = tmp_path / "deferred.md"
        path.write_text("# Deferred Items\n\n- [ ] Item A\n")
        mock = MockSynthesizer()
        result = await mock.synthesize_deferred(path)
        assert result == "# Deferred Items\n\n- [ ] Item A\n"

    @pytest.mark.asyncio
    async def test_tracks_call_count(self, tmp_path):
        path = tmp_path / "postmortem.md"
        path.write_text("# Postmortems\n")
        mock = MockSynthesizer()
        await mock.synthesize_postmortem(path)
        await mock.synthesize_postmortem(path)
        assert mock.call_count == 2

    @pytest.mark.asyncio
    async def test_custom_transform(self, tmp_path):
        path = tmp_path / "deferred.md"
        path.write_text("# Deferred Items\n\n- [ ] Item A\n- [ ] Item A\n")
        mock = MockSynthesizer(transform=lambda c: c.upper())
        result = await mock.synthesize_deferred(path)
        assert result == "# DEFERRED ITEMS\n\n- [ ] ITEM A\n- [ ] ITEM A\n"
        assert path.read_text() == result


# ---------------------------------------------------------------------------
# ArtifactGenerator integration with Synthesizer (4 tests)
# ---------------------------------------------------------------------------

class TestAppendAndSynthesize:
    @pytest.mark.asyncio
    async def test_deferred_calls_synthesizer(self, generator, tmp_path):
        mock = MockSynthesizer()
        await generator.append_and_synthesize_deferred(tmp_path, synthesizer=mock)
        assert mock.call_count == 1
        content = (tmp_path / "deferred.md").read_text()
        assert "Widget API redesign" in content

    @pytest.mark.asyncio
    async def test_deferred_skips_when_no_synthesizer(self, generator, tmp_path):
        path = await generator.append_and_synthesize_deferred(tmp_path, synthesizer=None)
        assert path.exists()
        content = path.read_text()
        assert "Widget API redesign" in content

    @pytest.mark.asyncio
    async def test_postmortem_calls_synthesizer(self, generator, tmp_path):
        mock = MockSynthesizer()
        await generator.append_and_synthesize_postmortem(tmp_path, synthesizer=mock)
        assert mock.call_count == 1
        content = (tmp_path / "postmortem.md").read_text()
        assert "s-26" in content

    @pytest.mark.asyncio
    async def test_postmortem_skips_when_no_synthesizer(self, generator, tmp_path):
        path = await generator.append_and_synthesize_postmortem(tmp_path, synthesizer=None)
        assert path.exists()
        content = path.read_text()
        assert "s-26" in content


# ---------------------------------------------------------------------------
# Runner integration (2 tests)
# ---------------------------------------------------------------------------

class TestRunnerSynthesizerIntegration:
    @pytest.mark.asyncio
    async def test_runner_calls_synthesizer(self, tmp_path):
        from src.adapters.memory import InMemoryAdapter
        from src.agents.execution.mocks import MockProductEngineerAgent
        from src.agents.execution.registry import AgentRegistry
        from src.execution.runner import SprintRunner

        backend = InMemoryAdapter()
        epic = await backend.create_epic("E", "desc")
        sprint = await backend.create_sprint(epic.id, "Test", tasks=[{"name": "implement"}])

        registry = AgentRegistry()
        registry.register("implement", MockProductEngineerAgent())

        kanban_dir = tmp_path / "kanban"
        mock_synth = MockSynthesizer()

        runner = SprintRunner(
            backend=backend,
            agent_registry=registry,
            kanban_dir=kanban_dir,
            synthesizer=mock_synth,
        )
        result = await runner.run(sprint.id)
        assert result.success is True
        # Synthesizer should be called twice: once for deferred, once for postmortem
        assert mock_synth.call_count == 2

    @pytest.mark.asyncio
    async def test_runner_without_synthesizer_no_regression(self, tmp_path):
        from src.adapters.memory import InMemoryAdapter
        from src.agents.execution.mocks import MockProductEngineerAgent
        from src.agents.execution.registry import AgentRegistry
        from src.execution.runner import SprintRunner

        backend = InMemoryAdapter()
        epic = await backend.create_epic("E", "desc")
        sprint = await backend.create_sprint(epic.id, "Test", tasks=[{"name": "implement"}])

        registry = AgentRegistry()
        registry.register("implement", MockProductEngineerAgent())

        kanban_dir = tmp_path / "kanban"

        runner = SprintRunner(
            backend=backend,
            agent_registry=registry,
            kanban_dir=kanban_dir,
        )
        result = await runner.run(sprint.id)
        assert result.success is True
        assert (kanban_dir / "deferred.md").exists()
        assert (kanban_dir / "postmortem.md").exists()


# ---------------------------------------------------------------------------
# Synthesizer edge cases (1 test)
# ---------------------------------------------------------------------------

class TestSynthesizerEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_file(self, tmp_path):
        path = tmp_path / "deferred.md"
        path.write_text("")
        mock = MockSynthesizer()
        result = await mock.synthesize_deferred(path)
        assert result == ""
