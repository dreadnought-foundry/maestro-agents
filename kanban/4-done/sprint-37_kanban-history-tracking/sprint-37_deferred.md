# Deferred Items — Sprint 37: Kanban History Tracking

- [ ] Standalone sprint support in execution engine — `runner.py` line 158 calls `get_epic(sprint.epic_id)` unconditionally, fails for sprints with `epic: null`. Needs a guard or optional epic handling.
- [ ] Cycle time / lead time calculations — use the `history` array to compute time between column transitions for sprint metrics and reporting
- [ ] History-based retrospective reports — aggregate history data across all sprints for project-level insights
- [ ] Backfill history for completed sprints — existing done/archived sprints have no history entries; could reconstruct from git log or timestamps
