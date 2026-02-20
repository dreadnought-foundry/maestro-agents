"""End-to-end integration tests for the unified sprint execution engine.

Tests the full lifecycle: create sprint → execute phases → review → complete,
using mock agents for fast execution.
"""

from __future__ import annotations

import pytest

from src.adapters.memory import InMemoryAdapter
from src.agents.execution.mocks import (
    MockPlanningAgent,
    MockProductEngineerAgent,
    MockTestRunnerAgent,
    MockValidationAgent,
)
from src.agents.execution.registry import AgentRegistry
from src.agents.execution.types import AgentResult
from src.execution.config import RunConfig
from src.execution.convenience import (
    create_test_registry,
    run_sprint,
)
from src.execution.phases import Phase, PhaseConfig, default_phase_configs
from src.execution.runner import SprintRunner
from src.workflow.models import SprintStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_backend_with_sprint(
    goal: str = "Build feature X",
    tasks: list[dict] | None = None,
    deliverables: list[str] | None = None,
) -> tuple[InMemoryAdapter, str]:
    """Create backend with one epic and one sprint, return (backend, sprint_id)."""
    backend = InMemoryAdapter()
    epic = await backend.create_epic("Test Epic", "End-to-end test epic")
    tasks = tasks or [{"name": "implement"}]
    sprint = await backend.create_sprint(
        epic.id, goal, tasks=tasks, deliverables=deliverables or [],
    )
    return backend, sprint.id


def _create_full_registry() -> AgentRegistry:
    """Create registry with all phase-required agents."""
    registry = AgentRegistry()
    registry.register("planning", MockPlanningAgent())
    registry.register("implement", MockProductEngineerAgent())
    registry.register("test", MockTestRunnerAgent())
    registry.register("validate", MockValidationAgent())
    registry.register("review", MockProductEngineerAgent())
    return registry


def _create_phased_runner(
    backend,
    registry: AgentRegistry | None = None,
    phase_configs: list[PhaseConfig] | None = None,
) -> SprintRunner:
    """Create a SprintRunner with phase-based execution."""
    if registry is None:
        registry = _create_full_registry()
    if phase_configs is None:
        phase_configs = default_phase_configs()
    return SprintRunner(
        backend=backend,
        agent_registry=registry,
        config=RunConfig(max_retries=0, retry_delay_seconds=0.0),
        phase_configs=phase_configs,
    )


# ---------------------------------------------------------------------------
# E2E: Full lifecycle with mock agents (fast)
# ---------------------------------------------------------------------------

class TestFullLifecycle:
    """Full sprint lifecycle: start → phases → review → complete."""

    async def test_sprint_runs_through_all_phases_to_review(self):
        backend, sprint_id = await _create_backend_with_sprint()
        runner = _create_phased_runner(backend)

        result = await runner.run(sprint_id)

        assert result.success is True
        assert result.stopped_at_review is True
        assert result.current_phase is Phase.REVIEW
        assert len(result.phase_results) == 4  # PLAN, TDD, BUILD, VALIDATE

        # Verify sprint status in backend
        sprint = await backend.get_sprint(sprint_id)
        assert sprint.status is SprintStatus.REVIEW

    async def test_phase_order_is_plan_tdd_build_validate(self):
        backend, sprint_id = await _create_backend_with_sprint()
        runner = _create_phased_runner(backend)

        result = await runner.run(sprint_id)

        phases = [pr.phase for pr in result.phase_results]
        assert phases == [Phase.PLAN, Phase.TDD, Phase.BUILD, Phase.VALIDATE]

    async def test_all_agents_called_once(self):
        backend, sprint_id = await _create_backend_with_sprint()

        planning = MockPlanningAgent()
        tdd = MockTestRunnerAgent()
        build = MockProductEngineerAgent()
        validate = MockValidationAgent()

        registry = AgentRegistry()
        registry.register("planning", planning)
        registry.register("test", tdd)
        registry.register("implement", build)
        registry.register("validate", validate)

        runner = _create_phased_runner(backend, registry=registry)
        await runner.run(sprint_id)

        assert planning.call_count == 1
        assert tdd.call_count == 1
        assert build.call_count == 1
        assert validate.call_count == 1

    async def test_agent_results_collected(self):
        backend, sprint_id = await _create_backend_with_sprint()
        runner = _create_phased_runner(backend)

        result = await runner.run(sprint_id)

        assert len(result.agent_results) == 4

    async def test_deferred_items_aggregated_across_phases(self):
        backend, sprint_id = await _create_backend_with_sprint()

        planning = MockPlanningAgent()
        build = MockProductEngineerAgent(
            result=AgentResult(
                success=True, output="built",
                deferred_items=["DEFER-1", "DEFER-2"],
            )
        )

        registry = AgentRegistry()
        registry.register("planning", planning)
        registry.register("test", MockTestRunnerAgent())
        registry.register("implement", build)
        registry.register("validate", MockValidationAgent())

        runner = _create_phased_runner(backend, registry=registry)
        result = await runner.run(sprint_id)

        assert "DEFER-1" in result.deferred_items
        assert "DEFER-2" in result.deferred_items

    async def test_progress_callback_reports_phases(self):
        backend, sprint_id = await _create_backend_with_sprint()
        runner = _create_phased_runner(backend)

        progress_log = []
        await runner.run(sprint_id, on_progress=lambda s: progress_log.append(s))

        assert len(progress_log) == 4
        assert progress_log[0]["current_phase"] == "plan"
        assert progress_log[3]["current_phase"] == "validate"


# ---------------------------------------------------------------------------
# E2E: Phase failure blocks sprint
# ---------------------------------------------------------------------------

class TestPhaseFailure:
    async def test_build_failure_blocks_at_build_phase(self):
        backend, sprint_id = await _create_backend_with_sprint()

        failing_build = MockProductEngineerAgent(
            result=AgentResult(success=False, output="Build failed: compile error")
        )

        registry = AgentRegistry()
        registry.register("planning", MockPlanningAgent())
        registry.register("test", MockTestRunnerAgent())
        registry.register("implement", failing_build)
        registry.register("validate", MockValidationAgent())

        runner = _create_phased_runner(backend, registry=registry)
        result = await runner.run(sprint_id)

        assert result.success is False
        assert result.current_phase is Phase.BUILD

        sprint = await backend.get_sprint(sprint_id)
        assert sprint.status is SprintStatus.BLOCKED

    async def test_validation_failure_blocks_before_review(self):
        backend, sprint_id = await _create_backend_with_sprint()

        failing_validator = MockValidationAgent(
            result=AgentResult(
                success=False, output="Tests failed",
                test_results={"total": 10, "passed": 3, "failed": 7, "errors": 0},
            )
        )

        registry = AgentRegistry()
        registry.register("planning", MockPlanningAgent())
        registry.register("test", MockTestRunnerAgent())
        registry.register("implement", MockProductEngineerAgent())
        registry.register("validate", failing_validator)

        runner = _create_phased_runner(backend, registry=registry)
        result = await runner.run(sprint_id)

        assert result.success is False
        assert result.current_phase is Phase.VALIDATE


# ---------------------------------------------------------------------------
# E2E: Rejection flow — reject → re-execute → complete
# ---------------------------------------------------------------------------

class TestRejectionFlow:
    async def test_reject_and_rerun(self):
        """Sprint reaches review, gets rejected, re-runs, reaches review again."""
        backend, sprint_id = await _create_backend_with_sprint()
        runner = _create_phased_runner(backend)

        # First run: reaches review
        result1 = await runner.run(sprint_id)
        assert result1.success is True
        assert result1.stopped_at_review is True

        sprint = await backend.get_sprint(sprint_id)
        assert sprint.status is SprintStatus.REVIEW

        # Reject: moves back to in-progress
        await backend.reject_sprint(sprint_id, "Need more test coverage")

        sprint = await backend.get_sprint(sprint_id)
        assert sprint.status is SprintStatus.IN_PROGRESS
        assert sprint.metadata["rejection_reason"] == "Need more test coverage"

        # Reset steps for re-run (steps are already DONE from first run)
        # The runner's start_sprint won't recreate steps, so we need fresh ones
        sprint.steps = []
        sprint.status = SprintStatus.TODO

        # Second run: reaches review again
        result2 = await runner.run(sprint_id)
        assert result2.success is True
        assert result2.stopped_at_review is True

    async def test_rejection_history_preserved(self):
        backend, sprint_id = await _create_backend_with_sprint()
        runner = _create_phased_runner(backend)

        # Run to review
        await runner.run(sprint_id)

        # Reject
        await backend.reject_sprint(sprint_id, "Missing feature Y")

        sprint = await backend.get_sprint(sprint_id)
        history = sprint.metadata.get("rejection_history", [])
        assert len(history) == 1
        assert history[0]["reason"] == "Missing feature Y"


# ---------------------------------------------------------------------------
# E2E: Convenience function integration
# ---------------------------------------------------------------------------

class TestConvenienceFunction:
    async def test_run_sprint_uses_phase_based_execution_by_default(self):
        backend, sprint_id = await _create_backend_with_sprint()

        result = await run_sprint(
            sprint_id,
            backend=backend,
            mock=True,
        )

        assert result.success is True
        assert result.stopped_at_review is True
        assert len(result.phase_results) == 4
        phases = [pr.phase for pr in result.phase_results]
        assert phases == [Phase.PLAN, Phase.TDD, Phase.BUILD, Phase.VALIDATE]

    async def test_run_sprint_with_mock_flag(self):
        backend, sprint_id = await _create_backend_with_sprint()

        result = await run_sprint(
            sprint_id,
            backend=backend,
            mock=True,
        )

        assert result.success is True

    async def test_run_sprint_progress_callback(self):
        backend, sprint_id = await _create_backend_with_sprint()

        progress_log = []
        await run_sprint(
            sprint_id,
            backend=backend,
            mock=True,
            on_progress=lambda s: progress_log.append(s),
        )

        assert len(progress_log) == 4
        assert progress_log[0]["current_phase"] == "plan"


# ---------------------------------------------------------------------------
# E2E: Sprint status transitions
# ---------------------------------------------------------------------------

class TestStatusTransitions:
    async def test_status_flow_todo_to_review(self):
        backend, sprint_id = await _create_backend_with_sprint()

        sprint = await backend.get_sprint(sprint_id)
        assert sprint.status is SprintStatus.TODO

        runner = _create_phased_runner(backend)
        await runner.run(sprint_id)

        sprint = await backend.get_sprint(sprint_id)
        assert sprint.status is SprintStatus.REVIEW

    async def test_failed_sprint_is_blocked(self):
        backend, sprint_id = await _create_backend_with_sprint()

        registry = AgentRegistry()
        registry.register("planning", MockPlanningAgent())
        # Deliberately fail at TDD
        registry.register("test", MockTestRunnerAgent(
            result=AgentResult(success=False, output="Could not write tests")
        ))
        registry.register("implement", MockProductEngineerAgent())
        registry.register("validate", MockValidationAgent())

        runner = _create_phased_runner(backend, registry=registry)
        result = await runner.run(sprint_id)

        assert result.success is False
        sprint = await backend.get_sprint(sprint_id)
        assert sprint.status is SprintStatus.BLOCKED

    async def test_complete_from_review(self):
        """After review, sprint can be completed via backend."""
        backend, sprint_id = await _create_backend_with_sprint()
        runner = _create_phased_runner(backend)

        await runner.run(sprint_id)

        sprint = await backend.get_sprint(sprint_id)
        assert sprint.status is SprintStatus.REVIEW

        # Complete the sprint (simulating human approval)
        await backend.complete_sprint(sprint_id)

        sprint = await backend.get_sprint(sprint_id)
        assert sprint.status is SprintStatus.DONE


# ---------------------------------------------------------------------------
# E2E: Default phase configs
# ---------------------------------------------------------------------------

class TestDefaultPhaseConfigs:
    def test_default_configs_have_all_phases(self):
        configs = default_phase_configs()
        phases = [c.phase for c in configs]
        assert phases == [
            Phase.PLAN, Phase.TDD, Phase.BUILD,
            Phase.VALIDATE, Phase.REVIEW, Phase.COMPLETE,
        ]

    def test_validate_uses_validate_agent(self):
        configs = default_phase_configs()
        validate_config = next(c for c in configs if c.phase is Phase.VALIDATE)
        assert validate_config.agent_type == "validate"

    def test_review_and_complete_have_no_agent(self):
        configs = default_phase_configs()
        review = next(c for c in configs if c.phase is Phase.REVIEW)
        complete = next(c for c in configs if c.phase is Phase.COMPLETE)
        assert review.agent_type is None
        assert complete.agent_type is None

    def test_plan_produces_artifacts(self):
        configs = default_phase_configs()
        plan = next(c for c in configs if c.phase is Phase.PLAN)
        assert "contracts" in plan.artifacts
        assert "team_plan" in plan.artifacts


# ---------------------------------------------------------------------------
# E2E: Test registry completeness
# ---------------------------------------------------------------------------

class TestRegistryCompleteness:
    def test_test_registry_has_all_phase_agents(self):
        """Verify test registry has agents for all phase_config agent_types."""
        registry = create_test_registry()
        configs = default_phase_configs()

        for config in configs:
            if config.agent_type is not None:
                agent = registry.get_agent(config.agent_type)
                assert agent is not None, f"Missing agent for {config.agent_type}"
