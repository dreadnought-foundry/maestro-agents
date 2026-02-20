# Postmortem — Sprint 26: End-to-End Sprint Execution

**Result**: Success | 415 tests passing | 0 regressions
**Date**: 2026-02-20

## What Was Built
- `create_registry()` — wires real agents (ProductEngineer, TestRunner, QualityEngineer) with ClaudeCodeExecutor as the default
- `create_test_registry()` — mock agents for fast unit testing (renamed from `create_default_registry`)
- `run_sprint()` now defaults to real execution; `mock=True` opts into test agents
- CLI `--mock` flag for debugging without burning tokens, `--model` flag for model selection
- QualityEngineerAgent now parses `review_verdict` from executor output (required by QualityReviewGate)
- 6 regression tests validating real registry wiring and verdict parsing

## Lessons Learned
- Flipping the default from mock to real exposed a test (`test_run_sprint_convenience_function`) that implicitly relied on mocks — tests should always be explicit about their dependencies
- The QualityReviewGate/QualityEngineerAgent gap (gate expects `review_verdict` but agent never set it) was only discoverable by tracing the full pipeline — unit tests for each component individually wouldn't catch this
- Backwards-compat alias (`create_default_registry = create_test_registry`) prevents breakage in external consumers while making the rename clean internally

## Deferred Items
- End-to-end execution with a real sprint through the full pipeline (runner + real agents + gates + artifacts) — validated at the wiring level but not run against a live sprint yet
