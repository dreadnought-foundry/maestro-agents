"""Edge case and error path tests for tool handlers."""

import json
from typing import Any

import pytest
import pytest_asyncio

from src.adapters.memory import InMemoryAdapter
from src.tools.handlers import (
    create_epic_handler,
    create_sprint_handler,
    get_epic_handler,
    get_sprint_handler,
    list_sprints_handler,
)


@pytest.fixture
def backend():
    return InMemoryAdapter()


@pytest_asyncio.fixture
async def backend_with_epic(backend):
    await backend.create_epic("Test Epic", "Test description")
    return backend


def _parse(result: dict) -> Any:
    text = result["content"][0]["text"]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


class TestCreateSprintEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_goal(self, backend_with_epic):
        result = await create_sprint_handler(
            {"epic_id": "e-1", "goal": ""},
            backend_with_epic,
        )
        data = _parse(result)
        assert data["created"]["goal"] == ""

    @pytest.mark.asyncio
    async def test_unicode_goal(self, backend_with_epic):
        result = await create_sprint_handler(
            {"epic_id": "e-1", "goal": "Diseñar interfaz de usuario 日本語テスト"},
            backend_with_epic,
        )
        data = _parse(result)
        assert "Diseñar" in data["created"]["goal"]
        assert "日本語" in data["created"]["goal"]

    @pytest.mark.asyncio
    async def test_malformed_json_tasks_becomes_single_task(self, backend_with_epic):
        result = await create_sprint_handler(
            {"epic_id": "e-1", "goal": "test", "tasks": "{not valid json"},
            backend_with_epic,
        )
        data = _parse(result)
        assert data["created"]["tasks"] == [{"name": "{not valid json"}]

    @pytest.mark.asyncio
    async def test_malformed_json_dependencies_becomes_empty(self, backend_with_epic):
        result = await create_sprint_handler(
            {"epic_id": "e-1", "goal": "test", "dependencies": "not-json"},
            backend_with_epic,
        )
        data = _parse(result)
        assert data["created"]["dependencies"] == []

    @pytest.mark.asyncio
    async def test_malformed_json_deliverables_becomes_single(self, backend_with_epic):
        result = await create_sprint_handler(
            {"epic_id": "e-1", "goal": "test", "deliverables": "just a string"},
            backend_with_epic,
        )
        data = _parse(result)
        assert data["created"]["deliverables"] == ["just a string"]

    @pytest.mark.asyncio
    async def test_tasks_as_list_not_string(self, backend_with_epic):
        """When tasks is already a list (not JSON string), use directly."""
        result = await create_sprint_handler(
            {"epic_id": "e-1", "goal": "test", "tasks": [{"name": "direct"}]},
            backend_with_epic,
        )
        data = _parse(result)
        assert data["created"]["tasks"] == [{"name": "direct"}]

    @pytest.mark.asyncio
    async def test_very_long_goal(self, backend_with_epic):
        long_goal = "x" * 10000
        result = await create_sprint_handler(
            {"epic_id": "e-1", "goal": long_goal},
            backend_with_epic,
        )
        data = _parse(result)
        assert len(data["created"]["goal"]) == 10000


class TestCreateEpicEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_title(self, backend):
        result = await create_epic_handler(
            {"title": "", "description": "still has description"},
            backend,
        )
        data = _parse(result)
        assert data["created"]["title"] == ""

    @pytest.mark.asyncio
    async def test_special_characters_in_title(self, backend):
        result = await create_epic_handler(
            {"title": 'Epic with "quotes" & <tags>', "description": "desc"},
            backend,
        )
        data = _parse(result)
        assert '"quotes"' in data["created"]["title"]


class TestGetEpicErrors:
    @pytest.mark.asyncio
    async def test_empty_id(self, backend):
        result = await get_epic_handler({"epic_id": ""}, backend)
        text = result["content"][0]["text"]
        assert "Error" in text

    @pytest.mark.asyncio
    async def test_none_like_id(self, backend):
        result = await get_epic_handler({"epic_id": "null"}, backend)
        text = result["content"][0]["text"]
        assert "Error" in text


class TestGetSprintErrors:
    @pytest.mark.asyncio
    async def test_empty_id(self, backend):
        result = await get_sprint_handler({"sprint_id": ""}, backend)
        text = result["content"][0]["text"]
        assert "Error" in text


class TestListSprintsEdgeCases:
    @pytest.mark.asyncio
    async def test_no_epic_id_returns_all(self, backend_with_epic):
        await backend_with_epic.create_sprint("e-1", "S1")
        await backend_with_epic.create_sprint("e-1", "S2")
        result = await list_sprints_handler({}, backend_with_epic)
        data = _parse(result)
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_nonexistent_epic_returns_empty(self, backend_with_epic):
        result = await list_sprints_handler({"epic_id": "e-999"}, backend_with_epic)
        data = _parse(result)
        assert data == []
