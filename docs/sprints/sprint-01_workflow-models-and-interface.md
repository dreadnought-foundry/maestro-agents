# Sprint 1: Workflow Models and Interface

## Goal
Define the domain models and abstract protocol that everything else builds on.

## Deliverables
- `src/workflow/models.py` — Sprint, Epic, ProjectState dataclasses with status enums
- `src/workflow/interface.py` — WorkflowBackend Protocol class
- `tests/test_models.py` — Unit tests for dataclass construction and enum values

## Tasks
1. Create `src/workflow/__init__.py`
2. Define `SprintStatus` and `EpicStatus` enums in `models.py`
3. Define `Sprint`, `Epic`, `ProjectState` dataclasses in `models.py`
4. Define `WorkflowBackend` Protocol in `interface.py` with 9 methods
5. Write tests for model construction, defaults, and enum values

## Acceptance Criteria
- All dataclasses can be instantiated with required fields
- Optional fields have sensible defaults (empty lists, empty dicts)
- Protocol class defines all 9 methods with correct signatures
- All tests pass

## Dependencies
None — this is the foundation.
