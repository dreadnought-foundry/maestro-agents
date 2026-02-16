# Sprint Postmortems

## Timeline
- **S01** [Workflow Models and Interface] — Success 5/5 steps (1m)
- **S02** [In-Memory Adapter] — Success 5/5 steps (1m)
- **S03** [Tool Handlers] — Success 8/8 steps (2m)
- **S04** [Maestro Adapter] — Success 7/7 steps (2m)
- **S05** [MCP Server Factory] — Success 6/6 steps (1m)
- **S06** [Agent Definitions] — Success 5/5 steps (1m)
- **S07** [Orchestrator and Integration] — Success 4/4 steps (2m)
- **S08** [Comprehensive Testing] — Success 6/6 steps (3m)
- **S09** [Step Models and Status Tracking] — Success 3/3 steps (15m)
- **S10** [Lifecycle Protocol Methods] — Success 3/3 steps (20m)
- **S11** [InMemory Lifecycle Implementation] — Success 3/3 steps (25m)
- **S12** [Agent Base Infrastructure] — Success 3/3 steps (15m)
- **S13** [Product Engineer Agent] — Success 3/3 steps (20m)
- **S14** [Test Runner Agent] — Success 3/3 steps (20m)
- **S15** [Quality Engineer Agent] — Success 3/3 steps (20m)
- **S16** [Core Sprint Runner] — Success 3/3 steps (25m)
- **S17** [Dependency Checking and Step Ordering] — Success 3/3 steps (20m)
- **S18** [Pause, Resume, and Retry Logic] — Success 3/3 steps (20m)
- **S19** [Hook System Architecture] — Success 3/3 steps (25m)
- **S20** [Concrete Enforcement Gates] — Success 3/3 steps (25m)
- **S21** [End-to-End Integration and CLI] — Success 3/3 steps (30m)
- **S22b** [Kanban TUI] — Success 10/10 tasks (tooling)
- **S22** [Runner Integration] — Success 8/8 tasks (12 tests)
- **S23** [Validation E2E] — Success 10/10 tasks (10 tests)
- **S24** [CLI Fix & Kanban Doc Cleanup] — Success 5/5 tasks (5 tests)

## Architecture & Design Patterns

**Protocol-First Design** (S01, S10, S12, S15): Define protocol/interface before implementation. This kept downstream sprints focused and ensured all backends implement the same contract. Protocol-level definitions with descriptive error messages save debugging time.

**Test-Friendly Architecture** (S02, S03, S11, S13, S14, S21): Build in-memory or mock implementations first to enable fast, deterministic testing without I/O or API costs. Mock agents with configurable results validate gates and thresholds without incurring API charges. In-memory adapters unlock testing for all layers above.

**Factory and Registry Patterns** (S05, S12): Factory functions (create_workflow_server) and registries (AgentRegistry, HookRegistry) decouple configuration from implementation. Closures for parameter binding keep registration clean.

**Separation of Concerns** (S03, S16, S19, S22): Handler/tool separation (pure async handlers testable without SDK), orchestrator pattern (delegating to specialist agents), and composable hook system mean features can be added or removed without changing core runner code. Wiring multiple cross-cutting concerns requires careful operation ordering (S22).

**Context Over Global State** (S12): StepContext design is critical—agents should never reach into global state. Providing step, sprint, epic, project_root, and previous_outputs as a single context object keeps agents predictable.

**Structured Results and Data Flow** (S14, S16, S19, S20): AgentResult with success, output, files, test_results, coverage, verdict, and deferred_items enables downstream gates to make decisions. Structured test results (JSON parsing preferred over raw output) and HookResult with blocking flags allow warnings without halting execution. Deferred items aggregation creates the learning circle.

## Testing Strategy

**Test Pyramid** (S08, S23): Unit tests on models and individual functions, integration tests with tmp_path or mock adapters, and end-to-end tests exercising the full stack (runner + hooks + gates + agents). Dedicated testing sprints catch edge cases missed in implementation sprints.

**Edge Case and Error Path Testing** (S08, S10): Test empty strings, unicode, long inputs, malformed JSON, missing fields, invalid transitions. Define valid transitions as data (not hardcoded logic) to make state machines testable and extensible.

**Smoke Tests and Validation** (S08, S24): Smoke tests catch integration issues. Verify all __init__.py exports are importable, agent tool references are valid, and MCP server schemas match definitions. Gate blocking behavior requires careful mock setup to simulate pass and fail verdicts (S23).

**Backward Compatibility** (S09): Careful field defaults prevent breaking existing tests when models evolve.

## Integration Lessons

**Convenience Functions and CLI Entry Points** (S07, S21): High-level wiring functions (run_orchestrator, run_sprint) reduce boilerplate. CLI entry points enable manual testing early and make the system usable outside tests immediately.

**Filesystem Conventions** (S22b, S24): Supporting multiple layout patterns (epic-grouped folders, standalone flat files, flat files inside epic) requires careful pattern matching. Test with real kanban contents. Standalone entities need explicit handling to avoid being swallowed by grouping logic.

**Dependency Management** (S17, S22, S24): Validate dependencies before starting sprints. Resume logic must reuse the same validation paths as initial runs to avoid state inconsistencies. Optional SDK dependencies must be guarded with try/except to prevent import crashes (S24).

**Hook Evaluation** (S19, S20, S22): Hook system must evaluate at PRE_SPRINT, PRE_STEP, POST_STEP, PRE_COMPLETION. Storing agent_results in run_state enables hooks to inspect prior step outcomes. Sprint-type-aware thresholds (fullstack 75%, backend 85%, frontend 70%, research 0%, infrastructure 60%) prevent one-size-fits-all problems.

## Common Pitfalls

**Mutable Defaults** (S01): Use `field(default_factory=list)` not `field(default=[])` in dataclasses.

**Index Tracking** (S11): Step progression logic requires careful index tracking to avoid off-by-one errors.

**Subprocess Output Parsing** (S14): Pytest output has multiple formats; JSON-report is most reliable. Handle parsing failures gracefully.

**State Preservation on Failure** (S16, S18): Agent failure must block the sprint but preserve all state to enable resume. Cancel must preserve all state for later resume without data loss.

**Documentation Drift** (S24): Enum renames or model changes require a linting pass to update docs. Stale enum names in kanban docs caused confusion.