# API Contracts — Sprint 26: End-to-End Sprint Execution

## Deliverables
- `src/execution/convenience.py` — real and test registry functions
- `src/execution/cli.py` — `--mock` and `--model` CLI flags
- `src/agents/execution/quality_engineer.py` — review_verdict parsing
- `tests/test_e2e_integration.py` — 6 regression tests

## API Changes

### `create_registry(model="sonnet", max_turns=25) -> AgentRegistry`
New function. Returns registry with real agents backed by ClaudeCodeExecutor.

### `create_test_registry() -> AgentRegistry`
Renamed from `create_default_registry()`. Returns registry with mock agents.

### `run_sprint(..., mock=False) -> RunResult`
New `mock` parameter. Default (`False`) uses real agents. `True` uses test agents.

### CLI
```
python -m src.execution run <sprint_id>              # real agents (default)
python -m src.execution run <sprint_id> --mock       # mock agents
python -m src.execution run <sprint_id> --model opus # model selection
```

## Regression Tests
- `test_create_registry_returns_real_agents` — real agent classes with executor
- `test_create_test_registry_returns_mock_agents` — mock agent classes
- `test_run_sprint_mock_flag_uses_test_registry` — mock=True uses mocks
- `test_quality_engineer_parses_approve_verdict` — approve detection
- `test_quality_engineer_parses_request_changes_verdict` — request_changes detection
- `test_quality_engineer_no_verdict_in_output` — graceful None when absent
