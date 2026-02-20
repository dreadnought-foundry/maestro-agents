# API Contracts — Sprint 01: Workflow Models and Interface

## Backend Contracts

### Enums
- `SprintStatus` — TODO, IN_PROGRESS, DONE, BLOCKED
- `EpicStatus` — TODO, IN_PROGRESS, DONE

### Dataclasses
- `Sprint` — id, epic_id, goal, status, tasks, dependencies, deliverables
- `Epic` — id, title, description, sprints, status
- `ProjectState` — project_name, epics, sprints

### Protocol
- `WorkflowBackend` — 9 methods:
  - `get_project_status() -> ProjectState`
  - `list_epics() -> list[Epic]`
  - `get_epic(epic_id) -> Epic`
  - `create_epic(title, description) -> Epic`
  - `list_sprints(epic_id=None) -> list[Sprint]`
  - `get_sprint(sprint_id) -> Sprint`
  - `create_sprint(epic_id, goal, tasks, dependencies, deliverables) -> Sprint`
  - `update_sprint(sprint_id, **kwargs) -> Sprint`
  - `get_status_summary() -> dict`

## Frontend Contracts
- N/A

## Deliverables
- `src/workflow/models.py` — Sprint, Epic, ProjectState dataclasses with status enums
- `src/workflow/interface.py` — WorkflowBackend Protocol class
- `tests/test_models.py` — Unit tests for dataclass construction and enum values
