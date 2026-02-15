"""Tests for custom tool functions from examples/02_custom_tools.py."""

import sys
from pathlib import Path

import pytest

# Add examples directory to path for imports
examples_dir = Path(__file__).parent.parent / "examples"
sys.path.insert(0, str(examples_dir))

# Import with the module name matching the filename (02_custom_tools)
import importlib.util
spec = importlib.util.spec_from_file_location(
    "custom_tools_module",
    examples_dir / "02_custom_tools.py"
)
custom_tools_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(custom_tools_module)

assign_task = custom_tools_module.assign_task_handler
get_team_members = custom_tools_module.get_team_members_handler


@pytest.mark.asyncio
async def test_get_team_members_returns_list():
    """Test that get_team_members returns expected team members."""
    result = await get_team_members({})

    assert "content" in result
    assert isinstance(result["content"], list)
    assert len(result["content"]) == 1
    assert result["content"][0]["type"] == "text"

    # Check that text contains team member information
    text = result["content"][0]["text"]
    assert "Alice" in text
    assert "Bob" in text
    assert "Carol" in text
    assert "backend" in text
    assert "frontend" in text
    assert "devops" in text


@pytest.mark.asyncio
async def test_get_team_members_structure():
    """Test that get_team_members returns proper structure."""
    result = await get_team_members({})

    # Verify the structure matches expected format
    assert isinstance(result, dict)
    assert "content" in result
    assert isinstance(result["content"], list)
    assert result["content"][0]["type"] == "text"
    assert isinstance(result["content"][0]["text"], str)


@pytest.mark.asyncio
async def test_assign_task_with_all_parameters():
    """Test assign_task with member, task, and priority."""
    args = {
        "member": "Alice",
        "task": "Review auth module",
        "priority": "high"
    }
    result = await assign_task(args)

    assert "content" in result
    assert isinstance(result["content"], list)
    assert len(result["content"]) == 1
    assert result["content"][0]["type"] == "text"

    text = result["content"][0]["text"]
    assert "Alice" in text
    assert "Review auth module" in text
    assert "high" in text
    assert "Assigned" in text


@pytest.mark.asyncio
async def test_assign_task_default_priority():
    """Test assign_task uses 'medium' as default priority."""
    args = {
        "member": "Bob",
        "task": "Fix bug #123"
    }
    result = await assign_task(args)

    text = result["content"][0]["text"]
    assert "Bob" in text
    assert "Fix bug #123" in text
    assert "medium" in text


@pytest.mark.asyncio
async def test_assign_task_various_priorities():
    """Test assign_task with different priority levels."""
    priorities = ["low", "medium", "high", "critical"]

    for priority in priorities:
        args = {
            "member": "Carol",
            "task": "Deploy to production",
            "priority": priority
        }
        result = await assign_task(args)
        text = result["content"][0]["text"]
        assert priority in text


@pytest.mark.asyncio
async def test_assign_task_return_structure():
    """Test assign_task returns proper structure."""
    args = {
        "member": "Alice",
        "task": "Write tests"
    }
    result = await assign_task(args)

    # Verify the structure matches expected format
    assert isinstance(result, dict)
    assert "content" in result
    assert isinstance(result["content"], list)
    assert result["content"][0]["type"] == "text"
    assert isinstance(result["content"][0]["text"], str)


@pytest.mark.asyncio
async def test_assign_task_with_special_characters():
    """Test assign_task handles special characters in task description."""
    args = {
        "member": "Bob",
        "task": "Fix bug: API endpoint /users/{id} returns 500",
        "priority": "high"
    }
    result = await assign_task(args)

    text = result["content"][0]["text"]
    assert "Bob" in text
    assert "/users/{id}" in text or "API endpoint" in text


@pytest.mark.asyncio
async def test_get_team_members_with_empty_args():
    """Test get_team_members works with empty arguments dictionary."""
    result = await get_team_members({})

    assert "content" in result
    assert len(result["content"]) > 0
