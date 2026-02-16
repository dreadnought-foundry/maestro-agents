---
sprint: 14
title: "Test Runner Agent"
type: backend
epic: 2
status: done
created: 2026-02-15T00:00:00Z
started: null
completed: null
hours: null
---

# Sprint 14: Test Runner Agent

## Overview

| Field | Value |
|-------|-------|
| Sprint | 14 |
| Title | Test Runner Agent |
| Type | backend |
| Epic | 2 |
| Status | Planning |
| Created | 2026-02-15 |

## Goal

Build the agent that executes pytest, parses results, and computes coverage metrics.

## Interface Contract

Implements `ExecutionAgent` protocol. Runs the test suite and returns structured results including pass/fail counts and coverage percentage.

## AgentResult.test_results format

```python
{
    "total": 48,
    "passed": 46,
    "failed": 2,
    "errors": 0,
    "coverage_pct": 87.5,
    "failed_tests": ["test_foo", "test_bar"],
}
```

## TDD Plan

1. Write MockTestRunnerAgent that returns canned test results
2. Write tests verifying result structure
3. Implement real agent that runs pytest via subprocess
4. Write tests for result parsing

## Tasks

### Phase 1: Planning
- [ ] Review requirements

### Phase 2: Implementation
- [ ] Create MockTestRunnerAgent in mocks.py
- [ ] Create TestRunnerAgent in src/agents/execution/test_runner.py
- [ ] Run pytest via Bash tool or subprocess with --json-report and --cov flags
- [ ] Parse pytest output into structured test_results dict
- [ ] Extract coverage percentage into AgentResult.coverage

### Phase 3: Validation
- [ ] Write 10 tests
- [ ] Quality review

## Deliverables

- src/agents/execution/test_runner.py
- Updated mocks.py (MockTestRunnerAgent)
- tests/test_test_runner.py (10 tests)

## Acceptance Criteria

- [ ] Runs pytest and captures results
- [ ] Coverage percentage extracted
- [ ] Failed test names listed
- [ ] Works with mock for runner testing
- [ ] 10 new tests passing

## Dependencies

- **Sprints**: Sprint 12 (agent infrastructure)
- **External**: None

## Deferred Items

- Test result trending across sprints → analytics
- Flaky test detection → future enhancement
- Coverage delta tracking (before/after sprint) → v1 had this, reimplement
