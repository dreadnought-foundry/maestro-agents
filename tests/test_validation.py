"""Tests for validation phase: report generation, gate enforcement, and agent wiring."""

from __future__ import annotations

import pytest

from src.adapters.memory import InMemoryAdapter
from src.agents.execution.mocks import MockProductEngineerAgent, MockValidationAgent
from src.agents.execution.registry import AgentRegistry
from src.agents.execution.types import AgentResult, StepContext
from src.execution.hooks import HookContext, HookPoint, HookResult
from src.execution.phases import Phase, PhaseConfig
from src.execution.runner import RunResult, SprintRunner
from src.execution.config import RunConfig
from src.execution.validation import (
    CheckSeverity,
    CheckStatus,
    ValidationCheck,
    ValidationGate,
    ValidationReport,
    build_report_from_agent_result,
)
from src.workflow.models import Epic, EpicStatus, Sprint, SprintStatus, Step


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _setup(tasks=None):
    backend = InMemoryAdapter()
    epic = await backend.create_epic("Test Epic", "An epic for testing")
    tasks = tasks or [{"name": "implement"}]
    sprint = await backend.create_sprint(epic.id, "Build feature", tasks=tasks)
    return backend, sprint.id


def _make_sprint(**kwargs) -> Sprint:
    defaults = dict(
        id="s1", epic_id="e1", goal="Test goal", status=SprintStatus.IN_PROGRESS,
        tasks=[], steps=[], deliverables=[],
    )
    defaults.update(kwargs)
    return Sprint(**defaults)


def _make_step(**kwargs) -> Step:
    defaults = dict(id="step1", name="validate")
    defaults["metadata"] = kwargs.pop("metadata", {"phase": "validate"})
    defaults.update(kwargs)
    return Step(**defaults)


# ---------------------------------------------------------------------------
# ValidationReport unit tests
# ---------------------------------------------------------------------------

class TestValidationReport:
    def test_empty_report_passes(self):
        report = ValidationReport()
        assert report.passed is True
        assert report.critical_failures == []
        assert report.all_failures == []

    def test_all_passing_checks(self):
        report = ValidationReport(checks=[
            ValidationCheck("Tests", CheckStatus.PASS, CheckSeverity.CRITICAL),
            ValidationCheck("Coverage", CheckStatus.PASS, CheckSeverity.MAJOR),
        ])
        assert report.passed is True

    def test_critical_failure_blocks(self):
        report = ValidationReport(checks=[
            ValidationCheck("Tests", CheckStatus.FAIL, CheckSeverity.CRITICAL, message="2 tests failed"),
        ])
        assert report.passed is False
        assert len(report.critical_failures) == 1
        assert report.critical_failures[0].name == "Tests"

    def test_major_failure_blocks(self):
        report = ValidationReport(checks=[
            ValidationCheck("Coverage", CheckStatus.FAIL, CheckSeverity.MAJOR),
        ])
        assert report.passed is False

    def test_minor_failure_does_not_block(self):
        report = ValidationReport(checks=[
            ValidationCheck("Style", CheckStatus.FAIL, CheckSeverity.MINOR),
        ])
        assert report.passed is True

    def test_info_failure_does_not_block(self):
        report = ValidationReport(checks=[
            ValidationCheck("Docs", CheckStatus.FAIL, CheckSeverity.INFO),
        ])
        assert report.passed is True

    def test_warn_does_not_block(self):
        report = ValidationReport(checks=[
            ValidationCheck("Coverage", CheckStatus.WARN, CheckSeverity.MAJOR),
        ])
        assert report.passed is True

    def test_all_failures_returns_all_failed(self):
        report = ValidationReport(checks=[
            ValidationCheck("A", CheckStatus.PASS, CheckSeverity.CRITICAL),
            ValidationCheck("B", CheckStatus.FAIL, CheckSeverity.CRITICAL),
            ValidationCheck("C", CheckStatus.FAIL, CheckSeverity.MINOR),
            ValidationCheck("D", CheckStatus.SKIP, CheckSeverity.MAJOR),
        ])
        assert len(report.all_failures) == 2
        names = [c.name for c in report.all_failures]
        assert "B" in names
        assert "C" in names

    def test_to_markdown_includes_summary(self):
        report = ValidationReport(checks=[
            ValidationCheck("Tests", CheckStatus.PASS, CheckSeverity.CRITICAL, message="10 passed"),
        ])
        md = report.to_markdown()
        assert "Validation Report" in md
        assert "PASS" in md
        assert "1/1 passed" in md

    def test_to_markdown_includes_test_results(self):
        report = ValidationReport(
            test_results={"total": 20, "passed": 18, "failed": 2, "errors": 0},
            coverage=85.5,
        )
        md = report.to_markdown()
        assert "Test Suite" in md
        assert "Total: 20" in md
        assert "Coverage: 85.5%" in md

    def test_to_markdown_includes_acceptance_criteria(self):
        report = ValidationReport(
            acceptance_criteria={"API works": True, "UI renders": False},
        )
        md = report.to_markdown()
        assert "Acceptance Criteria" in md
        assert "API works" in md
        assert "UI renders" in md


# ---------------------------------------------------------------------------
# build_report_from_agent_result
# ---------------------------------------------------------------------------

class TestBuildReport:
    def test_passing_tests_produce_pass_check(self):
        result = AgentResult(
            success=True,
            output="All tests passed",
            test_results={"total": 10, "passed": 10, "failed": 0, "errors": 0},
            coverage=90.0,
        )
        report = build_report_from_agent_result(result)
        assert report.passed is True
        assert any(c.name == "Test Suite" and c.status is CheckStatus.PASS for c in report.checks)

    def test_failing_tests_produce_fail_check(self):
        result = AgentResult(
            success=False,
            output="Tests failed",
            test_results={
                "total": 10, "passed": 8, "failed": 2, "errors": 0,
                "failed_tests": ["test_a", "test_b"],
            },
        )
        report = build_report_from_agent_result(result)
        assert report.passed is False
        test_check = next(c for c in report.checks if c.name == "Test Suite")
        assert test_check.status is CheckStatus.FAIL
        assert test_check.severity is CheckSeverity.CRITICAL

    def test_coverage_included_in_report(self):
        result = AgentResult(success=True, output="ok", coverage=80.0)
        report = build_report_from_agent_result(result)
        cov_check = next(c for c in report.checks if c.name == "Code Coverage")
        assert cov_check.status is CheckStatus.PASS
        assert "80.0%" in cov_check.message

    def test_low_coverage_produces_warning(self):
        result = AgentResult(success=True, output="ok", coverage=50.0)
        report = build_report_from_agent_result(result)
        cov_check = next(c for c in report.checks if c.name == "Code Coverage")
        assert cov_check.status is CheckStatus.WARN

    def test_no_test_results_produces_empty_report(self):
        result = AgentResult(success=True, output="ok")
        report = build_report_from_agent_result(result)
        assert report.passed is True
        assert len(report.checks) == 0

    def test_errors_count_as_failures(self):
        result = AgentResult(
            success=False,
            output="Errors",
            test_results={"total": 5, "passed": 4, "failed": 0, "errors": 1},
        )
        report = build_report_from_agent_result(result)
        assert report.passed is False


# ---------------------------------------------------------------------------
# ValidationGate (POST_STEP hook)
# ---------------------------------------------------------------------------

class TestValidationGate:
    @pytest.fixture
    def gate(self):
        return ValidationGate()

    async def test_no_agent_result_passes(self, gate):
        ctx = HookContext(sprint=_make_sprint(), step=_make_step(), agent_result=None)
        result = await gate.evaluate(ctx)
        assert result.passed is True

    async def test_no_step_passes(self, gate):
        ctx = HookContext(sprint=_make_sprint(), step=None)
        result = await gate.evaluate(ctx)
        assert result.passed is True

    async def test_non_validation_step_passes(self, gate):
        step = _make_step(name="build", metadata={"phase": "build", "type": "build"})
        agent_result = AgentResult(
            success=False, output="fail",
            test_results={"total": 1, "passed": 0, "failed": 1, "errors": 0},
        )
        ctx = HookContext(sprint=_make_sprint(), step=step, agent_result=agent_result)
        result = await gate.evaluate(ctx)
        assert result.passed is True  # Not a validation step, gate doesn't apply

    async def test_passing_validation_passes_gate(self, gate):
        step = _make_step(metadata={"phase": "validate"})
        agent_result = AgentResult(
            success=True, output="ok",
            test_results={"total": 10, "passed": 10, "failed": 0, "errors": 0},
            coverage=90.0,
        )
        ctx = HookContext(sprint=_make_sprint(), step=step, agent_result=agent_result)
        result = await gate.evaluate(ctx)
        assert result.passed is True

    async def test_critical_failure_blocks_gate(self, gate):
        step = _make_step(metadata={"phase": "validate"})
        agent_result = AgentResult(
            success=False, output="fail",
            test_results={"total": 10, "passed": 5, "failed": 5, "errors": 0,
                          "failed_tests": ["test_1", "test_2"]},
        )
        ctx = HookContext(sprint=_make_sprint(), step=step, agent_result=agent_result)
        result = await gate.evaluate(ctx)
        assert result.passed is False
        assert result.blocking is True
        assert "critical" in result.message.lower() or "Test Suite" in result.message

    async def test_step_type_validate_triggers_gate(self, gate):
        step = _make_step(name="validate", metadata={"type": "validate"})
        agent_result = AgentResult(
            success=True, output="ok",
            test_results={"total": 5, "passed": 5, "failed": 0, "errors": 0},
        )
        ctx = HookContext(sprint=_make_sprint(), step=step, agent_result=agent_result)
        result = await gate.evaluate(ctx)
        assert result.passed is True

    async def test_step_type_validation_triggers_gate(self, gate):
        step = _make_step(name="validation", metadata={"type": "validation"})
        agent_result = AgentResult(
            success=True, output="ok",
            test_results={"total": 5, "passed": 5, "failed": 0, "errors": 0},
        )
        ctx = HookContext(sprint=_make_sprint(), step=step, agent_result=agent_result)
        result = await gate.evaluate(ctx)
        assert result.passed is True


# ---------------------------------------------------------------------------
# MockValidationAgent
# ---------------------------------------------------------------------------

class TestMockValidationAgent:
    async def test_default_result_is_passing(self):
        agent = MockValidationAgent()
        sprint = _make_sprint()
        epic = Epic(id="e1", title="Test", description="test", status=EpicStatus.ACTIVE)
        ctx = StepContext(
            sprint=sprint, epic=epic, step=Step(id="v1", name="validate"),
            project_root=".", previous_outputs=[], cumulative_deferred="",
        )
        result = await agent.execute(ctx)
        assert result.success is True
        assert "VALIDATION_RESULT: PASS" in result.output
        assert agent.call_count == 1

    async def test_custom_failing_result(self):
        agent = MockValidationAgent(result=AgentResult(
            success=False,
            output="VALIDATION_RESULT: FAIL",
            test_results={"total": 10, "passed": 5, "failed": 5, "errors": 0},
        ))
        sprint = _make_sprint()
        epic = Epic(id="e1", title="Test", description="test", status=EpicStatus.ACTIVE)
        ctx = StepContext(
            sprint=sprint, epic=epic, step=Step(id="v1", name="validate"),
            project_root=".", previous_outputs=[], cumulative_deferred="",
        )
        result = await agent.execute(ctx)
        assert result.success is False
        assert agent.call_count == 1


# ---------------------------------------------------------------------------
# Integration: ValidationAgent prompt building
# ---------------------------------------------------------------------------

class TestValidationAgentPrompt:
    def test_prompt_includes_sprint_goal(self):
        from src.agents.execution.validation_agent import ValidationAgent
        agent = ValidationAgent(test_command="pytest")
        sprint = _make_sprint(
            goal="Build validation system",
            tasks=[{"name": "Create report generator"}, {"name": "Wire gate"}],
            deliverables=["validation.py", "tests/test_validation.py"],
        )
        epic = Epic(id="e1", title="Validation Epic", description="test", status=EpicStatus.ACTIVE)
        ctx = StepContext(
            sprint=sprint, epic=epic, step=Step(id="v1", name="validate"),
            project_root=".", previous_outputs=[], cumulative_deferred="",
        )
        prompt = agent._build_prompt(ctx)
        assert "Build validation system" in prompt
        assert "Validation Epic" in prompt
        assert "Create report generator" in prompt
        assert "Wire gate" in prompt
        assert "validation.py" in prompt

    def test_prompt_includes_previous_outputs(self):
        from src.agents.execution.validation_agent import ValidationAgent
        agent = ValidationAgent()
        sprint = _make_sprint()
        epic = Epic(id="e1", title="T", description="t", status=EpicStatus.ACTIVE)
        prev = [
            AgentResult(success=True, output="Plan done"),
            AgentResult(success=True, output="Tests written"),
        ]
        ctx = StepContext(
            sprint=sprint, epic=epic, step=Step(id="v1", name="validate"),
            project_root=".", previous_outputs=prev, cumulative_deferred="TODO-1",
        )
        prompt = agent._build_prompt(ctx)
        assert "Phase 1: PASS" in prompt
        assert "Phase 2: PASS" in prompt
        assert "TODO-1" in prompt

    async def test_execute_without_executor_raises(self):
        from src.agents.execution.validation_agent import ValidationAgent
        agent = ValidationAgent()
        sprint = _make_sprint()
        epic = Epic(id="e1", title="T", description="t", status=EpicStatus.ACTIVE)
        ctx = StepContext(
            sprint=sprint, epic=epic, step=Step(id="v1", name="validate"),
            project_root=".", previous_outputs=[], cumulative_deferred="",
        )
        result = await agent.execute(ctx)
        assert result.success is False
        assert "No ClaudeCodeExecutor" in result.output


# ---------------------------------------------------------------------------
# Integration: Validation in phase runner
# ---------------------------------------------------------------------------

class TestValidationInRunner:
    async def test_validation_phase_runs_in_pipeline(self):
        backend, sprint_id = await _setup()

        registry = AgentRegistry()
        registry.register("plan", MockProductEngineerAgent())
        registry.register("tdd", MockProductEngineerAgent())
        registry.register("build", MockProductEngineerAgent())
        registry.register("validate", MockValidationAgent())

        phase_configs = [
            PhaseConfig(phase=Phase.PLAN, agent_type="plan"),
            PhaseConfig(phase=Phase.TDD, agent_type="tdd"),
            PhaseConfig(phase=Phase.BUILD, agent_type="build"),
            PhaseConfig(phase=Phase.VALIDATE, agent_type="validate"),
            PhaseConfig(phase=Phase.REVIEW, agent_type=None),
        ]
        runner = SprintRunner(
            backend=backend,
            agent_registry=registry,
            config=RunConfig(max_retries=0, retry_delay_seconds=0.0),
            phase_configs=phase_configs,
        )

        result = await runner.run(sprint_id)
        assert result.success is True
        assert result.stopped_at_review is True
        assert len(result.phase_results) == 4

    async def test_failing_validation_blocks_review(self):
        backend, sprint_id = await _setup()

        failing_validator = MockValidationAgent(result=AgentResult(
            success=False,
            output="VALIDATION_RESULT: FAIL",
            test_results={"total": 10, "passed": 5, "failed": 5, "errors": 0},
        ))

        registry = AgentRegistry()
        registry.register("plan", MockProductEngineerAgent())
        registry.register("tdd", MockProductEngineerAgent())
        registry.register("build", MockProductEngineerAgent())
        registry.register("validate", failing_validator)

        phase_configs = [
            PhaseConfig(phase=Phase.PLAN, agent_type="plan", max_retries=0),
            PhaseConfig(phase=Phase.TDD, agent_type="tdd", max_retries=0),
            PhaseConfig(phase=Phase.BUILD, agent_type="build", max_retries=0),
            PhaseConfig(phase=Phase.VALIDATE, agent_type="validate", max_retries=0),
            PhaseConfig(phase=Phase.REVIEW, agent_type=None),
        ]
        runner = SprintRunner(
            backend=backend,
            agent_registry=registry,
            config=RunConfig(max_retries=0, retry_delay_seconds=0.0),
            phase_configs=phase_configs,
        )

        result = await runner.run(sprint_id)
        assert result.success is False
        assert result.current_phase is Phase.VALIDATE


# ---------------------------------------------------------------------------
# Quality report generation stub
# ---------------------------------------------------------------------------

class TestQualityReportGeneration:
    def test_validation_report_to_markdown_is_complete(self):
        report = ValidationReport(
            checks=[
                ValidationCheck("Test Suite", CheckStatus.PASS, CheckSeverity.CRITICAL, message="10 passed"),
                ValidationCheck("Coverage", CheckStatus.WARN, CheckSeverity.MAJOR, message="72%"),
                ValidationCheck("API Contracts", CheckStatus.PASS, CheckSeverity.MAJOR, message="All endpoints match"),
                ValidationCheck("Docs", CheckStatus.SKIP, CheckSeverity.INFO),
            ],
            test_results={"total": 10, "passed": 10, "failed": 0, "errors": 0},
            coverage=72.0,
            acceptance_criteria={
                "Full test suite runs": True,
                "Service health check": True,
                "API contracts verified": True,
            },
        )
        md = report.to_markdown()
        assert "Validation Report" in md
        assert "PASS" in md
        assert "Test Suite" in md
        assert "Coverage: 72.0%" in md
        assert "Full test suite runs" in md
        assert "API contracts verified" in md
        assert "2/4 passed" in md  # 2 PASS, 1 WARN, 1 SKIP
