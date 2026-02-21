---
sprint: 15
title: "Quality Engineer Agent"
type: backend
epic: 2
created: 2026-02-15T00:00:00Z
started: null
completed: null
hours: null
---

# Sprint 15: Quality Engineer Agent

## Overview

| Field | Value |
|-------|-------|
| Sprint | 15 |
| Title | Quality Engineer Agent |
| Type | backend |
| Epic | 2 |
| Status | Planning |
| Created | 2026-02-15 |

## Goal

Build the agent that reviews code changes and validates work against sprint acceptance criteria.

## Interface Contract

Implements `ExecutionAgent` protocol. Reviews the work done in previous steps and produces a verdict: approve or request_changes.

## TDD Plan

1. Write MockQualityEngineerAgent with configurable verdict
2. Write tests for approve and request_changes paths
3. Implement real agent using Claude SDK
4. Test that deferred items are surfaced

## Tasks

### Phase 1: Planning
- [ ] Review requirements

### Phase 2: Implementation
- [ ] Create MockQualityEngineerAgent in mocks.py
- [ ] Create QualityEngineerAgent in src/agents/execution/quality_engineer.py
- [ ] Agent uses Claude SDK with tools: Read, Grep, Glob (read-only)
- [ ] Agent receives previous_outputs from StepContext to review what was done
- [ ] Returns review_verdict: "approve" or "request_changes"
- [ ] Surfaces deferred_items for learning circle

### Phase 3: Validation
- [ ] Write 8 tests
- [ ] Quality review

## Deliverables

- src/agents/execution/quality_engineer.py
- Updated mocks.py (MockQualityEngineerAgent)
- tests/test_quality_engineer.py (8 tests)

## Acceptance Criteria

- [ ] Returns "approve" or "request_changes" verdict
- [ ] Read-only tool scoping (can't accidentally modify code during review)
- [ ] Deferred items captured for learning circle
- [ ] 8 new tests passing

## Dependencies

- **Sprints**: Sprint 12 (agent infrastructure)
- **External**: None

## Deferred Items

- Review severity levels (blocker, warning, suggestion) → future
- Review checklist customization per sprint type → future
