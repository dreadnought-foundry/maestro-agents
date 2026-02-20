# Postmortem — Sprint 29: KanbanAdapter

**Result**: Success | 451 tests passing | 36 new adapter tests
**Date**: 2026-02-20

## What Was Built
- `KanbanAdapter` class implementing full `WorkflowBackend` protocol (11 methods)
- Filesystem-backed: reads/writes kanban folder structure, YAML frontmatter, and `.claude/sprint-N-state.json`
- Drop-in replacement for InMemoryAdapter — runner doesn't know the difference
- Ported filesystem logic from `sprint_lifecycle.py` as private helper functions
- Handles epic-nested sprints, `--done`/`--blocked` suffixes, column moves

## Lessons Learned
- Transitions don't survive filesystem round-trips (by design) — each lifecycle call returns its own transitions, not accumulated history. Tests should assert behavior, not accumulation.
- `update_sprint()` for resume needs to remove `--blocked` suffix from both file and directory, not just update YAML
- State file (`.claude/sprint-N-state.json`) is the right place for step-level tracking since YAML frontmatter can't represent step arrays cleanly

## Deferred Items
- No deferred items
