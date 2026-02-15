"""Tests for tool handler functions using InMemoryAdapter."""

import json
from typing import Any

import pytest
import pytest_asyncio

from src.adapters.memory import InMemoryAdapter
from src.tools.handlers import (
    create_epic_handler,
    create_sprint_handler,
    get_epic_handler,
    get_project_status_handler,
    get_sprint_handler,
    list_epics_handler,
    list_sprints_handler,
)


@pytest.fixture
def backend():
    return InMemoryAdapter(project_name="test-project")


@pytest_asyncio.fixture
async def seeded_backend(backend):
    """Backend with an epic and two sprints."""
    epic = await backend.create_epic("Auth System", "Build authentication")
    await backend.create_sprint(
        epic_id=epic.id,
        goal="Design auth schema",
        tasks=[{"name": "Design DB tables"}],
        deliverables=["schema.sql"],
    )
    await backend.create_sprint(
        epic_id=epic.id,
        goal="Implement login API",
        tasks=[{"name": "Build endpoint"}, {"name": "Add tests"}],
        dependencies=["s-1"],
        deliverables=["auth API"],
    )
    return backend


def _parse_result(result: dict) -> Any:
    """Extract and parse the text content from an MCP result."""
    text = result["content"][0]["text"]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


# --- get_project_status ---


class TestGetProjectStatus:
    @pytest.mark.asyncio
    async def test_empty_project(self, backend):
        result = await get_project_status_handler({}, backend)
        data = _parse_result(result)
        assert data["project_name"] == "test-project"
        assert data["total_epics"] == 0
        assert data["total_sprints"] == 0
        assert data["progress_pct"] == 0.0

    @pytest.mark.asyncio
    async def test_with_data(self, seeded_backend):
        result = await get_project_status_handler({}, seeded_backend)
        data = _parse_result(result)
        assert data["total_epics"] == 1
        assert data["total_sprints"] == 2
        assert data["sprints_planned"] == 2


# --- list_epics ---


class TestListEpics:
    @pytest.mark.asyncio
    async def test_empty(self, backend):
        result = await list_epics_handler({}, backend)
        data = _parse_result(result)
        assert data == []

    @pytest.mark.asyncio
    async def test_with_epics(self, seeded_backend):
        result = await list_epics_handler({}, seeded_backend)
        data = _parse_result(result)
        assert len(data) == 1
        assert data[0]["title"] == "Auth System"


# --- get_epic ---


class TestGetEpic:
    @pytest.mark.asyncio
    async def test_existing(self, seeded_backend):
        result = await get_epic_handler({"epic_id": "e-1"}, seeded_backend)
        data = _parse_result(result)
        assert data["title"] == "Auth System"
        assert len(data["sprint_ids"]) == 2

    @pytest.mark.asyncio
    async def test_not_found(self, backend):
        result = await get_epic_handler({"epic_id": "e-999"}, backend)
        text = result["content"][0]["text"]
        assert "Error" in text


# --- list_sprints ---


class TestListSprints:
    @pytest.mark.asyncio
    async def test_all_sprints(self, seeded_backend):
        result = await list_sprints_handler({}, seeded_backend)
        data = _parse_result(result)
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_filter_by_epic(self, seeded_backend):
        result = await list_sprints_handler({"epic_id": "e-1"}, seeded_backend)
        data = _parse_result(result)
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_filter_no_match(self, seeded_backend):
        result = await list_sprints_handler({"epic_id": "e-999"}, seeded_backend)
        data = _parse_result(result)
        assert data == []


# --- get_sprint ---


class TestGetSprint:
    @pytest.mark.asyncio
    async def test_existing(self, seeded_backend):
        result = await get_sprint_handler({"sprint_id": "s-1"}, seeded_backend)
        data = _parse_result(result)
        assert data["goal"] == "Design auth schema"
        assert len(data["deliverables"]) == 1

    @pytest.mark.asyncio
    async def test_not_found(self, backend):
        result = await get_sprint_handler({"sprint_id": "s-999"}, backend)
        text = result["content"][0]["text"]
        assert "Error" in text


# --- create_epic ---


class TestCreateEpic:
    @pytest.mark.asyncio
    async def test_create(self, backend):
        result = await create_epic_handler(
            {"title": "Marketing", "description": "Launch campaign"},
            backend,
        )
        data = _parse_result(result)
        assert data["created"]["title"] == "Marketing"
        assert data["created"]["id"] == "e-1"

        # Verify it persisted
        epics = await backend.list_epics()
        assert len(epics) == 1


# --- create_sprint ---


class TestCreateSprint:
    @pytest.mark.asyncio
    async def test_create_with_json_strings(self, seeded_backend):
        result = await create_sprint_handler(
            {
                "epic_id": "e-1",
                "goal": "Add OAuth",
                "tasks": json.dumps([{"name": "Integrate Google OAuth"}]),
                "dependencies": json.dumps(["s-2"]),
                "deliverables": json.dumps(["OAuth integration"]),
            },
            seeded_backend,
        )
        data = _parse_result(result)
        assert data["created"]["goal"] == "Add OAuth"
        assert data["created"]["dependencies"] == ["s-2"]

    @pytest.mark.asyncio
    async def test_create_minimal(self, seeded_backend):
        result = await create_sprint_handler(
            {"epic_id": "e-1", "goal": "Quick fix"},
            seeded_backend,
        )
        data = _parse_result(result)
        assert data["created"]["goal"] == "Quick fix"
        assert data["created"]["tasks"] == []

    @pytest.mark.asyncio
    async def test_create_invalid_epic(self, backend):
        result = await create_sprint_handler(
            {"epic_id": "e-999", "goal": "Orphan sprint"},
            backend,
        )
        text = result["content"][0]["text"]
        assert "Error" in text

    @pytest.mark.asyncio
    async def test_create_with_plain_text_tasks(self, seeded_backend):
        """If tasks is a plain string (not JSON), wrap it as a single task."""
        result = await create_sprint_handler(
            {"epic_id": "e-1", "goal": "Do stuff", "tasks": "Just one thing"},
            seeded_backend,
        )
        data = _parse_result(result)
        assert data["created"]["tasks"] == [{"name": "Just one thing"}]
