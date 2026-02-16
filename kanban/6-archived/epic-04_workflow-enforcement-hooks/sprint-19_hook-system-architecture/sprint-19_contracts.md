# API Contracts — Sprint 19: Hook System Architecture

## Deliverables
- src/execution/hooks.py
- Updated src/execution/runner.py
- tests/test_hooks.py (12 tests)

## Backend Contracts
### Enums
- `HookPoint` — PRE_SPRINT, PRE_STEP, POST_STEP, PRE_COMPLETION

### Protocol
- `Hook` — hook_point: HookPoint, async evaluate(context: HookContext) -> HookResult

### Dataclasses
- `HookContext` — sprint, step (optional), agent_result (optional), run_state
- `HookResult` — passed, message, blocking (default True), deferred_items

### Registry
- `HookRegistry.register(hook: Hook) -> None`
- `HookRegistry.get_hooks(point: HookPoint) -> list[Hook]`
- `HookRegistry.evaluate_all(point, context) -> list[HookResult]`

### Integration
- Blocking hook failure stops sprint execution and blocks the sprint
- Non-blocking hook failure logs warning but continues execution

## Frontend Contracts
- N/A
