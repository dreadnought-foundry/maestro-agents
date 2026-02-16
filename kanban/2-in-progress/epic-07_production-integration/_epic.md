---
epic: 7
title: "Production Integration"
status: planning
created: 2026-02-15
started: null
completed: null
---

# Epic 07: Production Integration

## Overview

Wire the execution agents to run as Claude Code subprocesses so sprints execute for real. Currently every agent has a `_run_claude` stub that raises `NotImplementedError`. This epic replaces those stubs with actual Claude Code invocations — no API key needed, no extra cost, it runs through the same Claude Code session you already use.

## Why This Matters

The entire workflow system (runner, gates, hooks, agents) works end-to-end with mocks. But no agent has ever done real work. Without this epic:
- `ProductEngineerAgent._run_claude()` raises `NotImplementedError`
- `TestRunnerAgent`, `QualityEngineerAgent` — same, all stubs
- The orchestrator delegates to agents that can't actually execute
- The sprint runner goes through all the ceremony (gates, hooks, retry) but produces nothing

## Current State

- `src/agents/execution/product_engineer.py` — has `_run_claude` stub → `NotImplementedError`
- `src/agents/execution/test_runner.py` — same pattern
- `src/agents/execution/quality_engineer.py` — same pattern
- `src/agents/execution/mocks.py` — mock agents used in tests
- `src/execution/runner.py` — full runner, works, but only with mock agents
- `src/agents/definitions.py` — 4 planning agents with prompts (use `claude-agent-sdk`)
- `src/agents/orchestrator.py` — uses `ClaudeSDKClient` (requires SDK to be real)

## Approach

Instead of calling the Claude API directly (which costs money), execute agents as **Claude Code subprocesses** via the `claude` CLI. Each agent's `_run_claude` method will:
1. Build a prompt from the `StepContext`
2. Invoke `claude --print` (or similar) with the prompt and working directory
3. Parse the output into an `AgentResult`

This means:
- Zero API cost — runs through your existing Claude Code subscription
- Same model quality — uses whatever model Claude Code is configured with
- File access — agents can read/write files naturally
- Tool access — agents inherit Claude Code's tool capabilities

## Sprints

| Sprint | Title | Status |
|--------|-------|--------|
| 25 | Claude Code Agent Executor | in-progress |
| 26 | End-to-End Sprint Execution | planned |
| 27 | Sprint Lifecycle Automation | planned |

## Success Criteria

- All three execution agents (product_engineer, test_runner, quality_engineer) can execute for real
- At least one sprint can be run end-to-end with real Claude Code execution
- Agent output is captured and parsed into `AgentResult` correctly
- Errors from Claude Code are handled gracefully (timeout, failure)
- Mock agents still work for testing (no regression)

## Dependencies

- **External**: `claude` CLI available on PATH

## Deferred Items

- Streaming agent output in real-time → future enhancement
- Parallel agent execution → future enhancement
- Agent output caching to avoid re-running → future optimization
