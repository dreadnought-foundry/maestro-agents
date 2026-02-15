# Sprint 8: Comprehensive Testing

## Goal
Dedicated testing sprint covering edge cases, error paths, smoke tests, and integration testing of the full pipeline.

## Deliverables
- Extended test coverage for handlers (edge cases, malformed input)
- Extended test coverage for adapters (concurrent access, large data)
- Smoke test script (`tests/smoke_test.py`) that runs the orchestrator end-to-end
- Integration test verifying agent → tool → handler → adapter pipeline

## Tasks
1. Add edge case tests to test_handlers.py (empty strings, unicode, very long inputs)
2. Add error path tests (invalid JSON in tasks field, missing required fields)
3. Add adapter tests for state persistence across multiple operations
4. Create smoke test script that runs orchestrator with InMemoryAdapter
5. Test all 4 agent definitions can be imported and have valid tool references
6. Verify MCP server creates all 7 tools with correct schemas

## Acceptance Criteria
- All tests pass: `uv run pytest tests/ -v`
- Smoke test runs without errors
- No untested error paths in handlers

## Dependencies
- Sprint 7 (all code must be complete)
