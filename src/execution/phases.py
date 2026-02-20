"""Phase-based execution model for sprint runners.

Defines the six execution phases (PLAN, TDD, BUILD, VALIDATE, REVIEW, COMPLETE),
their configuration, and result types. Phases replace flat step iteration with
structured gates and artifact outputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine

from src.agents.execution.types import AgentResult


class Phase(Enum):
    """Execution phases in order."""

    PLAN = "plan"
    TDD = "tdd"
    BUILD = "build"
    VALIDATE = "validate"
    REVIEW = "review"
    COMPLETE = "complete"


# Canonical phase ordering
PHASE_ORDER: list[Phase] = [
    Phase.PLAN,
    Phase.TDD,
    Phase.BUILD,
    Phase.VALIDATE,
    Phase.REVIEW,
    Phase.COMPLETE,
]

# Gate callback type: async function(PhaseResult) -> (passed: bool, reason: str)
GateCheck = Callable[["PhaseResult"], Coroutine[Any, Any, tuple[bool, str]]]


@dataclass
class PhaseConfig:
    """Configuration for a single execution phase.

    Attributes:
        phase: Which phase this configures.
        agent_type: Step type name to look up in AgentRegistry (e.g. "implement", "test").
            None means no agent execution (e.g. REVIEW is human, COMPLETE is system).
            Used when steps is empty (single-agent phase).
        steps: Optional list of Steps for multi-step phases with dependency DAGs.
            When provided, the scheduler runs steps concurrently based on depends_on.
            Each step's metadata["type"] determines which agent to use.
        gate: Async callable that checks whether the phase's exit condition is met.
            Receives the PhaseResult and returns (passed, reason).
            None means no gate check — phase always passes.
        artifacts: List of artifact names this phase is expected to produce.
        required: If True, this phase cannot be skipped.
        max_retries: Max retries for agent execution within this phase.
    """

    phase: Phase
    agent_type: str | None = None
    steps: list[Any] | None = None  # list[Step] — deferred import to avoid circular
    gate: GateCheck | None = None
    artifacts: list[str] = field(default_factory=list)
    required: bool = True
    max_retries: int = 2


@dataclass
class PhaseResult:
    """Result of executing a single phase.

    Attributes:
        phase: Which phase produced this result.
        success: Whether the phase completed successfully.
        gate_passed: Whether the exit gate passed (None if no gate).
        gate_reason: Reason string from gate check.
        agent_results: Agent results produced during this phase.
        artifacts_produced: Names of artifacts actually generated.
        deferred_items: Deferred items collected during this phase.
    """

    phase: Phase
    success: bool
    gate_passed: bool | None = None
    gate_reason: str = ""
    agent_results: list[AgentResult] = field(default_factory=list)
    artifacts_produced: list[str] = field(default_factory=list)
    deferred_items: list[str] = field(default_factory=list)


def default_phase_configs() -> list[PhaseConfig]:
    """Return the default phase configuration for a standard sprint.

    PLAN uses 'planning' agent (PlanningAgent). BUILD uses 'implement'.
    TDD uses 'test' (write tests). VALIDATE uses 'test' (run tests).
    REVIEW has no agent (human checkpoint). COMPLETE has no agent (system).
    """
    return [
        PhaseConfig(
            phase=Phase.PLAN,
            agent_type="planning",
            artifacts=["contracts", "team_plan", "tdd_strategy", "coding_strategy", "context_brief"],
        ),
        PhaseConfig(
            phase=Phase.TDD,
            agent_type="test",
            artifacts=["test_files"],
        ),
        PhaseConfig(
            phase=Phase.BUILD,
            agent_type="implement",
            artifacts=["implementation_code"],
        ),
        PhaseConfig(
            phase=Phase.VALIDATE,
            agent_type="test",
            artifacts=["validation_report"],
        ),
        PhaseConfig(
            phase=Phase.REVIEW,
            agent_type=None,
            artifacts=[],
        ),
        PhaseConfig(
            phase=Phase.COMPLETE,
            agent_type=None,
            artifacts=["postmortem", "quality_report", "deferred_items"],
        ),
    ]
