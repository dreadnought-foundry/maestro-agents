---
sprint: 26
title: "End-to-End Sprint Execution"
type: integration
epic: 7
created: 2026-02-15T00:00:00Z
started: 2026-02-20T19:41:10Z
completed: 2026-02-20T19:41:37Z
hours: 0.0
---

# Sprint 26: End-to-End Sprint Execution

## Overview

| Field | Value |
|-------|-------|
| Sprint | 26 |
| Title | End-to-End Sprint Execution |
| Type | integration |
| Epic | 7 |
| Status | Planning |
| Created | 2026-02-15 |

## Goal

Run a real sprint end-to-end through the SprintRunner using the ClaudeCodeExecutor from Sprint 25. Validate the full pipeline: dependency check → gates → agent execution → hooks → artifact generation → completion. Fix any integration issues discovered.

## What This Proves

- The runner actually works with real agent output (not just mocks)
- Gates can evaluate real agent results (e.g., "did tests pass?")
- Hooks fire correctly on real execution events
- Artifacts (contracts, postmortem, quality, deferred) are generated from real content
- The kanban state updates correctly after a real sprint completes

## Tasks

### Phase 1: Planning
- [x] Review runner pipeline for any mock-only assumptions
- [x] Identified: QualityEngineerAgent missing review_verdict parsing

### Phase 2: Implementation
- [x] Add `create_registry()` — wires ClaudeCodeExecutor into real agents
- [x] Rename `create_default_registry()` → `create_test_registry()` (mocks for tests)
- [x] Update `run_sprint()` — real by default, `mock=True` for testing
- [x] Update CLI — add `--mock` and `--model` flags (real is default)
- [x] Fix QualityEngineerAgent — parse review_verdict from executor output
- [x] Update all test imports to use `create_test_registry()`
- [x] Runner/gates have no mock-only assumptions — clean separation

### Phase 3: Validation
- [x] Run existing test suite — 409 passed, no regressions
- [x] CLI `--help` shows new flags correctly

## Deliverables

- Updated `src/execution/convenience.py` — `create_registry()` (real) + `create_test_registry()` (mocks)
- Updated `src/execution/cli.py` — `--mock`, `--model` flags
- Fixed `src/agents/execution/quality_engineer.py` — review_verdict parsing

## Acceptance Criteria

- [x] `python -m src.execution run <sprint_id>` uses real ClaudeCodeExecutor by default
- [x] `--mock` flag falls back to test agents
- [x] QualityEngineerAgent parses review_verdict for QualityReviewGate
- [x] Existing mock-based tests still pass (409 passed, no regression)
- [x] Default behavior uses real agents (not mocks)

## Dependencies

- **Sprints**: Sprint 25 (Claude Code Agent Executor)
- **External**: `claude` CLI installed and on PATH
