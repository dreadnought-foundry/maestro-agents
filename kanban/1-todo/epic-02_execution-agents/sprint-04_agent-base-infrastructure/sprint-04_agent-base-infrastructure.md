---
sprint: 4
title: "Agent Base Infrastructure"
type: backend
epic: 2
status: planning
created: 2026-02-15T00:00:00Z
started: null
completed: null
hours: null
---

# Sprint 04: Agent Base Infrastructure

## Overview

| Field | Value |
|-------|-------|
| Sprint | 4 |
| Title | Agent Base Infrastructure |
| Type | backend |
| Epic | 2 |
| Status | Planning |
| Created | 2026-02-15 |

## Goal

Define the execution agent interface and supporting infrastructure: protocol, result types, registry, and context builder.

## Interface Contract (define first)

```python
class ExecutionAgent(Protocol):
    name: str
    description: str
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

class AgentRegistry:
    def register(self, step_type: str, agent: ExecutionAgent) -> None
    def get_agent(self, step_type: str) -> ExecutionAgent
    def list_agents(self) -> dict[str, ExecutionAgent]
```

## TDD Plan

1. Write tests for AgentResult construction and defaults
2. Write tests for StepContext construction
3. Write tests for AgentRegistry (register, get, list, missing key)
4. Implement all types

## Tasks

### Phase 1: Planning
- [ ] Review requirements

### Phase 2: Implementation
- [ ] Define AgentResult dataclass in src/agents/execution/types.py
- [ ] Define StepContext dataclass in src/agents/execution/types.py
- [ ] Define ExecutionAgent protocol in src/agents/execution/protocol.py
- [ ] Define AgentRegistry in src/agents/execution/registry.py

### Phase 3: Validation
- [ ] Write 10 tests
- [ ] Quality review

## Deliverables

- New src/agents/execution/ package
- tests/test_agent_infrastructure.py (10 tests)

## Acceptance Criteria

- [ ] AgentResult.deferred_items enables learning circle
- [ ] AgentRegistry raises KeyError for unregistered step types
- [ ] StepContext provides all info an agent needs without reaching into global state
- [ ] 10 new tests passing

## Dependencies

- **Sprints**: Sprint 1 (Step model for StepContext)
- **External**: None

## Deferred Items

- Agent execution metrics (tokens, duration) on AgentResult → analytics
- Agent configuration/settings per project → future
