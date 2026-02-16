---
epic: 4
title: "Workflow Enforcement Hooks"
status: planning
created: 2026-02-15
started: null
completed: null
---

# Epic 04: Workflow Enforcement Hooks

## Overview

Add quality gates and validation hooks that plug into the sprint runner as middleware, enforcing coverage thresholds, step ordering, and quality review requirements.

## Why This Matters

This is what made v1's workflow reliable — you couldn't skip steps, couldn't commit without coverage, couldn't complete without review. v2 implements the same enforcement but as composable, testable Python hooks instead of file-based scripts.

## Interface Contract

```python
class HookPoint(Enum):
    PRE_SPRINT = "pre_sprint"
    PRE_STEP = "pre_step"
    POST_STEP = "post_step"
    PRE_COMPLETION = "pre_completion"

class Hook(Protocol):
    """Contract for workflow enforcement hooks."""
    hook_point: HookPoint
    async def evaluate(self, context: HookContext) -> HookResult

@dataclass
class HookResult:
    passed: bool
    message: str
    blocking: bool = True
    deferred_items: list[str] = field(default_factory=list)

@dataclass
class HookContext:
    sprint: Sprint
    step: Step | None
    agent_result: AgentResult | None
    run_state: dict
```

## Quality Gates (from v1, reimagined)

| Gate | Hook Point | Rule |
|------|-----------|------|
| CoverageGate | POST_STEP (test runner) | Coverage >= threshold for sprint type |
| QualityReviewGate | PRE_COMPLETION | Quality engineer must approve |
| StepOrderingEnforcement | PRE_STEP | Steps must execute in dependency order |
| RequiredStepsGate | PRE_COMPLETION | All required steps completed |

### Coverage Thresholds by Sprint Type (from v1)

```python
COVERAGE_THRESHOLDS = {
    "fullstack": 75,
    "backend": 85,
    "frontend": 70,
    "research": 0,
    "design": 0,
    "infrastructure": 60,
}
```

## The Learning Circle in Hooks

Hooks can produce deferred items too. For example:
- CoverageGate passes but notices coverage dropped from last sprint → deferred: "investigate coverage regression in auth module"
- QualityReviewGate approves but flags a pattern → deferred: "consider extracting common error handling pattern"

These feed back into sprint planning, creating continuous improvement.

## Sprints

| Sprint | Title | Status |
|--------|-------|--------|
| 19 | Hook System Architecture | planned |
| 20 | Concrete Enforcement Gates | planned |
| 21 | End-to-End Integration and CLI | planned |

## Success Criteria

- Hook system is composable — add/remove hooks without changing runner
- Coverage gate blocks completion when coverage is below threshold
- Quality review gate requires explicit approval
- Step ordering prevents skipping required steps
- `create_default_hooks(sprint_type)` returns sensible preset
- 27 new tests passing

## Deferred Items

- Custom hook creation API for project-specific rules → future
- Hook metrics (how often each gate blocks, common failure reasons) → analytics
- Dynamic threshold adjustment based on historical data → learning circle optimization

## Notes

Created: 2026-02-15
