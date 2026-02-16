# Deferred Items

## Production Integration

- [ ] Production SDK integration (Claude Agent SDK for real agent execution)
  ↳ 🔴 High · L · Complexity 3 · (S01, S03, S05, S06, S13)
- [ ] Real Claude API calls (move from mocks/InMemory to production)
  ↳ 🔴 High · M · Complexity 2 · (S01, S13)
- [ ] Production deployment configuration
  ↳ 🔴 High · M · Complexity 2 · (S07)

## File System & Persistence

- [ ] MaestroAdapter full implementation (file-based persistence and lifecycle methods)
  ↳ 🔴 High · L · Complexity 3 · (S02, S04, S11)
- [ ] YAML frontmatter parsing for sprint/epic metadata
  ↳ 🟡 Medium · M · Complexity 2 · (S04)
- [ ] File locking for concurrent access
  ↳ 🟡 Medium · M · Complexity 2 · (S04)
- [ ] Checkpoint to disk for crash recovery
  ↳ 🟡 Medium · M · Complexity 2 · (S18)

## Analytics & Metrics

- [ ] Agent execution metrics (tokens, duration) on AgentResult
  ↳ 🟡 Medium · M · Complexity 2 · (S12, S16)
- [ ] Step-level timing utilities (duration calculation)
  ↳ 🟡 Medium · S · Complexity 1 · (S09, S11)
- [ ] Test result trending across sprints
  ↳ 🟡 Medium · M · Complexity 2 · (S14)
- [ ] Coverage delta tracking (before/after sprint)
  ↳ 🟡 Medium · M · Complexity 2 · (S14)
- [ ] Hook metrics dashboard
  ↳ 🟢 Low · M · Complexity 2 · (S19, S20)
- [ ] Historical gate pass rates
  ↳ 🟢 Low · S · Complexity 1 · (S20)

## Testing & Quality

- [ ] Performance benchmarking suite
  ↳ 🟡 Medium · M · Complexity 2 · (S08)
- [ ] Mutation testing integration
  ↳ 🟡 Medium · M · Complexity 2 · (S08)
- [ ] CI/CD pipeline setup
  ↳ 🟡 Medium · M · Complexity 2 · (S08)
- [ ] Flaky test detection
  ↳ 🟢 Low · M · Complexity 2 · (S14)

## UI & User Experience

- [ ] Web UI for sprint monitoring
  ↳ 🟡 Medium · L · Complexity 3 · (S21)
- [ ] Real-time progress streaming
  ↳ 🟡 Medium · M · Complexity 2 · (S07, S16)
- [ ] Interactive mode (pause at gates for user input)
  ↳ 🟡 Medium · M · Complexity 2 · (S21)
- [ ] Filtering by epic or status (Kanban TUI)
  ↳ 🟢 Low · S · Complexity 1 · (S22b)
- [ ] Search functionality (Kanban TUI)
  ↳ 🟢 Low · S · Complexity 1 · (S22b)
- [ ] Sprint creation from within the TUI
  ↳ 🟢 Low · M · Complexity 2 · (S22b)
- [ ] Watch mode for external changes (Kanban TUI)
  ↳ 🟢 Low · S · Complexity 1 · (S22b)

## Advanced Features

- [ ] Multi-turn conversation support
  ↳ 🟡 Medium · M · Complexity 2 · (S07)
- [ ] Agent response streaming
  ↳ 🟡 Medium · M · Complexity 2 · (S07)
- [ ] Agent prompt tuning based on real execution results
  ↳ 🟡 Medium · L · Complexity 3 · (S06, S13)
- [ ] Plugin system for custom agents
  ↳ 🟡 Medium · L · Complexity 3 · (S21)
- [ ] Dynamic tool registration (add/remove tools at runtime)
  ↳ 🟡 Medium · M · Complexity 2 · (S05)
- [ ] Parallel step execution
  ↳ 🟡 Medium · M · Complexity 3 · (S16)
- [ ] Auto-resolution of dependencies (run dependent sprint first)
  ↳ 🟢 Low · M · Complexity 2 · (S17)
- [ ] Async hook execution (run non-blocking hooks in parallel)
  ↳ 🟢 Low · M · Complexity 2 · (S19)
- [ ] File change diffing (before/after)
  ↳ 🟢 Low · S · Complexity 1 · (S13)

## Configuration & Customization

- [ ] Per-project agent configuration overrides
  ↳ 🟡 Medium · S · Complexity 1 · (S06, S12)
- [ ] Step template system (predefined step sequences per sprint type)
  ↳ 🟡 Medium · M · Complexity 2 · (S09)
- [ ] Review checklist customization per sprint type
  ↳ 🟢 Low · S · Complexity 1 · (S15)
- [ ] Review severity levels (blocker, warning, suggestion)
  ↳ 🟢 Low · S · Complexity 1 · (S15)
- [ ] Hook ordering/priority
  ↳ 🟢 Low · S · Complexity 1 · (S19)
- [ ] Custom gate creation API for project-specific rules
  ↳ 🟢 Low · M · Complexity 2 · (S20)
- [ ] Gate bypass with justification
  ↳ 🟢 Low · S · Complexity 1 · (S20)

## Operations & Resilience

- [ ] Exponential backoff on retries
  ↳ 🟡 Medium · S · Complexity 1 · (S18)
- [ ] Notification on pause/failure
  ↳ 🟡 Medium · S · Complexity 2 · (S18)
- [ ] Concurrent access handling (thread safety)
  ↳ 🟢 Low · M · Complexity 2 · (S02)
- [ ] Circular dependency detection
  ↳ 🟢 Low · S · Complexity 1 · (S17)

## CRUD & Data Operations

- [ ] Update/delete handlers for epics and sprints
  ↳ 🟡 Medium · M · Complexity 2 · (S03)
- [ ] Batch operations (create multiple sprints at once)
  ↳ 🟢 Low · S · Complexity 1 · (S03)
- [ ] Pagination for list operations
  ↳ 🟢 Low · S · Complexity 1 · (S02)
- [ ] Sprint rollback (undo last step)
  ↳ 🟢 Low · M · Complexity 2 · (S10)
- [ ] Unblock/resume operation (explicit method vs reuse start_sprint)
  ↳ 🟢 Low · S · Complexity 1 · (S10)

## Validation & Security

- [ ] Validation logic on model fields (e.g., non-empty title)
  ↳ 🟡 Medium · S · Complexity 1 · (S01)
- [ ] Tool-level authentication/authorization
  ↳ 🟢 Low · M · Complexity 2 · (S05)