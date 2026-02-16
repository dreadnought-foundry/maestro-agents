"""TDD tests for sprint dependency checking."""

import pytest

from src.adapters.memory import InMemoryAdapter
from src.workflow.exceptions import DependencyNotMetError
from src.workflow.models import SprintStatus, Step, StepStatus
from src.execution.dependencies import (
    check_sprint_dependencies,
    validate_sprint_dependencies,
    validate_step_order,
)


@pytest.fixture
def adapter():
    return InMemoryAdapter(project_name="dep-test")


class TestDependencyNotMetError:
    def test_error_attributes(self):
        err = DependencyNotMetError("s-5", ["s-1", "s-3"])
        assert err.sprint_id == "s-5"
        assert err.unmet_dependencies == ["s-1", "s-3"]

    def test_error_message(self):
        err = DependencyNotMetError("s-5", ["s-1", "s-3"])
        msg = str(err)
        assert "s-5" in msg
        assert "s-1" in msg
        assert "s-3" in msg


class TestCheckSprintDependencies:
    @pytest.mark.asyncio
    async def test_no_dependencies_returns_empty(self, adapter):
        epic = await adapter.create_epic("Epic", "desc")
        sprint = await adapter.create_sprint(epic.id, "Sprint 1")
        result = await check_sprint_dependencies(sprint.id, adapter)
        assert result == []

    @pytest.mark.asyncio
    async def test_all_dependencies_met(self, adapter):
        epic = await adapter.create_epic("Epic", "desc")
        dep1 = await adapter.create_sprint(epic.id, "Dep 1")
        dep2 = await adapter.create_sprint(epic.id, "Dep 2")
        # Mark both deps as DONE
        dep1.status = SprintStatus.DONE
        dep2.status = SprintStatus.DONE
        sprint = await adapter.create_sprint(
            epic.id, "Main", dependencies=[dep1.id, dep2.id]
        )
        result = await check_sprint_dependencies(sprint.id, adapter)
        assert result == []

    @pytest.mark.asyncio
    async def test_unmet_dependencies(self, adapter):
        epic = await adapter.create_epic("Epic", "desc")
        dep1 = await adapter.create_sprint(epic.id, "Dep 1")
        dep2 = await adapter.create_sprint(epic.id, "Dep 2")
        # Both still TODO
        sprint = await adapter.create_sprint(
            epic.id, "Main", dependencies=[dep1.id, dep2.id]
        )
        result = await check_sprint_dependencies(sprint.id, adapter)
        assert set(result) == {dep1.id, dep2.id}

    @pytest.mark.asyncio
    async def test_mixed_dependencies(self, adapter):
        epic = await adapter.create_epic("Epic", "desc")
        dep1 = await adapter.create_sprint(epic.id, "Dep 1")
        dep2 = await adapter.create_sprint(epic.id, "Dep 2")
        dep1.status = SprintStatus.DONE
        # dep2 stays TODO
        sprint = await adapter.create_sprint(
            epic.id, "Main", dependencies=[dep1.id, dep2.id]
        )
        result = await check_sprint_dependencies(sprint.id, adapter)
        assert result == [dep2.id]


class TestValidateSprintDependencies:
    @pytest.mark.asyncio
    async def test_raises_when_unmet(self, adapter):
        epic = await adapter.create_epic("Epic", "desc")
        dep = await adapter.create_sprint(epic.id, "Dep 1")
        sprint = await adapter.create_sprint(
            epic.id, "Main", dependencies=[dep.id]
        )
        with pytest.raises(DependencyNotMetError) as exc_info:
            await validate_sprint_dependencies(sprint.id, adapter)
        assert exc_info.value.sprint_id == sprint.id
        assert dep.id in exc_info.value.unmet_dependencies

    @pytest.mark.asyncio
    async def test_no_raise_when_all_met(self, adapter):
        epic = await adapter.create_epic("Epic", "desc")
        dep = await adapter.create_sprint(epic.id, "Dep 1")
        dep.status = SprintStatus.DONE
        sprint = await adapter.create_sprint(
            epic.id, "Main", dependencies=[dep.id]
        )
        # Should not raise
        await validate_sprint_dependencies(sprint.id, adapter)


class TestValidateStepOrder:
    def test_first_step_always_valid(self):
        step1 = Step(id="step-1", name="First", status=StepStatus.TODO)
        step2 = Step(id="step-2", name="Second", status=StepStatus.TODO)
        from src.workflow.models import Sprint

        sprint = Sprint(
            id="s-1",
            goal="Goal",
            status=SprintStatus.IN_PROGRESS,
            epic_id="e-1",
            steps=[step1, step2],
        )
        assert validate_step_order(sprint, step1) is True

    def test_step_blocked_by_preceding(self):
        step1 = Step(id="step-1", name="First", status=StepStatus.TODO)
        step2 = Step(id="step-2", name="Second", status=StepStatus.TODO)
        from src.workflow.models import Sprint

        sprint = Sprint(
            id="s-1",
            goal="Goal",
            status=SprintStatus.IN_PROGRESS,
            epic_id="e-1",
            steps=[step1, step2],
        )
        assert validate_step_order(sprint, step2) is False
