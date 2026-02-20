# Postmortem — Sprint 28: Backlog Grooming Agent

**Result**: Success | All tasks complete | 402 tests passing
**Date**: 2026-02-20

## What Was Built
- `src/execution/grooming.py` — GroomingAgent with two modes: full grooming (propose next epic) and mid-epic (propose additional sprints)
- `src/execution/grooming_hook.py` — GroomingHook that fires at POST_COMPLETION hook point
- Added POST_COMPLETION to HookPoint enum (non-blocking, fires after sprint completes)
- Wired grooming into default hook registry via `create_default_hooks(kanban_dir=...)`
- Updated convenience functions and CLI for kanban_dir passthrough
- 21 tests covering all grooming functionality

## Key Decisions
- Two separate prompts: GROOMING_PROMPT (full, for when epic is complete) and MID_EPIC_PROMPT (for additional sprints within current epic)
- GroomingHook is non-blocking (blocking=False) — proposals are informational, not gatekeeping
- Grooming is only wired in when kanban_dir is provided (optional)
- Uses `claude --print` subprocess pattern consistent with other CLI-based agents

## Lessons Learned
- The POST_COMPLETION hook point needed to be non-blocking to avoid interfering with the sprint success/failure flow
- `is_epic_complete()` can scan the kanban board to determine if all sprints in an epic are done, enabling automatic mode switching
- Parsing epic numbers from IDs like "e-3" or "epic-03" needs flexible regex

## Deferred Items
- Human approval workflow for grooming proposals (currently just outputs the proposal)
- Integration with backlog creation (auto-creating sprints from approved proposals)
