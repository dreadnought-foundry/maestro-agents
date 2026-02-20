---
sprint: 25
title: "Claude Code Agent Executor"
type: backend
epic: 7
status: done
created: 2026-02-15T00:00:00Z
started: 2026-02-15T00:00:00Z
completed: 2026-02-20T19:28:01Z
hours: 139.5
---

# Sprint 25: Claude Code Agent Executor

## Overview

| Field | Value |
|-------|-------|
| Sprint | 25 |
| Title | Claude Code Agent Executor |
| Type | backend |
| Epic | 7 |
| Status | Planning |
| Created | 2026-02-15 |

## Goal

Build a `ClaudeCodeExecutor` class that uses the `claude-agent-sdk` to run prompts through Claude Code sessions, capturing output into structured `AgentResult` objects. Wire it into the three execution agents to replace their `NotImplementedError` stubs.

## Implementation Notes

Originally specced for raw subprocess calls, but rewritten to use the claude-agent-sdk's `query()` function per project direction. The SDK handles all subprocess management internally. Supports both stateless (`query()` per call) and persistent (`ClaudeSDKClient` reuse) modes.

## Tasks

### Phase 1: Planning
- [x] Review claude-agent-sdk API surface (query, ClaudeSDKClient, message types)
- [x] Design executor around SDK's query() function

### Phase 2: Implementation
- [x] Create `src/agents/execution/claude_code.py` with `ClaudeCodeExecutor`
- [x] Implement via SDK `query()` with `ClaudeAgentOptions`
- [x] Implement output parsing — extract text from AssistantMessage/ResultMessage
- [x] Implement timeout handling and error capture
- [x] Wire into `ProductEngineerAgent._run_claude` — replace NotImplementedError
- [x] Wire into `TestRunnerAgent._run_claude` — replace NotImplementedError
- [x] Wire into `QualityEngineerAgent._run_claude` — replace NotImplementedError
- [x] Keep mock agents working — executor is injected, not hardcoded

### Phase 3: Validation
- [x] Test executor with real SDK (simple prompt, file tracking)
- [x] Test timeout handling
- [x] Verify mock agents still pass all existing tests (409 passed)
- [x] Real SDK integration tests with --run-slow flag

## Deliverables

- `src/agents/execution/claude_code.py` — ClaudeCodeExecutor (SDK-based)
- Updated `product_engineer.py`, `test_runner.py`, `quality_engineer.py` — wired to executor
- `tests/test_claude_code_executor.py` — real SDK integration tests + mock regression

## Acceptance Criteria

- [x] `ClaudeCodeExecutor.run()` uses claude-agent-sdk and returns an `AgentResult`
- [x] All three execution agents use the executor instead of raising `NotImplementedError`
- [x] Executor is injectable — agents accept it as a constructor parameter
- [x] Timeout produces a failed `AgentResult` with clear error message
- [x] All existing mock-based tests still pass (409 passed, 2 skipped)

## Dependencies

- **Sprints**: None — builds on existing agent protocol
- **External**: `claude` CLI installed and on PATH
