# Deferred Items

## Sprint 01: Workflow Models and Interface

- [ ] Production SDK integration (Claude Agent SDK for real agent execution)
- [ ] Real Claude API calls (using mocks/InMemory for now)
- [ ] Validation logic on model fields (e.g., non-empty title)

## Sprint 02: In-Memory Adapter

- [ ] MaestroAdapter full implementation (file-based persistence)
- [ ] Concurrent access handling (thread safety)
- [ ] Pagination for list operations

## Sprint 03: Tool Handlers

- [ ] Production SDK integration (handlers tested with InMemoryAdapter only)
- [ ] Update/delete handlers for epics and sprints
- [ ] Batch operations (create multiple sprints at once)

## Sprint 04: Maestro Adapter

- [ ] MaestroAdapter full implementation (lifecycle methods not yet added)
- [ ] YAML frontmatter parsing for sprint/epic metadata
- [ ] File locking for concurrent access

## Sprint 05: MCP Server Factory

- [ ] Production SDK integration (server tested with InMemoryAdapter only)
- [ ] Dynamic tool registration (add/remove tools at runtime)
- [ ] Tool-level authentication/authorization

## Sprint 06: Agent Definitions

- [ ] Production SDK integration (agent definitions not yet wired to real Claude API)
- [ ] Agent prompt tuning based on real execution results
- [ ] Per-project agent configuration overrides

## Sprint 07: Orchestrator and Integration

- [ ] Production deployment configuration
- [ ] Agent response streaming
- [ ] Multi-turn conversation support

## Sprint 08: Comprehensive Testing

- [ ] Performance benchmarking suite
- [ ] Mutation testing integration
- [ ] CI/CD pipeline setup

## Sprint 09: Step Models and Status Tracking

- [ ] Step-level timing utilities (duration calculation) -- deferred to future analytics sprint
- [ ] Step template system (predefined step sequences per sprint type) -- deferred to future enhancement

## Sprint 10: Lifecycle Protocol Methods

- [ ] Unblock/resume operation -- could be explicit method or reuse start_sprint
- [ ] Sprint rollback (undo last step) -- deferred to future enhancement

## Sprint 11: InMemory Lifecycle Implementation

- [ ] MaestroAdapter lifecycle implementation -- deferred to separate sprint
- [ ] Step timing (started_at, completed_at auto-populated) -- deferred for future inclusion

## Sprint 12: Agent Base Infrastructure

- [ ] Agent execution metrics (tokens, duration) on AgentResult -- deferred to analytics sprint
- [ ] Agent configuration/settings per project -- deferred to future enhancement

## Sprint 13: Product Engineer Agent

- [ ] File change diffing (before/after) -- deferred to future enhancement
- [ ] Agent prompt tuning based on success rates -- deferred to learning circle iteration
- [ ] Production Claude SDK integration (real API calls) -- unit tests use mock only

## Sprint 14: Test Runner Agent

- [ ] Test result trending across sprints -- deferred to analytics sprint
- [ ] Flaky test detection -- deferred to future enhancement
- [ ] Coverage delta tracking (before/after sprint) -- deferred, reimplement from v1

## Sprint 15: Quality Engineer Agent

- [ ] Review severity levels (blocker, warning, suggestion) -- deferred to future enhancement
- [ ] Review checklist customization per sprint type -- deferred to future enhancement

## Sprint 16: Core Sprint Runner

- [ ] Parallel step execution -- deferred to future optimization
- [ ] Cost tracking (API tokens per run) -- deferred to analytics sprint
- [ ] Real-time progress streaming -- deferred to UI integration

## Sprint 17: Dependency Checking and Step Ordering

- [ ] Circular dependency detection -- deferred to future validation enhancement
- [ ] Auto-resolution of dependencies (run dependent sprint first) -- deferred to future enhancement

## Sprint 18: Pause, Resume, and Retry Logic

- [ ] Exponential backoff on retries -- deferred to future enhancement
- [ ] Checkpoint to disk for crash recovery -- deferred to future persistence sprint
- [ ] Notification on pause/failure -- deferred to integration sprint

## Sprint 19: Hook System Architecture

- [ ] Hook ordering/priority -- deferred to future enhancement
- [ ] Async hook execution (run non-blocking hooks in parallel) -- deferred to optimization sprint
- [ ] Hook metrics dashboard -- deferred to analytics sprint

## Sprint 20: Concrete Enforcement Gates

- [ ] Custom gate creation API for project-specific rules -- deferred to future enhancement
- [ ] Gate bypass with justification (like v1's coverage_threshold override) -- deferred to future enhancement
- [ ] Historical gate pass rates -- deferred to analytics sprint

## Sprint 21: End-to-End Integration and CLI

- [ ] Interactive mode (pause at gates for user input) -- deferred to future enhancement
- [ ] Web UI for sprint monitoring -- deferred to future UI sprint
- [ ] Plugin system for custom agents -- deferred to future expansion

## Sprint 22b: Kanban TUI

- [ ] Filtering by epic or status
- [ ] Search functionality
- [ ] Sprint creation from within the TUI
- [ ] Watch mode for external changes

## Sprint 22: Runner Integration

No deferred items.

## Sprint 23: Validation E2E

No deferred items.

## Sprint 24: CLI Fix & Kanban Doc Cleanup

No deferred items.
