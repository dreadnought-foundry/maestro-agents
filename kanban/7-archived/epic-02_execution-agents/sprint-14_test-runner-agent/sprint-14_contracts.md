# API Contracts — Sprint 14: Test Runner Agent

## Deliverables
- src/agents/execution/test_runner.py
- Updated mocks.py (MockTestRunnerAgent)
- tests/test_test_runner.py (10 tests)

## Backend Contracts
### Agents
- `TestRunnerAgent` — implements ExecutionAgent, runs pytest via subprocess with --json-report and --cov flags
- `MockTestRunnerAgent` — returns configurable canned test results

### AgentResult.test_results Format
```python
{
    "total": 48,
    "passed": 46,
    "failed": 2,
    "errors": 0,
    "coverage_pct": 87.5,
    "failed_tests": ["test_foo", "test_bar"],
}
```

### Behavior
- Runs pytest and captures structured results
- Extracts coverage percentage into AgentResult.coverage
- Lists failed test names in test_results

## Frontend Contracts
- N/A
