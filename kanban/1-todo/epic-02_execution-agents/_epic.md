---
epic: 2
title: "Execution Agents"
status: planning
created: 2026-02-15
started: null
completed: null
---

# Epic 02: Execution Agents

## Overview

Build three Claude Agent SDK-powered agents that do the actual work of a sprint: writing code, running tests, and reviewing quality.

## Why This Matters

Planning agents tell you *what* to do. Execution agents *do* it. This is the core automation — an agent that can take a sprint step like "implement the auth module" and produce working, tested code.

## Interface Contract

```python
class ExecutionAgent(Protocol):
    """Contract all execution agents must satisfy."""
    async def execute(self, context: StepContext) -> AgentResult

@dataclass
class StepContext:
    step: Step
    sprint: Sprint
    epic: Epic
    project_root: Path
    previous_outputs: list[AgentResult]

@dataclass
class AgentResult:
    success: bool
    output: str
    files_modified: list[str]
    files_created: list[str]
    test_results: dict | None = None
    coverage: float | None = None
    review_verdict: str | None = None
    deferred_items: list[str] = field(default_factory=list)
```

## TDD Approach

Each agent sprint follows:
1. Define mock agent that returns canned results
2. Write tests against mock
3. Implement real agent using Claude SDK
4. Verify tests pass with both mock and real (where practical)

## Parallelism

s-13, s-14, s-15 are fully independent — different agents, same ExecutionAgent interface. Can be built simultaneously.

## Sprints

| Sprint | Title | Status |
|--------|-------|--------|
| 12 | Agent Base Infrastructure | planned |
| 13 | Product Engineer Agent | planned |
| 14 | Test Runner Agent | planned |
| 15 | Quality Engineer Agent | planned |

## Success Criteria

- All three agents implement ExecutionAgent protocol
- Mock versions exist for testing without API calls
- AgentResult captures files modified, test results, coverage, and deferred items
- 36 new tests passing

## Deferred Items

- Agent performance metrics (tokens used, time per step) → future analytics
- Agent prompt tuning based on postmortem feedback → learning circle
- Domain-specific agent variants (marketing-writer, data-analyst) → future expansion

## Notes

Created: 2026-02-15
