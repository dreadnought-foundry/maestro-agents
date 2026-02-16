"""Tests for workflow domain models."""

import pytest

from src.workflow.models import (
    Epic,
    EpicStatus,
    ProjectState,
    Sprint,
    SprintStatus,
)


class TestSprintStatus:
    def test_all_values(self):
        assert SprintStatus.BACKLOG.value == "backlog"
        assert SprintStatus.TODO.value == "todo"
        assert SprintStatus.IN_PROGRESS.value == "in_progress"
        assert SprintStatus.DONE.value == "done"
        assert SprintStatus.BLOCKED.value == "blocked"
        assert SprintStatus.ABANDONED.value == "abandoned"
        assert SprintStatus.ARCHIVED.value == "archived"

    def test_from_value(self):
        assert SprintStatus("todo") is SprintStatus.TODO


class TestEpicStatus:
    def test_all_values(self):
        assert EpicStatus.DRAFT.value == "draft"
        assert EpicStatus.ACTIVE.value == "active"
        assert EpicStatus.COMPLETED.value == "completed"


class TestSprint:
    def test_required_fields(self):
        s = Sprint(id="s-1", goal="Build auth", status=SprintStatus.TODO, epic_id="e-1")
        assert s.id == "s-1"
        assert s.goal == "Build auth"
        assert s.status is SprintStatus.TODO
        assert s.epic_id == "e-1"

    def test_defaults(self):
        s = Sprint(id="s-1", goal="x", status=SprintStatus.TODO, epic_id="e-1")
        assert s.tasks == []
        assert s.dependencies == []
        assert s.deliverables == []
        assert s.metadata == {}

    def test_with_all_fields(self):
        s = Sprint(
            id="s-1",
            goal="Build auth",
            status=SprintStatus.IN_PROGRESS,
            epic_id="e-1",
            tasks=[{"name": "Design schema"}],
            dependencies=["s-0"],
            deliverables=["auth module"],
            metadata={"type": "backend"},
        )
        assert len(s.tasks) == 1
        assert s.dependencies == ["s-0"]
        assert s.metadata["type"] == "backend"


class TestEpic:
    def test_required_fields(self):
        e = Epic(id="e-1", title="Auth", description="Authentication system", status=EpicStatus.DRAFT)
        assert e.id == "e-1"
        assert e.title == "Auth"

    def test_defaults(self):
        e = Epic(id="e-1", title="Auth", description="desc", status=EpicStatus.DRAFT)
        assert e.sprint_ids == []
        assert e.metadata == {}


class TestProjectState:
    def test_required_fields(self):
        p = ProjectState(project_name="test-project")
        assert p.project_name == "test-project"

    def test_defaults(self):
        p = ProjectState(project_name="test")
        assert p.epics == []
        assert p.sprints == []
        assert p.active_sprint_id is None
        assert p.metadata == {}

    def test_with_data(self):
        epic = Epic(id="e-1", title="Auth", description="desc", status=EpicStatus.ACTIVE)
        sprint = Sprint(id="s-1", goal="Build it", status=SprintStatus.TODO, epic_id="e-1")
        p = ProjectState(
            project_name="test",
            epics=[epic],
            sprints=[sprint],
            active_sprint_id="s-1",
        )
        assert len(p.epics) == 1
        assert len(p.sprints) == 1
        assert p.active_sprint_id == "s-1"
