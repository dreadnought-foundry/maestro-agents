"""Sprint 23: Validate Execution Agents & Lifecycle End-to-End tests.

Integration tests that validate the runner works with hooks, gates,
and agents together as a cohesive system.
"""

from __future__ import annotations

import pytest

from src.adapters.memory import InMemoryAdapter
from src.agents.execution.mocks import (
    MockProductEngineerAgent,
    MockQualityEngineerAgent,
    MockTestRunnerAgent,
)
from src.agents.execution.registry import AgentRegistry
from src.agents.execution.types import AgentResult
from src.execution.config import RunConfig
from src.execution.convenience import create_default_registry, create_hook_registry
from src.execution.gates import CoverageGate, QualityReviewGate, create_default_hooks
from src.execution.hooks import HookRegistry
from src.execution.runner import RunResult, SprintRunner
from src.workflow.models import SprintStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_sprint(tasks, goal="Test sprint"):
    """Create a backend with one epic and one sprint. Returns (backend, sprint_id)."""
    backend = InMemoryAdapter()
    epic = await backend.create_epic("E2E Epic", "Epic for validation tests")
    sprint = await backend.create_sprint(epic.id, goal, tasks=tasks)
    return backend, sprint.id


def _registry_for_types(mapping: dict) -> AgentRegistry:
    """Build an AgentRegistry from a {step_type: agent} mapping."""
    registry = AgentRegistry()
    for step_type, agent in mapping.items():
        registry.register(step_type, agent)
    return registry


# ---------------------------------------------------------------------------
# 1. Multi-type sprint (implement -> test -> review) — all succeed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_multi_type_sprint_with_hooks_all_succeed():
    """implement -> test -> review sprint completes through the integrated runner
    with hooks when all agents return successful results."""
    tasks = [{"name": "implement"}, {"name": "test"}, {"name": "review"}]
    backend, sprint_id = await _create_sprint(tasks)

    impl_agent = MockProductEngineerAgent()
    test_agent = MockTestRunnerAgent()
    review_agent = MockQualityEngineerAgent()

    registry = _registry_for_types({
        "implement": impl_agent,
        "test": test_agent,
        "review": review_agent,
    })

    hook_registry = create_hook_registry("backend")
    runner = SprintRunner(
        backend=backend,
        agent_registry=registry,
        hook_registry=hook_registry,
    )

    result = await runner.run(sprint_id)

    assert result.success is True
    assert result.steps_completed == 3
    assert result.steps_total == 3
    assert len(result.agent_results) == 3
    assert impl_agent.call_count == 1
    assert test_agent.call_count == 1
    assert review_agent.call_count == 1

    sprint = await backend.get_sprint(sprint_id)
    assert sprint.status is SprintStatus.DONE


# ---------------------------------------------------------------------------
# 2. Coverage gate blocks low-coverage sprint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_coverage_gate_blocks_low_coverage():
    """POST_STEP CoverageGate blocks the sprint when the test agent reports
    coverage below the threshold (50% < 80%)."""
    tasks = [{"name": "implement"}, {"name": "test"}]
    backend, sprint_id = await _create_sprint(tasks)

    low_coverage_result = AgentResult(
        success=True,
        output="Tests passed but low coverage",
        coverage=50.0,
    )
    impl_agent = MockProductEngineerAgent()
    test_agent = MockTestRunnerAgent(result=low_coverage_result)

    registry = _registry_for_types({
        "implement": impl_agent,
        "test": test_agent,
    })

    hook_registry = HookRegistry()
    hook_registry.register(CoverageGate(threshold=80.0))

    runner = SprintRunner(
        backend=backend,
        agent_registry=registry,
        hook_registry=hook_registry,
        config=RunConfig(max_retries=0, retry_delay_seconds=0.0),
    )

    result = await runner.run(sprint_id)

    assert result.success is False
    assert test_agent.call_count == 1
    sprint = await backend.get_sprint(sprint_id)
    assert sprint.status is SprintStatus.BLOCKED


# ---------------------------------------------------------------------------
# 3. Quality review gate blocks unapproved sprint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_quality_review_gate_blocks_unapproved():
    """PRE_COMPLETION QualityReviewGate blocks the sprint when no review agent
    has produced an 'approve' verdict."""
    tasks = [{"name": "implement"}, {"name": "test"}]
    backend, sprint_id = await _create_sprint(tasks)

    impl_agent = MockProductEngineerAgent()
    test_agent = MockTestRunnerAgent()

    registry = _registry_for_types({
        "implement": impl_agent,
        "test": test_agent,
    })

    # Only register the QualityReviewGate — no review agent in the pipeline
    hook_registry = HookRegistry()
    hook_registry.register(QualityReviewGate())

    runner = SprintRunner(
        backend=backend,
        agent_registry=registry,
        hook_registry=hook_registry,
        config=RunConfig(max_retries=0, retry_delay_seconds=0.0),
    )

    result = await runner.run(sprint_id)

    assert result.success is False
    sprint = await backend.get_sprint(sprint_id)
    assert sprint.status is SprintStatus.BLOCKED


# ---------------------------------------------------------------------------
# 4. Sprint with 10+ steps completes correctly
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_large_sprint_with_many_steps():
    """A sprint with 12 steps completes successfully, executing all agents."""
    tasks = [{"name": "implement"} for _ in range(12)]
    backend, sprint_id = await _create_sprint(tasks, goal="Large sprint")

    agent = MockProductEngineerAgent()
    registry = _registry_for_types({"implement": agent})

    runner = SprintRunner(backend=backend, agent_registry=registry)
    result = await runner.run(sprint_id)

    assert result.success is True
    assert result.steps_completed == 12
    assert result.steps_total == 12
    assert agent.call_count == 12
    assert len(result.agent_results) == 12


# ---------------------------------------------------------------------------
# 5. Empty sprint (no tasks) completes immediately
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_empty_sprint_completes_immediately():
    """A sprint with no tasks completes immediately with zero steps."""
    backend, sprint_id = await _create_sprint(tasks=[])

    registry = AgentRegistry()
    runner = SprintRunner(backend=backend, agent_registry=registry)

    result = await runner.run(sprint_id)

    assert result.success is True
    assert result.steps_completed == 0
    assert result.steps_total == 0
    assert len(result.agent_results) == 0

    sprint = await backend.get_sprint(sprint_id)
    assert sprint.status is SprintStatus.DONE


# ---------------------------------------------------------------------------
# 6. All deferred items from agents collected across mixed agent types
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_deferred_items_collected_across_mixed_agents():
    """Deferred items from implement, test, and review agents are all collected
    in the final RunResult."""
    tasks = [{"name": "implement"}, {"name": "test"}, {"name": "review"}]
    backend, sprint_id = await _create_sprint(tasks)

    impl_agent = MockProductEngineerAgent(
        result=AgentResult(
            success=True,
            output="done",
            deferred_items=["TODO: add error handling"],
        )
    )
    test_agent = MockTestRunnerAgent(
        result=AgentResult(
            success=True,
            output="tests pass",
            coverage=90.0,
            deferred_items=["TODO: add edge case tests", "TODO: add integration tests"],
        )
    )
    review_agent = MockQualityEngineerAgent(
        result=AgentResult(
            success=True,
            output="approved",
            review_verdict="approve",
            deferred_items=["TODO: improve docstrings"],
        )
    )

    registry = _registry_for_types({
        "implement": impl_agent,
        "test": test_agent,
        "review": review_agent,
    })

    runner = SprintRunner(backend=backend, agent_registry=registry)
    result = await runner.run(sprint_id)

    assert result.success is True
    assert len(result.deferred_items) == 4
    assert result.deferred_items == [
        "TODO: add error handling",
        "TODO: add edge case tests",
        "TODO: add integration tests",
        "TODO: improve docstrings",
    ]


# ---------------------------------------------------------------------------
# 7. create_default_registry agents handle all standard step types
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_default_registry_handles_all_standard_step_types():
    """create_default_registry() registers agents for implement, write_code,
    test, run_tests, review, and quality_review step types."""
    registry = create_default_registry()

    standard_types = ["implement", "write_code", "test", "run_tests", "review", "quality_review"]
    for step_type in standard_types:
        agent = registry.get_agent(step_type)
        assert agent is not None, f"No agent for step type '{step_type}'"

    # Verify each can actually execute
    for step_type in standard_types:
        backend = InMemoryAdapter()
        epic = await backend.create_epic("Test", "Test")
        sprint = await backend.create_sprint(epic.id, "goal", tasks=[{"name": step_type}])
        runner = SprintRunner(backend=backend, agent_registry=registry)

        result = await runner.run(sprint.id)
        assert result.success is True, f"Step type '{step_type}' did not succeed"
        assert result.steps_completed == 1


# ---------------------------------------------------------------------------
# 8. Previous outputs accumulate correctly across steps
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_previous_outputs_accumulate_across_steps():
    """Each successive step receives a growing list of previous_outputs from
    earlier steps."""
    tasks = [{"name": "implement"}, {"name": "test"}, {"name": "review"}]
    backend, sprint_id = await _create_sprint(tasks)

    result_1 = AgentResult(success=True, output="step-1-output")
    result_2 = AgentResult(success=True, output="step-2-output", coverage=95.0)
    result_3 = AgentResult(success=True, output="step-3-output", review_verdict="approve")

    agent_1 = MockProductEngineerAgent(result=result_1)
    agent_2 = MockTestRunnerAgent(result=result_2)
    agent_3 = MockQualityEngineerAgent(result=result_3)

    registry = _registry_for_types({
        "implement": agent_1,
        "test": agent_2,
        "review": agent_3,
    })

    runner = SprintRunner(backend=backend, agent_registry=registry)
    await runner.run(sprint_id)

    # First agent sees no previous outputs
    assert agent_1.last_context is not None
    assert len(agent_1.last_context.previous_outputs) == 0

    # Second agent sees one previous output (from step 1)
    assert agent_2.last_context is not None
    assert len(agent_2.last_context.previous_outputs) == 1
    assert agent_2.last_context.previous_outputs[0].output == "step-1-output"

    # Third agent sees two previous outputs (from steps 1 and 2)
    assert agent_3.last_context is not None
    assert len(agent_3.last_context.previous_outputs) == 2
    assert agent_3.last_context.previous_outputs[0].output == "step-1-output"
    assert agent_3.last_context.previous_outputs[1].output == "step-2-output"


# ---------------------------------------------------------------------------
# 9. Full lifecycle: create epic -> create sprint -> run -> verify DONE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_full_lifecycle_epic_to_done():
    """End-to-end lifecycle: create epic, create sprint, run through runner,
    and verify the sprint ends in DONE status with correct transitions."""
    backend = InMemoryAdapter()

    # Create epic
    epic = await backend.create_epic(
        "User Authentication",
        "Implement user auth for the platform",
    )
    assert epic.id is not None

    # Create sprint under the epic
    sprint = await backend.create_sprint(
        epic.id,
        "Build login flow",
        tasks=[
            {"name": "implement"},
            {"name": "test"},
            {"name": "review"},
        ],
    )
    assert sprint.status is SprintStatus.TODO

    # Set up agents and run
    registry = _registry_for_types({
        "implement": MockProductEngineerAgent(),
        "test": MockTestRunnerAgent(),
        "review": MockQualityEngineerAgent(),
    })

    runner = SprintRunner(backend=backend, agent_registry=registry)
    result = await runner.run(sprint.id)

    # Verify run result
    assert result.success is True
    assert result.steps_completed == 3
    assert result.steps_total == 3
    assert result.duration_seconds > 0

    # Verify final sprint state
    final_sprint = await backend.get_sprint(sprint.id)
    assert final_sprint.status is SprintStatus.DONE

    # Verify transitions: TODO -> IN_PROGRESS -> DONE
    assert len(final_sprint.transitions) == 2
    assert final_sprint.transitions[0].from_status is SprintStatus.TODO
    assert final_sprint.transitions[0].to_status is SprintStatus.IN_PROGRESS
    assert final_sprint.transitions[1].from_status is SprintStatus.IN_PROGRESS
    assert final_sprint.transitions[1].to_status is SprintStatus.DONE

    # Verify all steps are DONE
    step_status = await backend.get_step_status(sprint.id)
    for step_info in step_status["steps"]:
        assert step_info["status"] == "done"

    # Verify the epic still references the sprint
    refreshed_epic = await backend.get_epic(epic.id)
    assert sprint.id in refreshed_epic.sprint_ids


# ---------------------------------------------------------------------------
# 10. Runner with all hooks from create_default_hooks — happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_runner_with_all_default_hooks_happy_path():
    """Runner with the full set of default hooks (CoverageGate, QualityReviewGate,
    StepOrderingGate, RequiredStepsGate) passes the happy path when the test agent
    reports sufficient coverage and the review agent approves."""
    tasks = [{"name": "implement"}, {"name": "test"}, {"name": "review"}]
    backend, sprint_id = await _create_sprint(tasks, goal="Happy path with all hooks")

    impl_agent = MockProductEngineerAgent()
    test_agent = MockTestRunnerAgent(
        result=AgentResult(
            success=True,
            output="All tests passed",
            coverage=95.0,
        )
    )
    review_agent = MockQualityEngineerAgent(
        result=AgentResult(
            success=True,
            output="Looks great",
            review_verdict="approve",
        )
    )

    registry = _registry_for_types({
        "implement": impl_agent,
        "test": test_agent,
        "review": review_agent,
    })

    hook_registry = create_hook_registry("backend")
    runner = SprintRunner(
        backend=backend,
        agent_registry=registry,
        hook_registry=hook_registry,
    )

    result = await runner.run(sprint_id)

    assert result.success is True
    assert result.steps_completed == 3
    assert result.steps_total == 3
    assert impl_agent.call_count == 1
    assert test_agent.call_count == 1
    assert review_agent.call_count == 1

    sprint = await backend.get_sprint(sprint_id)
    assert sprint.status is SprintStatus.DONE
    assert result.duration_seconds > 0
