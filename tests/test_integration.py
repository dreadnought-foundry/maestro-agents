"""Integration tests verifying the full pipeline works together.

Tests the agent definitions, MCP server factory, and adapter-through-handler flow.
Does NOT spawn actual Claude agents (that requires API access).
"""

import json
from typing import Any

import pytest
import pytest_asyncio

from src.adapters.maestro import MaestroAdapter
from src.adapters.memory import InMemoryAdapter
from src.agents.definitions import (
    ALL_AGENTS,
    TOOL_PREFIX,
    WORKFLOW_TOOLS,
    epic_breakdown_agent,
    research_agent,
    sprint_spec_agent,
    status_report_agent,
)
from src.tools.handlers import (
    create_epic_handler,
    create_sprint_handler,
    get_project_status_handler,
    get_sprint_handler,
    list_sprints_handler,
)
from src.tools.server import create_workflow_server
from src.workflow.models import SprintStatus


def _parse(result: dict) -> Any:
    text = result["content"][0]["text"]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


class TestAgentDefinitions:
    """Verify all agent definitions are valid and consistent."""

    def test_all_agents_present(self):
        assert len(ALL_AGENTS) == 4
        assert set(ALL_AGENTS.keys()) == {
            "epic_breakdown",
            "sprint_spec",
            "research",
            "status_report",
        }

    def test_all_agents_have_required_fields(self):
        for name, agent in ALL_AGENTS.items():
            assert agent.description, f"{name} missing description"
            assert agent.prompt, f"{name} missing prompt"
            assert agent.tools, f"{name} missing tools"
            assert agent.model, f"{name} missing model"

    def test_workflow_tool_references_are_valid(self):
        """All workflow tools referenced by agents should follow naming convention."""
        for name, agent in ALL_AGENTS.items():
            for tool_name in agent.tools:
                if tool_name.startswith(TOOL_PREFIX):
                    assert tool_name in WORKFLOW_TOOLS, (
                        f"Agent '{name}' references unknown tool: {tool_name}"
                    )

    def test_epic_breakdown_has_read_tool(self):
        assert "Read" in epic_breakdown_agent.tools

    def test_research_has_web_tools(self):
        assert "WebSearch" in research_agent.tools
        assert "WebFetch" in research_agent.tools

    def test_sprint_spec_only_has_workflow_tools(self):
        for t in sprint_spec_agent.tools:
            assert t.startswith(TOOL_PREFIX), f"Unexpected tool: {t}"

    def test_status_report_only_has_workflow_tools(self):
        for t in status_report_agent.tools:
            assert t.startswith(TOOL_PREFIX), f"Unexpected tool: {t}"

    def test_all_use_sonnet(self):
        for name, agent in ALL_AGENTS.items():
            assert agent.model == "sonnet", f"{name} uses {agent.model}, expected sonnet"


class TestMCPServerFactory:
    """Verify the server factory creates a valid server."""

    def test_creates_server(self):
        backend = InMemoryAdapter()
        server = create_workflow_server(backend)
        assert server is not None

    def test_creates_server_with_maestro_adapter(self, tmp_path):
        backend = MaestroAdapter(tmp_path)
        server = create_workflow_server(backend)
        assert server is not None


class TestFullPipeline:
    """End-to-end flow: handler → adapter → verify state."""

    @pytest.mark.asyncio
    async def test_create_epic_then_sprints_then_status(self):
        backend = InMemoryAdapter(project_name="pipeline-test")

        # Create an epic
        result = await create_epic_handler(
            {"title": "Marketing Launch", "description": "Q1 campaign"},
            backend,
        )
        epic_data = _parse(result)
        epic_id = epic_data["created"]["id"]

        # Create sprints
        for goal in ["Design landing page", "Write copy", "Set up analytics"]:
            await create_sprint_handler(
                {"epic_id": epic_id, "goal": goal},
                backend,
            )

        # Check status
        result = await get_project_status_handler({}, backend)
        status = _parse(result)
        assert status["total_epics"] == 1
        assert status["total_sprints"] == 3
        assert status["sprints_planned"] == 3
        assert status["progress_pct"] == 0.0

        # Complete one sprint
        sprints = await backend.list_sprints()
        await backend.update_sprint(sprints[0].id, status=SprintStatus.COMPLETED)

        # Verify progress updated
        result = await get_project_status_handler({}, backend)
        status = _parse(result)
        assert status["sprints_completed"] == 1
        assert status["progress_pct"] == pytest.approx(33.3, abs=0.1)

    @pytest.mark.asyncio
    async def test_pipeline_with_maestro_adapter(self, tmp_path):
        """Same flow but with file-based adapter."""
        backend = MaestroAdapter(tmp_path)

        result = await create_epic_handler(
            {"title": "Research", "description": "Market research"},
            backend,
        )
        epic_id = _parse(result)["created"]["id"]

        await create_sprint_handler(
            {
                "epic_id": epic_id,
                "goal": "Competitive analysis",
                "tasks": json.dumps([
                    {"name": "Identify competitors"},
                    {"name": "Compare features"},
                ]),
                "deliverables": json.dumps(["Research report"]),
            },
            backend,
        )

        # Verify files exist
        assert (tmp_path / ".maestro" / "state.json").exists()
        assert (tmp_path / ".maestro" / "epics" / "e-1.md").exists()
        assert (tmp_path / ".maestro" / "sprints" / "s-1.md").exists()

        # Read back from fresh adapter
        backend2 = MaestroAdapter(tmp_path)
        result = await get_sprint_handler({"sprint_id": "s-1"}, backend2)
        sprint_data = _parse(result)
        assert sprint_data["goal"] == "Competitive analysis"
        assert len(sprint_data["tasks"]) == 2

    @pytest.mark.asyncio
    async def test_multiple_epics_with_cross_references(self):
        """Sprints in different epics can reference each other via dependencies."""
        backend = InMemoryAdapter()

        e1 = await backend.create_epic("Backend", "API services")
        e2 = await backend.create_epic("Frontend", "Web UI")

        s1 = await backend.create_sprint(e1.id, "Build API", deliverables=["REST API"])
        s2 = await backend.create_sprint(
            e2.id, "Build UI", dependencies=[s1.id]
        )

        assert s2.dependencies == [s1.id]

        # List all sprints
        result = await list_sprints_handler({}, backend)
        all_sprints = _parse(result)
        assert len(all_sprints) == 2

        # Filter by epic
        result = await list_sprints_handler({"epic_id": e1.id}, backend)
        e1_sprints = _parse(result)
        assert len(e1_sprints) == 1
        assert e1_sprints[0]["goal"] == "Build API"
