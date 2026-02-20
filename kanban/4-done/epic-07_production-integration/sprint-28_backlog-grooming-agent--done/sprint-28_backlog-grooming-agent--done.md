---
sprint: 28
title: "Backlog Grooming Agent"
type: backend
epic: 7
status: done
created: 2026-02-20T19:35:05Z
started: 2026-02-20T19:35:09Z
completed: 2026-02-20T19:35:35Z
hours: 0.0
---

# Sprint 28: Backlog Grooming Agent

## Overview

| Field | Value |
|-------|-------|
| Sprint | 28 |
| Title | Backlog Grooming Agent |
| Type | backend |
| Epic | 7 |
| Status | Done |
| Created | 2026-02-20 |

## Goal

Build the backlog grooming agent that closes the feedback loop: agents execute sprints, defer items, the synthesizer condenses them, and the grooming agent proposes the next work (new epic or additional sprints). Wire it into the hook system as a POST_COMPLETION hook.

## Tasks

### Phase 1: Planning
- [x] Design grooming agent interface (propose method)
- [x] Design two grooming modes: full (new epic) and mid-epic (additional sprints)

### Phase 2: Implementation
- [x] Create `src/execution/grooming.py` — GroomingAgent, GroomingProposal, MockGroomingAgent
- [x] Create `src/execution/grooming_hook.py` — GroomingHook (POST_COMPLETION)
- [x] Add POST_COMPLETION to HookPoint enum
- [x] Wire GroomingHook into default hook registry via `create_default_hooks()`
- [x] Update `run_sprint()` convenience function to accept kanban_dir and grooming_agent
- [x] Add `--kanban-dir` to CLI run subcommand
- [x] Write 21 tests covering MockGroomingAgent, prompt building, is_epic_complete, hook, runner integration

### Phase 3: Validation
- [x] All 402 tests passing
- [x] Hook fires POST_COMPLETION after sprint completes
- [x] Grooming agent proposes next epic when all sprints in current epic are done

## Deliverables

- `src/execution/grooming.py` — GroomingAgent, GroomingProposal, MockGroomingAgent
- `src/execution/grooming_hook.py` — GroomingHook
- `tests/test_grooming.py` — 21 tests
- Updated `src/execution/gates.py` — wired grooming into default hooks
- Updated `src/execution/convenience.py` — kanban_dir passthrough
- Updated `src/execution/cli.py` — --kanban-dir flag

## Acceptance Criteria

- [x] GroomingAgent.propose() generates proposals via claude --print
- [x] GroomingHook fires after sprint completion (POST_COMPLETION)
- [x] Two modes: full grooming (new epic) and mid-epic (more sprints)
- [x] is_epic_complete() checks kanban board state
- [x] Wired into default hook registry when kanban_dir is provided
- [x] All 402 tests passing

## Dependencies

- **Sprints**: Sprint 25 (executor), Sprint 19 (hook system)
- **External**: `claude` CLI for real grooming proposals
