# Postmortem — Sprint 25: Claude Code Agent Executor

**Result**: Success | All tasks complete | 409 tests passing (2 slow skipped by default)
**Date**: 2026-02-20

## What Was Built
- `src/agents/execution/claude_code.py` — ClaudeCodeExecutor using claude-agent-sdk `query()` function
- Wired executor into ProductEngineerAgent, TestRunnerAgent, QualityEngineerAgent (replaced NotImplementedError stubs)
- Real SDK integration tests with `@pytest.mark.slow` flag
- File operation tracking (Write = created, Edit = modified) from ToolUseBlock inspection

## Key Decisions
- Used SDK's `query()` function (stateless, per-call) rather than `ClaudeSDKClient` persistent sessions — persistent mode doesn't work from within Claude Code due to subprocess limitations
- Executor is injectable via constructor parameter — agents work with mock executor (tests) or real executor (production)
- Used haiku model + max_turns=1 for SDK integration tests to minimize API round-trip time

## Lessons Learned
- The claude-agent-sdk's `connect()` hangs when invoked from within a Claude Code session — the CLAUDECODE env var must be stripped, and even then SubprocessCLITransport doesn't support persistent sessions in this context
- SDK tests are bottlenecked by API latency (~6s per call: 3s subprocess spawn + 3s API round-trip), not local compute
- Consolidating SDK tests (batching agent types into one test) halved total slow-test time

## Deferred Items
- Persistent session reuse for faster SDK calls (blocked by SDK limitations within Claude Code)
