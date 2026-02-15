"""Unit tests for InMemoryAdapter."""

import pytest

from src.adapters.memory import InMemoryAdapter
from src.workflow.models import EpicStatus, SprintStatus


@pytest.fixture
def adapter():
    return InMemoryAdapter(project_name="test-project")


class TestCreateEpic:
    @pytest.mark.asyncio
    async def test_auto_increments_ids(self, adapter):
        e1 = await adapter.create_epic("First", "desc")
        e2 = await adapter.create_epic("Second", "desc")
        assert e1.id == "e-1"
        assert e2.id == "e-2"

    @pytest.mark.asyncio
    async def test_defaults_to_draft(self, adapter):
        e = await adapter.create_epic("Title", "desc")
        assert e.status is EpicStatus.DRAFT

    @pytest.mark.asyncio
    async def test_unicode_title(self, adapter):
        e = await adapter.create_epic("Diseño de interfaz 🎨", "Descripción en español")
        assert e.title == "Diseño de interfaz 🎨"

    @pytest.mark.asyncio
    async def test_empty_description(self, adapter):
        e = await adapter.create_epic("Title", "")
        assert e.description == ""


class TestCreateSprint:
    @pytest.mark.asyncio
    async def test_links_sprint_to_epic(self, adapter):
        epic = await adapter.create_epic("Epic", "desc")
        s = await adapter.create_sprint(epic.id, "Sprint goal")
        assert s.epic_id == epic.id
        assert s.id in epic.sprint_ids

    @pytest.mark.asyncio
    async def test_raises_on_missing_epic(self, adapter):
        with pytest.raises(KeyError, match="Epic not found"):
            await adapter.create_sprint("e-999", "goal")

    @pytest.mark.asyncio
    async def test_defaults_to_planned(self, adapter):
        epic = await adapter.create_epic("E", "d")
        s = await adapter.create_sprint(epic.id, "goal")
        assert s.status is SprintStatus.PLANNED

    @pytest.mark.asyncio
    async def test_with_all_optional_fields(self, adapter):
        epic = await adapter.create_epic("E", "d")
        s = await adapter.create_sprint(
            epic.id,
            "Build it",
            tasks=[{"name": "task1"}, {"name": "task2"}],
            dependencies=["s-0"],
            deliverables=["artifact.zip"],
        )
        assert len(s.tasks) == 2
        assert s.dependencies == ["s-0"]
        assert s.deliverables == ["artifact.zip"]


class TestListSprints:
    @pytest.mark.asyncio
    async def test_filter_by_epic(self, adapter):
        e1 = await adapter.create_epic("E1", "d")
        e2 = await adapter.create_epic("E2", "d")
        await adapter.create_sprint(e1.id, "S1")
        await adapter.create_sprint(e2.id, "S2")
        await adapter.create_sprint(e1.id, "S3")

        e1_sprints = await adapter.list_sprints(epic_id=e1.id)
        assert len(e1_sprints) == 2
        assert all(s.epic_id == e1.id for s in e1_sprints)

    @pytest.mark.asyncio
    async def test_list_all(self, adapter):
        e = await adapter.create_epic("E", "d")
        await adapter.create_sprint(e.id, "S1")
        await adapter.create_sprint(e.id, "S2")
        all_sprints = await adapter.list_sprints()
        assert len(all_sprints) == 2


class TestUpdateSprint:
    @pytest.mark.asyncio
    async def test_update_status(self, adapter):
        e = await adapter.create_epic("E", "d")
        s = await adapter.create_sprint(e.id, "goal")
        updated = await adapter.update_sprint(s.id, status=SprintStatus.IN_PROGRESS)
        assert updated.status is SprintStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_update_goal(self, adapter):
        e = await adapter.create_epic("E", "d")
        s = await adapter.create_sprint(e.id, "old goal")
        updated = await adapter.update_sprint(s.id, goal="new goal")
        assert updated.goal == "new goal"

    @pytest.mark.asyncio
    async def test_update_unknown_field_raises(self, adapter):
        e = await adapter.create_epic("E", "d")
        s = await adapter.create_sprint(e.id, "goal")
        with pytest.raises(ValueError, match="Unknown sprint field"):
            await adapter.update_sprint(s.id, nonexistent="value")

    @pytest.mark.asyncio
    async def test_update_not_found(self, adapter):
        with pytest.raises(KeyError):
            await adapter.update_sprint("s-999", goal="nope")


class TestGetProjectState:
    @pytest.mark.asyncio
    async def test_empty_project(self, adapter):
        state = await adapter.get_project_state()
        assert state.project_name == "test-project"
        assert state.epics == []
        assert state.sprints == []
        assert state.active_sprint_id is None

    @pytest.mark.asyncio
    async def test_detects_active_sprint(self, adapter):
        e = await adapter.create_epic("E", "d")
        s = await adapter.create_sprint(e.id, "goal")
        await adapter.update_sprint(s.id, status=SprintStatus.IN_PROGRESS)
        state = await adapter.get_project_state()
        assert state.active_sprint_id == s.id


class TestStatusSummary:
    @pytest.mark.asyncio
    async def test_progress_calculation(self, adapter):
        e = await adapter.create_epic("E", "d")
        s1 = await adapter.create_sprint(e.id, "S1")
        s2 = await adapter.create_sprint(e.id, "S2")
        await adapter.update_sprint(s1.id, status=SprintStatus.COMPLETED)

        summary = await adapter.get_status_summary()
        assert summary["sprints_completed"] == 1
        assert summary["sprints_planned"] == 1
        assert summary["progress_pct"] == 50.0

    @pytest.mark.asyncio
    async def test_zero_division_empty(self, adapter):
        summary = await adapter.get_status_summary()
        assert summary["progress_pct"] == 0.0
