---
sprint: 26
title: "End-to-End Sprint Execution"
type: integration
epic: 7
status: planning
created: 2026-02-15T00:00:00Z
started: null
completed: null
hours: null
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
- [ ] Choose a small, self-contained sprint to run as the test case
- [ ] Review runner pipeline for any mock-only assumptions

### Phase 2: Implementation
- [ ] Create a convenience function that wires ClaudeCodeExecutor into the runner
- [ ] Update `src/execution/convenience.py` — `run_sprint()` to accept executor option
- [ ] Update CLI (`src/execution/cli.py`) — add `--real` flag to use ClaudeCodeExecutor
- [ ] Fix any issues where runner assumes mock response shapes
- [ ] Fix any issues where gates assume mock outputs
- [ ] Ensure artifact generation works with real agent output strings

### Phase 3: Validation
- [ ] Run a real sprint execution end-to-end via CLI
- [ ] Verify all gates pass/fail appropriately
- [ ] Verify artifacts are generated and contain real content
- [ ] Verify kanban board reflects the completed sprint
- [ ] Run existing test suite — confirm no regressions

## Deliverables

- Updated `src/execution/convenience.py` — real executor support
- Updated `src/execution/cli.py` — `--real` flag
- Documented first real sprint execution (output log)
- Any fixes to runner/gates/hooks discovered during integration

## Acceptance Criteria

- [ ] `python -m src.execution run <sprint_id> --real` executes a sprint with Claude Code
- [ ] Runner completes all steps without crashing
- [ ] Agent output is captured in `RunResult.agent_results`
- [ ] Artifacts (postmortem, quality, deferred, contracts) are generated
- [ ] Sprint status updates correctly in the workflow backend
- [ ] Existing mock-based tests still pass (no regression)
- [ ] Default behavior (without `--real`) still uses mocks

## Dependencies

- **Sprints**: Sprint 25 (Claude Code Agent Executor)
- **External**: `claude` CLI installed and on PATH
