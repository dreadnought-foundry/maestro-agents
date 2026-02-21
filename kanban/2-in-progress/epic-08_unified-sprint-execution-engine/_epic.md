---
epic: 8
title: "Unified Sprint Execution Engine"
created: 2026-02-20
started: null
completed: null
---

# Epic 08: Unified Sprint Execution Engine

## Overview

Consolidate the two disconnected systems (SprintRunner + sprint_lifecycle.py) into a single unified engine. Replace the in-memory-only backend with a KanbanAdapter that reads/writes the filesystem directly. Introduce a phase-based execution model (Plan → TDD → Build → Validate → Review → Complete) with a new Review column for human sign-off. Add a PlanningAgent that generates rich execution context (contracts, team plan, TDD strategy, coding strategy) before agents start building.

## Problem

Today there are two separate systems that don't talk to each other:
- **SprintRunner** — orchestrates agent execution via InMemoryAdapter (no persistence, no kanban awareness)
- **sprint_lifecycle.py** — manages kanban filesystem operations (folder moves, suffixes, YAML) but has no agent execution

This means: the runner can't move sprints on the board, the lifecycle script can't trigger agents, artifact files must be created manually, and there's no planning phase or human review checkpoint.

## Vision

One system. The user runs `/sprint-start 29`, the engine:
1. **Plans** — PlanningAgent reads the sprint spec + codebase and produces contracts, team plan, TDD strategy, coding strategy
2. **TDD** — Writes failing tests that define expected behavior
3. **Builds** — Agents implement code to pass the tests (potentially parallel)
4. **Validates** — Runs full test suite, spins up services/UIs, verifies against acceptance criteria
5. **Moves to Review** — Sprint appears in the Review column on the kanban board
6. The user reviews, then runs `/sprint-complete 29`
7. **Completes** — Generates postmortem, quality report, deferred items; moves to Done

If the user rejects: `/sprint-reject 29 "reason"` → moves back to In Progress with feedback.

## Sprints

| Sprint | Title | Type | Dependencies |
|--------|-------|------|-------------|
| 29 | KanbanAdapter | backend | — |
| 30 | Review Column & Rejection Flow | infrastructure | 29 |
| 31 | Phase-Based Runner | backend | 29 |
| 32 | PlanningAgent & Planning Artifacts | backend | 31 |
| 33 | Parallel Execution & Step Dependencies | backend | 31 |
| 34 | Validation Phase | backend | 31, 33 |
| 35 | End-to-End Integration | integration | 29–36 |
| 36 | Kanban TUI Split Rendering | frontend | 30 |

## Success Criteria

- [ ] Single system handles both agent execution and kanban state
- [ ] `sprint_lifecycle.py` is deleted — its logic lives in KanbanAdapter
- [ ] Sprint execution follows 6 phases: Plan → TDD → Build → Validate → Review → Complete
- [ ] PlanningAgent generates contracts, team plan, TDD strategy, coding strategy before execution
- [ ] Review column visible on kanban board; user sees sprints waiting for sign-off
- [ ] Sprints render in the correct column by status, not by epic folder location
- [ ] Complete/reject actions available directly from the kanban TUI board
- [ ] `/sprint-reject` moves sprint back to In Progress with feedback
- [ ] Agents can run in parallel within a phase when the team plan allows it
- [ ] Validation phase can spin up services/UIs and verify what was built
- [ ] All existing tests continue to pass (InMemoryAdapter preserved for fast testing)
