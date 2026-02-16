# API Contracts — Sprint 17: Dependency Checking and Step Ordering

## Deliverables
- src/execution/dependencies.py
- Updated src/execution/runner.py
- tests/test_dependencies.py (10 tests)

## Backend Contracts
### Exceptions
- `DependencyNotMetError(sprint_id, unmet_dependencies: list[str])` — raised when sprint dependencies are not satisfied

### Functions
- `validate_sprint_dependencies(sprint_id, backend) -> list[str]` — returns list of unmet dependency sprint IDs, empty if all met
- `validate_step_order(sprint, current_step) -> bool` — returns True if step can execute given completed steps

### Integration
- SprintRunner.run() calls validate_sprint_dependencies before starting sprint execution

## Frontend Contracts
- N/A
