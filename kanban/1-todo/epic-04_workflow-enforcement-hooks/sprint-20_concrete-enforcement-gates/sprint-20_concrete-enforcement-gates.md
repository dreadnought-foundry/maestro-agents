---
sprint: 20
title: "Concrete Enforcement Gates"
type: backend
epic: 4
status: planning
created: 2026-02-15T00:00:00Z
started: null
completed: null
hours: null
---

# Sprint 20: Concrete Enforcement Gates

## Overview

| Field | Value |
|-------|-------|
| Sprint | 20 |
| Title | Concrete Enforcement Gates |
| Type | backend |
| Epic | 4 |
| Status | Planning |
| Created | 2026-02-15 |

## Goal

Implement the actual quality gates: coverage thresholds, quality review requirements, step ordering, and required steps.

## Interface Contract

Each gate implements the Hook protocol from Sprint 19.

## TDD Plan

1. Write tests for CoverageGate (pass/fail at threshold)
2. Write tests for QualityReviewGate (approve/reject)
3. Write tests for StepOrderingEnforcement
4. Write tests for RequiredStepsGate
5. Write tests for create_default_hooks()
6. Implement all gates

## Tasks

### Phase 1: Planning
- [ ] Review requirements

### Phase 2: Implementation
- [ ] CoverageGate — POST_STEP hook, checks AgentResult.coverage >= threshold
- [ ] QualityReviewGate — PRE_COMPLETION hook, checks review_verdict == "approve"
- [ ] StepOrderingEnforcement — PRE_STEP hook, validates step dependencies
- [ ] RequiredStepsGate — PRE_COMPLETION hook, validates all required steps done
- [ ] create_default_hooks(sprint_type) — returns sensible preset
- [ ] Coverage thresholds: fullstack 75%, backend 85%, frontend 70%, research 0%, infrastructure 60%

### Phase 3: Validation
- [ ] Write 15 tests
- [ ] Quality review

## Deliverables

- src/execution/gates.py
- tests/test_gates.py (15 tests)

## Acceptance Criteria

- [ ] CoverageGate blocks when coverage below threshold
- [ ] QualityReviewGate blocks without approval
- [ ] Sprint type determines which gates and thresholds apply
- [ ] create_default_hooks() is the easy-mode setup
- [ ] 15 new tests passing

## Dependencies

- **Sprints**: Sprint 19 (hook system), Sprint 14 (test runner agent), Sprint 15 (quality engineer agent)
- **External**: None

## Deferred Items

- Custom gate creation API for project-specific rules → future
- Gate bypass with justification (like v1's coverage_threshold override) → future
- Historical gate pass rates → analytics
