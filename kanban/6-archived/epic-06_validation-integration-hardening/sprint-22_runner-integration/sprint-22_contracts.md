# API Contracts — Sprint 22: Runner Integration

## Deliverables
- Updated `src/execution/runner.py` with dependency validation, hooks, retry, and RunConfig
- Updated `src/execution/resume.py` with validate_transition
- `tests/test_runner_integration.py` (12 tests)

## Backend Contracts
### SprintRunner
- `SprintRunner.__init__(hook_registry=None, run_config=None)` — accepts optional HookRegistry and RunConfig
- `SprintRunner.run()` — calls validate_sprint_dependencies() before start_sprint(), evaluates hooks at PRE_SPRINT, PRE_STEP, POST_STEP, PRE_COMPLETION
- `SprintRunner._execute_with_retry()` — retry logic driven by RunConfig

### Hook Evaluation
- Blocking hook failure raises and blocks sprint execution
- Non-blocking hook failure logs warning and continues
- Hook context includes agent_results from run_state

### Resume
- `resume_sprint()` — uses validate_transition for state checks

## Frontend Contracts
- N/A
