"""Integration tests for MaestroAdapter file I/O."""

import json

import pytest
import pytest_asyncio

from src.adapters.maestro import MaestroAdapter


@pytest_asyncio.fixture
async def adapter(tmp_path):
    return MaestroAdapter(tmp_path)


@pytest_asyncio.fixture
async def seeded_adapter(tmp_path):
    adapter = MaestroAdapter(tmp_path)
    epic = await adapter.create_epic("Auth System", "Build authentication")
    await adapter.create_sprint(
        epic_id=epic.id,
        goal="Design schema",
        tasks=[{"name": "Design DB tables"}],
        deliverables=["schema.sql"],
    )
    await adapter.create_sprint(
        epic_id=epic.id,
        goal="Build login API",
        dependencies=["s-1"],
    )
    return adapter


class TestDirectoryStructure:
    @pytest.mark.asyncio
    async def test_creates_dirs_on_first_operation(self, adapter, tmp_path):
        await adapter.get_project_state()
        assert (tmp_path / ".maestro").is_dir()
        assert (tmp_path / ".maestro" / "epics").is_dir()
        assert (tmp_path / ".maestro" / "sprints").is_dir()

    @pytest.mark.asyncio
    async def test_state_json_created(self, adapter, tmp_path):
        await adapter.create_epic("Test", "Desc")
        assert (tmp_path / ".maestro" / "state.json").exists()


class TestEpicPersistence:
    @pytest.mark.asyncio
    async def test_create_and_read_back(self, adapter, tmp_path):
        epic = await adapter.create_epic("Marketing Campaign", "Launch Q1 campaign")
        assert epic.id == "e-1"
        assert epic.title == "Marketing Campaign"

        # Read back from a fresh adapter instance
        adapter2 = MaestroAdapter(tmp_path)
        epic2 = await adapter2.get_epic("e-1")
        assert epic2.title == "Marketing Campaign"
        assert epic2.description == "Launch Q1 campaign"

    @pytest.mark.asyncio
    async def test_epic_markdown_written(self, adapter, tmp_path):
        await adapter.create_epic("Auth", "Build auth")
        md_path = tmp_path / ".maestro" / "epics" / "e-1.md"
        assert md_path.exists()
        content = md_path.read_text()
        assert "# Auth" in content
        assert "Build auth" in content

    @pytest.mark.asyncio
    async def test_list_epics(self, seeded_adapter):
        epics = await seeded_adapter.list_epics()
        assert len(epics) == 1


class TestSprintPersistence:
    @pytest.mark.asyncio
    async def test_create_and_read_back(self, seeded_adapter, tmp_path):
        # Read back from fresh adapter
        adapter2 = MaestroAdapter(tmp_path)
        sprint = await adapter2.get_sprint("s-1")
        assert sprint.goal == "Design schema"
        assert sprint.epic_id == "e-1"

    @pytest.mark.asyncio
    async def test_sprint_markdown_written(self, seeded_adapter, tmp_path):
        md_path = tmp_path / ".maestro" / "sprints" / "s-1.md"
        assert md_path.exists()
        content = md_path.read_text()
        assert "Design schema" in content
        assert "Design DB tables" in content

    @pytest.mark.asyncio
    async def test_list_sprints_by_epic(self, seeded_adapter):
        sprints = await seeded_adapter.list_sprints(epic_id="e-1")
        assert len(sprints) == 2

    @pytest.mark.asyncio
    async def test_sprint_linked_to_epic(self, seeded_adapter):
        epic = await seeded_adapter.get_epic("e-1")
        assert "s-1" in epic.sprint_ids
        assert "s-2" in epic.sprint_ids


class TestStatusSummary:
    @pytest.mark.asyncio
    async def test_summary(self, seeded_adapter):
        summary = await seeded_adapter.get_status_summary()
        assert summary["total_epics"] == 1
        assert summary["total_sprints"] == 2
        assert summary["sprints_todo"] == 2
        assert summary["progress_pct"] == 0.0

    @pytest.mark.asyncio
    async def test_empty_project(self, adapter):
        summary = await adapter.get_status_summary()
        assert summary["total_sprints"] == 0
        assert summary["progress_pct"] == 0.0


class TestUpdateSprint:
    @pytest.mark.asyncio
    async def test_update_goal(self, seeded_adapter):
        from src.workflow.models import SprintStatus
        sprint = await seeded_adapter.update_sprint("s-1", status=SprintStatus.IN_PROGRESS)
        assert sprint.status is SprintStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_update_not_found(self, adapter):
        with pytest.raises(KeyError):
            await adapter.update_sprint("s-999", goal="nope")
