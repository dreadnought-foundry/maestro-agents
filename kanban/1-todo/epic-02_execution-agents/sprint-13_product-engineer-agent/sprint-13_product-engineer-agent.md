---
sprint: 13
title: "Product Engineer Agent"
type: backend
epic: 2
status: planning
created: 2026-02-15T00:00:00Z
started: null
completed: null
hours: null
---

# Sprint 13: Product Engineer Agent

## Overview

| Field | Value |
|-------|-------|
| Sprint | 13 |
| Title | Product Engineer Agent |
| Type | backend |
| Epic | 2 |
| Status | Planning |
| Created | 2026-02-15 |

## Goal

Build the agent that writes and modifies code during sprint execution, using the Claude Agent SDK.

## Interface Contract

Implements `ExecutionAgent` protocol. Given a StepContext describing what code to write, produces files and returns an AgentResult with files_modified/created.

## TDD Plan

1. Write MockProductEngineerAgent that returns canned results
2. Write tests using mock (verifies protocol compliance)
3. Implement real agent using Claude SDK AgentDefinition
4. Write integration test that runs real agent on a trivial task

## Tasks

### Phase 1: Planning
- [ ] Review requirements

### Phase 2: Implementation
- [ ] Create MockProductEngineerAgent in src/agents/execution/mocks.py
- [ ] Create ProductEngineerAgent in src/agents/execution/product_engineer.py
- [ ] Agent uses Claude SDK with tools: Read, Write, Edit, Glob, Grep, Bash
- [ ] Agent prompt focuses on TDD: write tests first, then implementation
- [ ] Track files modified/created in AgentResult

### Phase 3: Validation
- [ ] Write 8 tests (mock-based, no API calls needed for unit tests)
- [ ] Quality review

## Deliverables

- src/agents/execution/product_engineer.py
- src/agents/execution/mocks.py (MockProductEngineerAgent)
- tests/test_product_engineer.py (8 tests)

## Acceptance Criteria

- [ ] Implements ExecutionAgent protocol
- [ ] Mock version works for runner testing
- [ ] Real version uses Claude SDK with appropriate tool scoping
- [ ] AgentResult includes files_modified and files_created
- [ ] 8 new tests passing

## Dependencies

- **Sprints**: Sprint 12 (agent infrastructure)
- **External**: None

## Deferred Items

- File change diffing (before/after) → future enhancement
- Agent prompt tuning based on success rates → learning circle
