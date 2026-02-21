---
epic: 3
title: "Sprint Runner Orchestrator"
created: 2026-02-15
started: null
completed: null
---

# Epic 03: Sprint Runner Orchestrator

## Overview

Build the top-level controller that walks through a sprint end-to-end: loading the sprint, dispatching steps to the right agents, tracking progress, and handling failures.

## Why This Matters

The runner is where everything comes together. It's the equivalent of v1's `sprint-next` / `sprint-start` / `sprint-complete` commands, but as a programmatic Python class that can be driven by the SDK or called from CLI.

## Interface Contract

```python
class SprintRunner:
    """Orchestrates sprint execution end-to-end."""

    def __init__(
        self,
        backend: WorkflowBackend,
        agent_registry: AgentRegistry,
        hooks: list[Hook] | None = None,
    ): ...

    async def run(self, sprint_id: str, on_progress: Callable | None = None) -> RunResult: ...
    async def resume(self, sprint_id: str) -> RunResult: ...
    async def cancel(self, sprint_id: str, reason: str) -> None: ...

@dataclass
class RunResult:
    sprint_id: str
    success: bool
    steps_completed: int
    steps_total: int
    agent_results: list[AgentResult]
    deferred_items: list[str]
    duration_seconds: float
```

## The Learning Circle in the Runner

```
SprintRunner.run(sprint_id)
    │
    ├── For each step:
    │     ├── agent.execute(context) → AgentResult
    │     │     └── deferred_items collected
    │     ├── hooks.validate(step, result)
    │     └── backend.advance_step(sprint_id)
    │
    ├── On completion:
    │     ├── Aggregate all deferred_items
    │     ├── Generate postmortem data
    │     └── Return RunResult
    │
    └── Deferred items → input to next sprint planning cycle
```

## Sprints

| Sprint | Title | Status |
|--------|-------|--------|
| 16 | Core Sprint Runner | planned |
| 17 | Dependency Checking and Step Ordering | planned |
| 18 | Pause, Resume, and Retry Logic | planned |

## Success Criteria

- Runner executes a sprint from start to completion using mock agents
- Resume works from any checkpoint (step boundary)
- Cancel stops gracefully and preserves state
- Retry logic handles transient failures
- 32 new tests passing

## Deferred Items

- Progress streaming/webhooks for real-time UI → future enhancement
- Parallel step execution (when steps are independent) → future optimization
- Cost tracking per run (API tokens consumed) → future analytics

## Notes

Created: 2026-02-15
