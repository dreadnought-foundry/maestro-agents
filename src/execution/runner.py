"""Core sprint runner — orchestrates end-to-end sprint execution."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from src.agents.execution.registry import AgentRegistry
from src.agents.execution.types import AgentResult, StepContext
from src.execution.config import RunConfig
from src.execution.context_selector import select_context
from src.execution.dependencies import validate_sprint_dependencies
from src.execution.hooks import HookContext, HookPoint, HookRegistry, HookResult
from src.execution.phases import Phase, PhaseConfig, PhaseResult
from src.workflow.models import SprintStatus, StepStatus


@dataclass
class RunResult:
    sprint_id: str
    success: bool
    steps_completed: int
    steps_total: int
    agent_results: list[AgentResult] = field(default_factory=list)
    deferred_items: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    hook_results: dict[str, list[HookResult]] = field(default_factory=dict)
    phase_results: list[PhaseResult] = field(default_factory=list)
    current_phase: Phase | None = None
    stopped_at_review: bool = False


class SprintRunner:
    """Orchestrates end-to-end sprint execution."""

    def __init__(
        self,
        backend,
        agent_registry: AgentRegistry,
        project_root: Path | None = None,
        hook_registry: HookRegistry | None = None,
        config: RunConfig | None = None,
        artifact_dir: Path | None = None,
        kanban_dir: Path | None = None,
        synthesizer=None,
        phase_configs: list[PhaseConfig] | None = None,
    ):
        self._backend = backend
        self._registry = agent_registry
        self._project_root = project_root or Path(".")
        self._hooks = hook_registry
        self._config = config or RunConfig()
        self._artifact_dir = artifact_dir
        self._kanban_dir = kanban_dir
        self._synthesizer = synthesizer
        self._phase_configs = phase_configs

    async def _evaluate_hooks(
        self,
        point: HookPoint,
        context: HookContext,
        collected_hook_results: dict[str, list[HookResult]],
    ) -> bool:
        """Evaluate hooks at a given point. Returns False if a blocking hook failed."""
        if self._hooks is None:
            return True
        results = await self._hooks.evaluate_all(point, context)
        collected_hook_results.setdefault(point.name, []).extend(results)
        for result in results:
            if not result.passed and result.blocking:
                return False
        return True

    def _store_planning_artifacts(self, phase_result: PhaseResult, run_state: dict) -> None:
        """Parse planning artifacts from PLAN phase output and store in run_state."""
        from src.agents.execution.planning_agent import _parse_artifacts

        for ar in phase_result.agent_results:
            if ar.success and ar.output:
                artifacts = _parse_artifacts(ar.output)
                if artifacts.is_complete():
                    run_state["planning_artifacts"] = artifacts
                    return

    async def _generate_draft_quality_report(self, sprint, run_result: RunResult) -> None:
        """Generate a draft quality report when sprint enters review."""
        from src.execution.artifacts import ArtifactGenerator

        generator = ArtifactGenerator(sprint=sprint, run_result=run_result)
        quality_content = generator.generate_quality_report()

        # Write to sprint artifact dir if configured
        if self._artifact_dir is not None:
            self._artifact_dir.mkdir(parents=True, exist_ok=True)
            path = self._artifact_dir / f"{sprint.id}_quality.md"
            path.write_text(quality_content)

    async def _generate_artifacts(self, sprint, run_result: RunResult) -> None:
        """Generate artifact files if artifact_dir or kanban_dir are configured."""
        from src.execution.artifacts import ArtifactGenerator

        generator = ArtifactGenerator(sprint=sprint, run_result=run_result)

        if self._artifact_dir is not None:
            generator.write_sprint_artifacts(self._artifact_dir)

        if self._kanban_dir is not None:
            await generator.append_and_synthesize_deferred(
                self._kanban_dir, synthesizer=self._synthesizer
            )
            await generator.append_and_synthesize_postmortem(
                self._kanban_dir, synthesizer=self._synthesizer
            )

    async def run(
        self,
        sprint_id: str,
        on_progress: Callable | None = None,
    ) -> RunResult:
        """Run a sprint from start to completion.

        If phase_configs were provided, runs in phase-based mode.
        Otherwise, runs the original flat step loop for backwards compatibility.
        """
        if self._phase_configs is not None:
            return await self._run_phased(sprint_id, on_progress)
        return await self._run_flat(sprint_id, on_progress)

    # ------------------------------------------------------------------
    # Phase-based execution
    # ------------------------------------------------------------------

    async def _run_phased(
        self,
        sprint_id: str,
        on_progress: Callable | None = None,
    ) -> RunResult:
        """Run a sprint using phase-based execution."""
        start_time = time.monotonic()
        agent_results: list[AgentResult] = []
        deferred_items: list[str] = []
        hook_results: dict[str, list[HookResult]] = {}
        phase_results: list[PhaseResult] = []
        run_state: dict = {"agent_results": agent_results}

        # --- Dependency check ---
        await validate_sprint_dependencies(sprint_id, self._backend)

        # --- Load cumulative context ---
        cumulative_deferred = self._read_kanban_file("deferred.md")
        cumulative_postmortem = self._read_kanban_file("postmortem.md")

        # Start the sprint
        sprint = await self._backend.start_sprint(sprint_id)
        epic = await self._backend.get_epic(sprint.epic_id)

        # --- PRE_SPRINT hooks ---
        hook_ctx = HookContext(sprint=sprint, run_state=run_state)
        if not await self._evaluate_hooks(HookPoint.PRE_SPRINT, hook_ctx, hook_results):
            await self._backend.block_sprint(sprint_id, "PRE_SPRINT hook failed")
            return self._make_result(
                sprint_id, False, start_time, agent_results, deferred_items,
                hook_results, phase_results, current_phase=Phase.PLAN,
            )

        # --- Execute phases ---
        resume_phase = sprint.metadata.get("current_phase")
        started = False

        for phase_config in self._phase_configs:
            # Support resume: skip phases already completed
            if resume_phase is not None and not started:
                if phase_config.phase.value == resume_phase:
                    started = True
                else:
                    continue
            else:
                started = True

            # REVIEW phase: stop and transition to review status
            if phase_config.phase is Phase.REVIEW:
                # Advance all backend steps to DONE so move_to_review validation passes
                sprint = await self._backend.get_sprint(sprint_id)
                for step in sprint.steps:
                    if step.status is StepStatus.IN_PROGRESS:
                        await self._backend.advance_step(sprint_id, {"output": "phase-completed"})

                await self._backend.move_to_review(sprint_id)

                # Generate draft quality report
                sprint = await self._backend.get_sprint(sprint_id)
                elapsed = time.monotonic() - start_time
                step_status = await self._backend.get_step_status(sprint_id)
                run_result = RunResult(
                    sprint_id=sprint_id,
                    success=True,
                    steps_completed=step_status["completed_steps"],
                    steps_total=step_status["total_steps"],
                    agent_results=agent_results,
                    deferred_items=deferred_items,
                    duration_seconds=elapsed,
                    hook_results=hook_results,
                    phase_results=phase_results,
                    current_phase=Phase.REVIEW,
                    stopped_at_review=True,
                )
                await self._generate_draft_quality_report(sprint, run_result)
                return run_result

            # COMPLETE phase: generate artifacts, no agent
            if phase_config.phase is Phase.COMPLETE:
                phase_result = PhaseResult(
                    phase=Phase.COMPLETE,
                    success=True,
                    artifacts_produced=phase_config.artifacts,
                )
                phase_results.append(phase_result)
                continue

            # Execute phase with agent(s)
            if phase_config.agent_type is not None or phase_config.steps:
                phase_result = await self._execute_phase(
                    phase_config, sprint_id, sprint, epic,
                    agent_results, cumulative_deferred, cumulative_postmortem,
                    hook_results, run_state,
                )
                phase_results.append(phase_result)
                deferred_items.extend(phase_result.deferred_items)

                # After PLAN phase: parse and store planning artifacts
                if phase_config.phase is Phase.PLAN and phase_result.success:
                    self._store_planning_artifacts(phase_result, run_state)

                # Report progress
                if on_progress:
                    step_status = await self._backend.get_step_status(sprint_id)
                    step_status["current_phase"] = phase_config.phase.value
                    step_status["phases_completed"] = len(phase_results)
                    step_status["phases_total"] = len(self._phase_configs)
                    on_progress(step_status)

                if not phase_result.success:
                    await self._backend.block_sprint(
                        sprint_id,
                        f"Phase '{phase_config.phase.value}' failed: {phase_result.gate_reason or 'agent failure'}",
                    )
                    return self._make_result(
                        sprint_id, False, start_time, agent_results, deferred_items,
                        hook_results, phase_results, current_phase=phase_config.phase,
                    )

                # Check gate
                if phase_config.gate is not None:
                    gate_passed, gate_reason = await phase_config.gate(phase_result)
                    phase_result.gate_passed = gate_passed
                    phase_result.gate_reason = gate_reason
                    if not gate_passed:
                        phase_result.success = False
                        await self._backend.block_sprint(
                            sprint_id,
                            f"Gate failed for phase '{phase_config.phase.value}': {gate_reason}",
                        )
                        return self._make_result(
                            sprint_id, False, start_time, agent_results, deferred_items,
                            hook_results, phase_results, current_phase=phase_config.phase,
                        )

        # --- PRE_COMPLETION hooks ---
        sprint = await self._backend.get_sprint(sprint_id)
        hook_ctx = HookContext(sprint=sprint, run_state=run_state)
        if not await self._evaluate_hooks(HookPoint.PRE_COMPLETION, hook_ctx, hook_results):
            await self._backend.block_sprint(sprint_id, "PRE_COMPLETION hook failed")
            return self._make_result(
                sprint_id, False, start_time, agent_results, deferred_items,
                hook_results, phase_results,
            )

        # Advance all backend steps to DONE so complete_sprint validation passes
        sprint = await self._backend.get_sprint(sprint_id)
        for step in sprint.steps:
            if step.status is StepStatus.IN_PROGRESS:
                await self._backend.advance_step(sprint_id, {"output": "phase-completed"})

        # Complete
        await self._backend.complete_sprint(sprint_id)
        elapsed = time.monotonic() - start_time
        step_status = await self._backend.get_step_status(sprint_id)

        run_result = RunResult(
            sprint_id=sprint_id,
            success=True,
            steps_completed=step_status["completed_steps"],
            steps_total=step_status["total_steps"],
            agent_results=agent_results,
            deferred_items=deferred_items,
            duration_seconds=elapsed,
            hook_results=hook_results,
            phase_results=phase_results,
            current_phase=Phase.COMPLETE,
        )

        sprint = await self._backend.get_sprint(sprint_id)
        await self._generate_artifacts(sprint, run_result)

        # --- POST_COMPLETION hooks ---
        hook_ctx = HookContext(sprint=sprint, run_state=run_state)
        await self._evaluate_hooks(HookPoint.POST_COMPLETION, hook_ctx, hook_results)

        return run_result

    async def _execute_phase(
        self,
        phase_config: PhaseConfig,
        sprint_id: str,
        sprint,
        epic,
        agent_results: list[AgentResult],
        cumulative_deferred: str | None,
        cumulative_postmortem: str | None,
        hook_results: dict[str, list[HookResult]],
        run_state: dict,
    ) -> PhaseResult:
        """Execute a single phase.

        If phase_config.steps is provided, uses DAG-based parallel execution.
        Otherwise, dispatches a single agent for the phase.
        """
        if phase_config.steps:
            return await self._execute_phase_parallel(
                phase_config, sprint_id, sprint, epic,
                agent_results, cumulative_deferred, cumulative_postmortem,
                hook_results, run_state,
            )
        return await self._execute_phase_single(
            phase_config, sprint_id, sprint, epic,
            agent_results, cumulative_deferred, cumulative_postmortem,
            hook_results, run_state,
        )

    async def _execute_phase_single(
        self,
        phase_config: PhaseConfig,
        sprint_id: str,
        sprint,
        epic,
        agent_results: list[AgentResult],
        cumulative_deferred: str | None,
        cumulative_postmortem: str | None,
        hook_results: dict[str, list[HookResult]],
        run_state: dict,
    ) -> PhaseResult:
        """Execute a single-agent phase (original behavior)."""
        agent = self._registry.get_agent(phase_config.agent_type)

        from src.workflow.models import Step

        phase_step = Step(
            id=f"phase-{phase_config.phase.value}",
            name=phase_config.phase.value,
            status=StepStatus.IN_PROGRESS,
            metadata={"type": phase_config.agent_type, "phase": phase_config.phase.value},
        )

        selected = select_context(
            step_type=phase_config.agent_type,
            sprint_goal=sprint.goal,
            cumulative_deferred=cumulative_deferred,
            cumulative_postmortem=cumulative_postmortem,
        )

        context = StepContext(
            step=phase_step,
            sprint=sprint,
            epic=epic,
            project_root=self._project_root,
            previous_outputs=list(agent_results),
            cumulative_deferred=selected.deferred,
            cumulative_postmortem=selected.postmortem,
            planning_artifacts=run_state.get("planning_artifacts"),
        )

        max_retries = phase_config.max_retries
        result = await agent.execute(context)
        retries = 0
        while not result.success and retries < max_retries:
            if self._config.retry_delay_seconds > 0:
                await asyncio.sleep(self._config.retry_delay_seconds)
            result = await agent.execute(context)
            retries += 1

        agent_results.append(result)

        hook_ctx = HookContext(
            sprint=sprint,
            step=phase_step,
            agent_result=result,
            run_state=run_state,
        )
        hooks_ok = await self._evaluate_hooks(HookPoint.POST_STEP, hook_ctx, hook_results)

        return PhaseResult(
            phase=phase_config.phase,
            success=result.success and hooks_ok,
            agent_results=[result],
            artifacts_produced=phase_config.artifacts if result.success else [],
            deferred_items=list(result.deferred_items),
        )

    async def _execute_phase_parallel(
        self,
        phase_config: PhaseConfig,
        sprint_id: str,
        sprint,
        epic,
        agent_results: list[AgentResult],
        cumulative_deferred: str | None,
        cumulative_postmortem: str | None,
        hook_results: dict[str, list[HookResult]],
        run_state: dict,
    ) -> PhaseResult:
        """Execute a multi-step phase with DAG-based parallel scheduling."""
        from src.execution.scheduler import Scheduler

        scheduler = Scheduler(phase_config.steps)
        phase_agent_results: list[AgentResult] = []
        phase_deferred: list[str] = []
        all_hooks_ok = True

        while not scheduler.is_done():
            ready_steps = scheduler.get_ready_steps()
            if not ready_steps:
                break  # Deadlock — remaining steps have unmet deps due to failures

            for step in ready_steps:
                scheduler.mark_in_progress(step.id)

            async def _run_step(step):
                step_type = step.metadata.get("type", step.name)
                agent = self._registry.get_agent(step_type)

                selected = select_context(
                    step_type=step_type,
                    sprint_goal=sprint.goal,
                    cumulative_deferred=cumulative_deferred,
                    cumulative_postmortem=cumulative_postmortem,
                )

                context = StepContext(
                    step=step,
                    sprint=sprint,
                    epic=epic,
                    project_root=self._project_root,
                    previous_outputs=list(agent_results) + list(phase_agent_results),
                    cumulative_deferred=selected.deferred,
                    cumulative_postmortem=selected.postmortem,
                    planning_artifacts=run_state.get("planning_artifacts"),
                )

                max_retries = phase_config.max_retries
                result = await agent.execute(context)
                retries = 0
                while not result.success and retries < max_retries:
                    if self._config.retry_delay_seconds > 0:
                        await asyncio.sleep(self._config.retry_delay_seconds)
                    result = await agent.execute(context)
                    retries += 1

                return step.id, result

            # Run all ready steps concurrently
            results = await asyncio.gather(
                *[_run_step(step) for step in ready_steps],
                return_exceptions=True,
            )

            for item in results:
                if isinstance(item, Exception):
                    # Unexpected exception — treat as failure
                    all_hooks_ok = False
                    continue

                step_id, result = item
                phase_agent_results.append(result)
                agent_results.append(result)
                phase_deferred.extend(result.deferred_items)

                if result.success:
                    scheduler.mark_complete(step_id)
                else:
                    scheduler.mark_failed(step_id)

                # POST_STEP hook per step
                step_obj = next(s for s in phase_config.steps if s.id == step_id)
                hook_ctx = HookContext(
                    sprint=sprint,
                    step=step_obj,
                    agent_result=result,
                    run_state=run_state,
                )
                hooks_ok = await self._evaluate_hooks(HookPoint.POST_STEP, hook_ctx, hook_results)
                if not hooks_ok:
                    all_hooks_ok = False

        success = not scheduler.has_failures() and all_hooks_ok

        return PhaseResult(
            phase=phase_config.phase,
            success=success,
            agent_results=phase_agent_results,
            artifacts_produced=phase_config.artifacts if success else [],
            deferred_items=phase_deferred,
        )

    def _make_result(
        self,
        sprint_id: str,
        success: bool,
        start_time: float,
        agent_results: list[AgentResult],
        deferred_items: list[str],
        hook_results: dict[str, list[HookResult]],
        phase_results: list[PhaseResult],
        current_phase: Phase | None = None,
    ) -> RunResult:
        """Build a RunResult with current timing."""
        elapsed = time.monotonic() - start_time
        return RunResult(
            sprint_id=sprint_id,
            success=success,
            steps_completed=len([pr for pr in phase_results if pr.success]),
            steps_total=len(self._phase_configs) if self._phase_configs else 0,
            agent_results=agent_results,
            deferred_items=deferred_items,
            duration_seconds=elapsed,
            hook_results=hook_results,
            phase_results=phase_results,
            current_phase=current_phase,
        )

    # ------------------------------------------------------------------
    # Original flat-step execution (backwards compatible)
    # ------------------------------------------------------------------

    async def _run_flat(
        self,
        sprint_id: str,
        on_progress: Callable | None = None,
    ) -> RunResult:
        """Run a sprint using the original flat step loop."""
        start_time = time.monotonic()
        agent_results: list[AgentResult] = []
        deferred_items: list[str] = []
        hook_results: dict[str, list[HookResult]] = {}
        run_state: dict = {"agent_results": agent_results}

        # --- Dependency check ---
        await validate_sprint_dependencies(sprint_id, self._backend)

        # --- Load cumulative context from kanban files ---
        cumulative_deferred = self._read_kanban_file("deferred.md")
        cumulative_postmortem = self._read_kanban_file("postmortem.md")

        # Start the sprint (validates TODO -> IN_PROGRESS, creates steps)
        sprint = await self._backend.start_sprint(sprint_id)
        epic = await self._backend.get_epic(sprint.epic_id)

        # --- PRE_SPRINT hooks ---
        hook_ctx = HookContext(sprint=sprint, run_state=run_state)
        if not await self._evaluate_hooks(HookPoint.PRE_SPRINT, hook_ctx, hook_results):
            await self._backend.block_sprint(sprint_id, "PRE_SPRINT hook failed")
            elapsed = time.monotonic() - start_time
            step_status = await self._backend.get_step_status(sprint_id)
            result = RunResult(
                sprint_id=sprint_id,
                success=False,
                steps_completed=step_status["completed_steps"],
                steps_total=step_status["total_steps"],
                agent_results=agent_results,
                deferred_items=deferred_items,
                duration_seconds=elapsed,
                hook_results=hook_results,
            )
            sprint = await self._backend.get_sprint(sprint_id)
            await self._generate_artifacts(sprint, result)
            return result

        # Iterate through steps
        while True:
            status = await self._backend.get_step_status(sprint_id)
            current_step_name = status["current_step"]

            if current_step_name is None:
                break

            sprint = await self._backend.get_sprint(sprint_id)
            current_step = None
            for step in sprint.steps:
                if step.status is StepStatus.IN_PROGRESS:
                    current_step = step
                    break

            if current_step is None:
                break

            step_type = current_step.metadata.get("type", current_step.name)
            agent = self._registry.get_agent(step_type)

            # Filter cumulative context by relevance to this step
            selected = select_context(
                step_type=step_type,
                sprint_goal=sprint.goal,
                cumulative_deferred=cumulative_deferred,
                cumulative_postmortem=cumulative_postmortem,
            )

            context = StepContext(
                step=current_step,
                sprint=sprint,
                epic=epic,
                project_root=self._project_root,
                previous_outputs=list(agent_results),
                cumulative_deferred=selected.deferred,
                cumulative_postmortem=selected.postmortem,
            )

            result = await self._execute_with_retry(agent, context)
            agent_results.append(result)
            deferred_items.extend(result.deferred_items)

            # --- POST_STEP hooks ---
            hook_ctx = HookContext(
                sprint=sprint,
                step=current_step,
                agent_result=result,
                run_state=run_state,
            )
            if not await self._evaluate_hooks(HookPoint.POST_STEP, hook_ctx, hook_results):
                await self._backend.block_sprint(
                    sprint_id, f"POST_STEP hook failed for step '{current_step.name}'"
                )
                elapsed = time.monotonic() - start_time
                step_status = await self._backend.get_step_status(sprint_id)
                run_result = RunResult(
                    sprint_id=sprint_id,
                    success=False,
                    steps_completed=step_status["completed_steps"],
                    steps_total=step_status["total_steps"],
                    agent_results=agent_results,
                    deferred_items=deferred_items,
                    duration_seconds=elapsed,
                    hook_results=hook_results,
                )
                sprint = await self._backend.get_sprint(sprint_id)
                await self._generate_artifacts(sprint, run_result)
                return run_result

            if not result.success:
                await self._backend.block_sprint(
                    sprint_id, f"Step '{current_step.name}' failed: {result.output}"
                )
                elapsed = time.monotonic() - start_time
                step_status = await self._backend.get_step_status(sprint_id)
                run_result = RunResult(
                    sprint_id=sprint_id,
                    success=False,
                    steps_completed=step_status["completed_steps"],
                    steps_total=step_status["total_steps"],
                    agent_results=agent_results,
                    deferred_items=deferred_items,
                    duration_seconds=elapsed,
                    hook_results=hook_results,
                )
                sprint = await self._backend.get_sprint(sprint_id)
                await self._generate_artifacts(sprint, run_result)
                return run_result

            await self._backend.advance_step(sprint_id, {"output": result.output})

            if on_progress:
                step_status = await self._backend.get_step_status(sprint_id)
                on_progress(step_status)

        # --- PRE_COMPLETION hooks ---
        sprint = await self._backend.get_sprint(sprint_id)
        hook_ctx = HookContext(sprint=sprint, run_state=run_state)
        if not await self._evaluate_hooks(HookPoint.PRE_COMPLETION, hook_ctx, hook_results):
            await self._backend.block_sprint(
                sprint_id, "PRE_COMPLETION hook failed"
            )
            elapsed = time.monotonic() - start_time
            step_status = await self._backend.get_step_status(sprint_id)
            run_result = RunResult(
                sprint_id=sprint_id,
                success=False,
                steps_completed=step_status["completed_steps"],
                steps_total=step_status["total_steps"],
                agent_results=agent_results,
                deferred_items=deferred_items,
                duration_seconds=elapsed,
                hook_results=hook_results,
            )
            sprint = await self._backend.get_sprint(sprint_id)
            await self._generate_artifacts(sprint, run_result)
            return run_result

        # Move to review instead of completing directly
        await self._backend.move_to_review(sprint_id)
        elapsed = time.monotonic() - start_time
        step_status = await self._backend.get_step_status(sprint_id)

        run_result = RunResult(
            sprint_id=sprint_id,
            success=True,
            steps_completed=step_status["completed_steps"],
            steps_total=step_status["total_steps"],
            agent_results=agent_results,
            deferred_items=deferred_items,
            duration_seconds=elapsed,
            hook_results=hook_results,
            stopped_at_review=True,
        )

        # Generate artifacts and draft quality report for reviewer
        sprint = await self._backend.get_sprint(sprint_id)
        await self._generate_artifacts(sprint, run_result)
        await self._generate_draft_quality_report(sprint, run_result)

        return run_result

    def _read_kanban_file(self, filename: str) -> str | None:
        """Read a file from kanban_dir, returning None if unavailable."""
        if self._kanban_dir is None:
            return None
        path = self._kanban_dir / filename
        if not path.exists():
            return None
        content = path.read_text().strip()
        return content or None

    async def _execute_with_retry(self, agent, context: StepContext) -> AgentResult:
        """Execute an agent, retrying up to config.max_retries on failure."""
        result = await agent.execute(context)
        retries = 0
        while not result.success and retries < self._config.max_retries:
            if self._config.retry_delay_seconds > 0:
                await asyncio.sleep(self._config.retry_delay_seconds)
            result = await agent.execute(context)
            retries += 1
        return result
