---
sprint: 21
title: "End-to-End Integration and CLI"
type: backend
epic: 4
status: done
created: 2026-02-15T00:00:00Z
started: null
completed: null
hours: null
---

# Sprint 21: End-to-End Integration and CLI

## Overview

| Field | Value |
|-------|-------|
| Sprint | 21 |
| Title | End-to-End Integration and CLI |
| Type | backend |
| Epic | 4 |
| Status | Planning |
| Created | 2026-02-15 |

## Goal

Wire everything together: convenience functions, CLI entry point, full integration tests, and documentation.

## Tasks

### Phase 1: Planning
- [ ] Review requirements

### Phase 2: Implementation
- [ ] Create run_sprint() convenience function
- [ ] Create CLI entry point: `python -m src.execution "run" <sprint_id>`
- [ ] Register all agents in default registry
- [ ] Update Makefile with `run-sprint` target

### Phase 3: Validation
- [ ] Write full integration test: create epic → create sprint → run sprint → verify completion
- [ ] Write integration test with hooks: coverage gate blocks undercovered sprint
- [ ] Write integration test: resume after failure
- [ ] Update docs/phase-2/overview.md with final architecture

## Deliverables

- src/execution/__init__.py (convenience functions)
- src/execution/cli.py (CLI entry point)
- tests/test_e2e_integration.py (integration tests)
- Updated Makefile
- Updated docs

## Acceptance Criteria

- [ ] `python -m src.execution run <sprint_id>` works end-to-end
- [ ] Integration tests pass with mock agents
- [ ] Full learning circle visible: deferred items collected, aggregated, available
- [ ] All Phase 2 tests passing (150+)
- [ ] All Phase 1 tests still passing (93)

## Dependencies

- **Sprints**: Sprint 17 (dependency checking), Sprint 18 (pause/resume), Sprint 20 (enforcement gates)
- **External**: None

## Deferred Items

- Interactive mode (pause at gates for user input) → future
- Web UI for sprint monitoring → future
- Plugin system for custom agents → future expansion
