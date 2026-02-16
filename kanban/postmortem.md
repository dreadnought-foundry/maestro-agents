# Sprint Postmortems

## Sprint 01: Workflow Models and Interface

**Result**: Success | 5/5 steps | 1m

### What Was Built
- SprintStatus and EpicStatus enums in src/workflow/models.py
- Sprint, Epic, ProjectState dataclasses with sensible defaults
- WorkflowBackend Protocol class with 9 method signatures in src/workflow/interface.py
- Unit tests for model construction and enum values

### Lessons Learned
- Defining the protocol first (interface.py) before any implementation keeps downstream sprints focused
- Dataclasses with field(default_factory=list) avoid mutable default pitfalls

### Deferred Items
- Production SDK integration
- Real Claude API calls
- Field validation logic

---

## Sprint 02: In-Memory Adapter

**Result**: Success | 5/5 steps | 1m

### What Was Built
- InMemoryAdapter implementing all 9 WorkflowBackend protocol methods
- Dict-based storage with auto-generated IDs
- Status summary with counts and progress percentage
- No file I/O -- purely in-memory for fast testing

### Lessons Learned
- Having a test-friendly adapter first unlocks testing for all layers above
- Auto-ID generation (incrementing counter) keeps tests deterministic when reset

### Deferred Items
- MaestroAdapter full implementation
- Concurrent access handling
- Pagination for list operations

---

## Sprint 03: Tool Handlers

**Result**: Success | 8/8 steps | 2m

### What Was Built
- 7 pure async handler functions in src/tools/handlers.py
- Each handler follows the pattern: `async def handler(args, backend) -> dict`
- Returns MCP result format: `{"content": [{"type": "text", "text": "..."}]}`
- Comprehensive tests using InMemoryAdapter

### Lessons Learned
- Handler/tool separation pattern (pure async handlers testable without SDK) is the key architectural insight
- JSON string parsing for list fields (tasks, dependencies, deliverables) needs careful error handling

### Deferred Items
- Update/delete handlers
- Batch operations

---

## Sprint 04: Maestro Adapter

**Result**: Success | 7/7 steps | 2m

### What Was Built
- MaestroAdapter implementing WorkflowBackend with file-based persistence
- Directory structure: .maestro/state.json, .maestro/epics/, .maestro/sprints/
- asyncio.to_thread for sync file operations
- Integration tests using pytest tmp_path fixture

### Lessons Learned
- Using tmp_path for file-based adapter tests avoids side effects on real filesystem
- asyncio.to_thread wraps sync I/O cleanly for async protocol compliance

### Deferred Items
- MaestroAdapter lifecycle methods
- YAML frontmatter parsing
- File locking for concurrent access

---

## Sprint 05: MCP Server Factory

**Result**: Success | 6/6 steps | 1m

### What Was Built
- create_workflow_server(backend) factory function in src/tools/server.py
- 7 MCP tools registered with correct names, descriptions, and input schemas
- Closure-based backend binding: lambda args: handler(args, backend)
- Tool naming convention: mcp__maestro__{tool_name}

### Lessons Learned
- Closures to bind backend parameter keep tool registration clean
- Factory pattern (create_workflow_server) makes testing easy -- pass InMemoryAdapter

### Deferred Items
- Dynamic tool registration
- Tool-level authentication

---

## Sprint 06: Agent Definitions

**Result**: Success | 5/5 steps | 1m

### What Was Built
- 4 AgentDefinition instances: epic_breakdown, sprint_spec, research, status_report
- TOOL_PREFIX and WORKFLOW_TOOLS shared constants
- Each agent has description, prompt, tools list, and model selection
- Tool lists reference MCP tool names with correct prefix

### Lessons Learned
- Scoping tool access per agent (read-only for research, full access for breakdown) improves safety
- Domain-agnostic prompts (not coding-specific) make agents reusable across project types

### Deferred Items
- Production SDK integration
- Agent prompt tuning
- Per-project configuration overrides

---

## Sprint 07: Orchestrator and Integration

**Result**: Success | 4/4 steps | 2m

### What Was Built
- run_orchestrator() entry point wiring all agents and tools together
- CLI interface via __main__.py
- Makefile `run` target
- End-to-end integration with MaestroAdapter

### Lessons Learned
- Wiring together all components reveals integration gaps not caught by unit tests
- Having a CLI entry point early makes manual testing much easier
- The orchestrator pattern (delegating to specialist agents) keeps concerns separated

### Deferred Items
- Production deployment configuration
- Agent response streaming
- Multi-turn conversation support

---

## Sprint 08: Comprehensive Testing

**Result**: Success | 6/6 steps | 3m

### What Was Built
- Extended handler tests with edge cases (empty strings, unicode, long inputs)
- Error path tests for malformed JSON and missing fields
- Adapter tests for state persistence across operations
- Smoke test script running orchestrator with InMemoryAdapter
- Agent definition import and tool reference validation
- MCP server schema verification for all 7 tools

### Lessons Learned
- Dedicated testing sprints catch edge cases that implementation sprints miss
- Smoke tests are invaluable for catching integration issues
- Testing agent definitions for valid tool references prevents runtime surprises

### Deferred Items
- Performance benchmarking suite
- Mutation testing integration
- CI/CD pipeline setup

---

## Sprint 09: Step Models and Status Tracking

**Result**: Success | 3/3 steps | ~15m

### What Was Built
- `StepStatus` enum with TODO, IN_PROGRESS, DONE, FAILED, SKIPPED values
- `Step` dataclass with id, name, status, agent, output, started_at, completed_at, metadata
- `SprintTransition` dataclass with from_status, to_status, timestamp, reason
- Updated `Sprint` model with steps and transitions fields
- 12 tests covering all new models

### Lessons Learned
- Defining dataclasses with sensible defaults first made testing straightforward
- Keeping backward compatibility with existing Sprint tests required careful field defaults
- Enum-based status tracking is cleaner than string constants for state management

### Deferred Items
- Step-level timing utilities (duration calculation)
- Step template system (predefined step sequences per sprint type)

---

## Sprint 10: Lifecycle Protocol Methods

**Result**: Success | 3/3 steps | ~20m

### What Was Built
- Five new protocol methods on WorkflowBackend: start_sprint, advance_step, complete_sprint, block_sprint, get_step_status
- `InvalidTransitionError` exception with descriptive from/to state messages
- Valid state transitions defined as data (TODO->IN_PROGRESS, IN_PROGRESS->DONE, IN_PROGRESS->BLOCKED, BLOCKED->IN_PROGRESS)
- 15 tests for transition validation

### Lessons Learned
- Defining valid transitions as data rather than hardcoded logic made the state machine testable and extensible
- Protocol-level definitions ensure all backends implement the same interface
- Descriptive error messages on InvalidTransitionError save debugging time

### Deferred Items
- Unblock/resume operation
- Sprint rollback (undo last step)

---

## Sprint 11: InMemory Lifecycle Implementation

**Result**: Success | 3/3 steps | ~25m

### What Was Built
- Full lifecycle implementation in InMemoryAdapter: start_sprint, advance_step, complete_sprint, block_sprint, get_step_status
- Transition validation using rules from Sprint 10
- Step output capture on advance
- Block/resume cycle support
- 25 tests covering all lifecycle operations

### Lessons Learned
- Having the protocol defined first (Sprint 10) made implementation straightforward
- In-memory testing proved essential for fast iteration on the sprint runner later
- Step progression logic requires careful index tracking to avoid off-by-one errors

### Deferred Items
- MaestroAdapter lifecycle implementation
- Step timing auto-population

---

## Sprint 12: Agent Base Infrastructure

**Result**: Success | 3/3 steps | ~15m

### What Was Built
- `ExecutionAgent` protocol with name, description, and async execute method
- `StepContext` dataclass providing step, sprint, epic, project_root, and previous_outputs
- `AgentResult` dataclass with success, output, files_modified, files_created, test_results, coverage, review_verdict, deferred_items
- `AgentRegistry` with register, get_agent, and list_agents methods
- 10 tests covering all infrastructure types

### Lessons Learned
- StepContext design is critical -- agents should never reach into global state
- AgentResult.deferred_items enables the learning circle pattern across sprints
- Registry pattern decouples step types from agent implementations cleanly

### Deferred Items
- Agent execution metrics (tokens, duration)
- Agent configuration/settings per project

---

## Sprint 13: Product Engineer Agent

**Result**: Success | 3/3 steps | ~20m

### What Was Built
- `ProductEngineerAgent` implementing ExecutionAgent protocol, using Claude SDK with Read, Write, Edit, Glob, Grep, Bash tools
- `MockProductEngineerAgent` for runner testing without API calls
- Agent prompt focused on TDD: write tests first, then implementation
- File tracking in AgentResult (files_modified, files_created)
- 8 tests using mock-based approach

### Lessons Learned
- Mock agent is essential for testing the runner without incurring API costs
- TDD-focused prompting produces more testable code from the agent
- Tool scoping (limiting available tools) keeps agent behavior predictable

### Deferred Items
- File change diffing (before/after)
- Agent prompt tuning based on success rates
- Production SDK integration for real API calls

---

## Sprint 14: Test Runner Agent

**Result**: Success | 3/3 steps | ~20m

### What Was Built
- `TestRunnerAgent` implementing ExecutionAgent protocol, runs pytest via subprocess
- `MockTestRunnerAgent` for runner testing without real test execution
- Pytest output parsing into structured test_results dict (total, passed, failed, errors, coverage_pct, failed_tests)
- Coverage percentage extraction into AgentResult.coverage
- 10 tests covering result structure and parsing

### Lessons Learned
- Parsing pytest output requires handling multiple output formats (json-report is most reliable)
- Mock agent with configurable results enables testing gate thresholds later
- Structured test_results format enables downstream gates to make decisions

### Deferred Items
- Test result trending across sprints
- Flaky test detection
- Coverage delta tracking (before/after sprint)

---

## Sprint 15: Quality Engineer Agent

**Result**: Success | 3/3 steps | ~20m

### What Was Built
- `QualityEngineerAgent` implementing ExecutionAgent protocol, uses Claude SDK with read-only tools (Read, Grep, Glob)
- `MockQualityEngineerAgent` with configurable verdict for testing
- Review verdict system: "approve" or "request_changes"
- Deferred items surfacing for learning circle
- 8 tests covering approve and request_changes paths

### Lessons Learned
- Read-only tool scoping prevents accidental code modification during review
- Previous_outputs from StepContext gives the reviewer full context of what was done
- Deferred items from quality review feed naturally into the learning circle

### Deferred Items
- Review severity levels (blocker, warning, suggestion)
- Review checklist customization per sprint type

---

## Sprint 16: Core Sprint Runner

**Result**: Success | 3/3 steps | ~25m

### What Was Built
- `SprintRunner` class with run(), resume(), and cancel() methods
- `RunResult` dataclass with sprint_id, success, steps_completed, steps_total, agent_results, deferred_items, duration_seconds
- Step dispatch system routing step types to registered agents via AgentRegistry
- Progress callback support (on_progress called after each step)
- Deferred items aggregation from all AgentResults into RunResult
- Failure handling: agent failure blocks the sprint
- 12 tests using mock agents and InMemoryAdapter

### Lessons Learned
- Composing InMemoryAdapter + mock agents makes the runner fully testable without I/O
- Progress callbacks enable both CLI output and future UI integration
- Aggregating deferred items across all steps creates a clear learning circle

### Deferred Items
- Parallel step execution
- Cost tracking (API tokens per run)
- Real-time progress streaming

---

## Sprint 17: Dependency Checking and Step Ordering

**Result**: Success | 3/3 steps | ~20m

### What Was Built
- `DependencyNotMetError` exception listing unmet dependency sprint IDs
- `validate_sprint_dependencies()` function checking all dependent sprints are completed
- `validate_step_order()` function ensuring steps execute in correct sequence
- Integration into SprintRunner.run() -- checks dependencies before starting
- 10 tests covering no dependencies, met dependencies, unmet dependencies, and step ordering

### Lessons Learned
- Dependency validation as a separate module keeps the runner clean
- Listing specific unmet dependencies in the error message aids debugging
- Step ordering validation prevents subtle bugs from out-of-order execution

### Deferred Items
- Circular dependency detection
- Auto-resolution of dependencies

---

## Sprint 18: Pause, Resume, and Retry Logic

**Result**: Success | 3/3 steps | ~20m

### What Was Built
- `resume()` on SprintRunner -- finds last completed step, continues from next
- Retry logic with configurable max_retries per step
- `cancel()` -- graceful stop, blocks sprint with reason, preserves state
- `RunConfig` dataclass with max_retries and retry_delay_seconds
- 10 tests covering resume, retry, max retries exceeded, and cancel scenarios

### Lessons Learned
- Resume logic depends on accurate step status tracking from the lifecycle layer
- Retry with fixed delay is sufficient for v2; exponential backoff adds complexity without clear benefit yet
- Cancel must preserve all state to enable later resume without data loss

### Deferred Items
- Exponential backoff on retries
- Checkpoint to disk for crash recovery
- Notification on pause/failure

---

## Sprint 19: Hook System Architecture

**Result**: Success | 3/3 steps | ~25m

### What Was Built
- `HookPoint` enum: PRE_SPRINT, PRE_STEP, POST_STEP, PRE_COMPLETION
- `Hook` protocol with hook_point and async evaluate method
- `HookContext` dataclass with sprint, step, agent_result, run_state
- `HookResult` dataclass with passed, message, blocking flag, deferred_items
- `HookRegistry` with register, get_hooks, and evaluate_all methods
- MockHook for testing
- Integration into SprintRunner
- 12 tests covering registry, evaluate_all, blocking vs non-blocking behavior

### Lessons Learned
- Separating blocking from non-blocking hooks allows warnings without halting execution
- HookResult.deferred_items feeds the learning circle from enforcement gates
- Composable hook system means gates can be added or removed without changing runner code

### Deferred Items
- Hook ordering/priority
- Async hook execution for non-blocking hooks
- Hook metrics dashboard

---

## Sprint 20: Concrete Enforcement Gates

**Result**: Success | 3/3 steps | ~25m

### What Was Built
- `CoverageGate` -- POST_STEP hook checking AgentResult.coverage >= threshold
- `QualityReviewGate` -- PRE_COMPLETION hook checking review_verdict == "approve"
- `StepOrderingEnforcement` -- PRE_STEP hook validating step dependencies
- `RequiredStepsGate` -- PRE_COMPLETION hook validating all required steps are done
- `create_default_hooks(sprint_type)` -- returns sensible preset hooks per sprint type
- Coverage thresholds per type: fullstack 75%, backend 85%, frontend 70%, research 0%, infrastructure 60%
- 15 tests covering all gates and threshold configurations

### Lessons Learned
- Sprint-type-aware thresholds prevent one-size-fits-all coverage problems
- create_default_hooks() provides easy-mode setup while keeping individual gates composable
- Quality review gate as PRE_COMPLETION ensures review happens before sprint closes

### Deferred Items
- Custom gate creation API for project-specific rules
- Gate bypass with justification
- Historical gate pass rates

---

## Sprint 21: End-to-End Integration and CLI

**Result**: Success | 3/3 steps | ~30m

### What Was Built
- `run_sprint()` convenience function wiring backend, agents, hooks, and runner together
- CLI entry point: `python -m src.execution run <sprint_id>`
- Default agent registry with all agents registered
- Makefile `run-sprint` target
- Full integration tests: create epic, create sprint, run sprint, verify completion
- Integration test with hooks: coverage gate blocks undercovered sprint
- Integration test: resume after failure
- Updated docs/phase-2/overview.md with final architecture

### Lessons Learned
- Convenience functions dramatically reduce boilerplate for common operations
- End-to-end integration tests with mock agents validate the full pipeline without API costs
- CLI entry point makes the system usable outside of tests immediately

### Deferred Items
- Interactive mode (pause at gates for user input)
- Web UI for sprint monitoring
- Plugin system for custom agents

---

## Sprint 22b: Kanban TUI

**Result**: Success | 10/10 tasks | tooling sprint

### What Was Built
- Rich/Textual-based terminal UI for visualizing the kanban board
- `kanban_tui/app.py` -- main KanbanBoard Textual app
- `kanban_tui/board.py` -- board layout and column rendering
- `kanban_tui/cli.py` -- CLI entry point
- `kanban_tui/scanner.py` -- filesystem scanning and frontmatter parsing
- `kanban_tui/widgets.py` -- Column, EpicCard, SprintCard, DetailPanel widgets
- Supports all three sprint layout patterns (epic-grouped folders, standalone flat files, flat files inside epic)
- Arrow key navigation and card move operations via shutil.move()

### Lessons Learned
- Scanning three different filesystem conventions requires careful pattern matching; testing with real kanban contents is essential
- Textual widget hierarchy design should be planned upfront to avoid refactoring mid-sprint
- Standalone sprints need explicit handling to avoid being swallowed by epic grouping logic

### Deferred Items
- Filtering by epic or status
- Search functionality
- Sprint creation from within the TUI
- Watch mode for external changes

---

## Sprint 22: Runner Integration

**Result**: Success | 8/8 tasks | 12 tests passing

### What Was Built
- Wired validate_sprint_dependencies() into SprintRunner.run() before start_sprint()
- Added optional HookRegistry support in SprintRunner.__init__()
- Implemented hook evaluation at PRE_SPRINT, PRE_STEP, POST_STEP, PRE_COMPLETION
- Blocking hook failure blocks sprint; non-blocking continues
- Added optional RunConfig support in SprintRunner.__init__()
- Implemented retry logic via _execute_with_retry()
- Stored agent_results in run_state dict for hook contexts
- Fixed resume_sprint() to use validate_transition

### Lessons Learned
- Wiring multiple cross-cutting concerns (hooks, retry, validation) into a runner requires careful ordering of operations
- Storing agent_results in run_state enables hooks to make decisions based on prior step outcomes
- resume_sprint must reuse the same validation paths as the initial run to avoid state inconsistencies

### Deferred Items
- No deferred items

---

## Sprint 23: Validation E2E

**Result**: Success | 10/10 tasks | 10 tests passing

### What Was Built
- 10 end-to-end tests validating the full sprint lifecycle with integrated runner
- Multi-type sprint (implement/test/review) through runner with hooks
- Coverage gate blocking low-coverage sprints via runner
- Quality review gate blocking unapproved sprints via runner
- Sprint with 12 steps completing correctly
- Empty sprint completing immediately
- Deferred items collected across mixed agent types
- create_default_registry handling all standard step types
- Previous outputs accumulating correctly across steps
- Full lifecycle test: epic -> sprint -> run -> DONE

### Lessons Learned
- E2E tests that exercise the full stack (runner + hooks + gates + agents) catch integration bugs that unit tests miss
- Testing gate blocking behavior requires careful mock setup to simulate both pass and fail verdicts
- Deferred item collection across mixed agent types validates the cross-cutting data flow

### Deferred Items
- No deferred items

---

## Sprint 24: CLI Fix & Kanban Doc Cleanup

**Result**: Success | 5/5 tasks | 5 tests passing

### What Was Built
- Import guard for claude_agent_sdk in src/agents/definitions.py (try/except wrapping)
- Fixed stale enum names in sprint-09 doc (PENDING -> TODO, COMPLETED -> DONE)
- Fixed stale enum names in sprint-10 doc (PLANNED -> TODO, COMPLETED -> DONE)
- tests/test_cli.py with 5 tests verifying CLI module imports and all __init__.py exports

### Lessons Learned
- Optional SDK dependencies must always be guarded with try/except to prevent import crashes in environments where they are not installed
- Kanban documentation drifts when enum values are renamed; a linting pass should follow any enum refactor
- Verifying all __init__.py exports are importable catches broken re-exports early

### Deferred Items
- No deferred items
