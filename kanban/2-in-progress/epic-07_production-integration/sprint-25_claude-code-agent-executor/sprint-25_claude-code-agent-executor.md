---
sprint: 25
title: "Claude Code Agent Executor"
type: backend
epic: 7
status: in-progress
created: 2026-02-15T00:00:00Z
started: 2026-02-15T00:00:00Z
completed: null
hours: null
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

Build a `ClaudeCodeExecutor` class that invokes the `claude` CLI as a subprocess, passes a prompt, captures the output, and returns a structured `AgentResult`. Then wire it into the three execution agents to replace their `NotImplementedError` stubs.

## Interface Contract (define first)

```python
class ClaudeCodeExecutor:
    """Executes prompts via the claude CLI subprocess."""

    async def run(
        self,
        prompt: str,
        working_dir: Path,
        timeout: int = 300,
        allowed_tools: list[str] | None = None,
    ) -> AgentResult:
        """Run a prompt through claude CLI and return structured result."""
        ...
```

The executor will:
- Invoke `claude --print --output-format json` with the prompt piped to stdin
- Set the working directory so file operations target the right project
- Use `--allowedTools` to restrict tool access per agent type
- Parse JSON output into `AgentResult` (success, output, files_modified, etc.)
- Handle timeout, exit codes, and stderr

## Tasks

### Phase 1: Planning
- [ ] Review `claude --help` output for available flags and output formats
- [ ] Design the subprocess invocation and output parsing

### Phase 2: Implementation
- [ ] Create `src/agents/execution/claude_code.py` with `ClaudeCodeExecutor`
- [ ] Implement subprocess invocation with `asyncio.create_subprocess_exec`
- [ ] Implement output parsing — extract result from claude JSON output
- [ ] Implement timeout handling and error capture
- [ ] Wire into `ProductEngineerAgent._run_claude` — replace NotImplementedError
- [ ] Wire into `TestRunnerAgent._run_claude` — replace NotImplementedError
- [ ] Wire into `QualityEngineerAgent._run_claude` — replace NotImplementedError
- [ ] Keep mock agents working — executor is injected, not hardcoded

### Phase 3: Validation
- [ ] Test executor with a simple prompt (e.g., "What is 2+2?")
- [ ] Test timeout handling
- [ ] Test error handling (bad prompt, claude not on PATH)
- [ ] Verify mock agents still pass all existing tests

## Deliverables

- `src/agents/execution/claude_code.py` — ClaudeCodeExecutor
- Updated `product_engineer.py`, `test_runner.py`, `quality_engineer.py` — wired to executor
- Tests for the executor (mocking the subprocess for unit tests)

## Acceptance Criteria

- [ ] `ClaudeCodeExecutor.run()` invokes `claude` CLI and returns an `AgentResult`
- [ ] All three execution agents use the executor instead of raising `NotImplementedError`
- [ ] Executor is injectable — agents accept it as a constructor parameter
- [ ] Timeout produces a failed `AgentResult` with clear error message
- [ ] Missing `claude` CLI produces a clear error, not a crash
- [ ] All existing mock-based tests still pass

## Dependencies

- **Sprints**: None — builds on existing agent protocol
- **External**: `claude` CLI installed and on PATH
