# API Contracts — Sprint 02: In-Memory Adapter

## Backend Contracts

### InMemoryAdapter
- Implements `WorkflowBackend` protocol
- `__init__()` — initializes empty dicts for epics and sprints
- `get_project_status() -> ProjectState`
- `list_epics() -> list[Epic]`
- `get_epic(epic_id) -> Epic`
- `create_epic(title, description) -> Epic` — auto-generates ID
- `list_sprints(epic_id=None) -> list[Sprint]`
- `get_sprint(sprint_id) -> Sprint`
- `create_sprint(epic_id, goal, tasks, dependencies, deliverables) -> Sprint`
- `update_sprint(sprint_id, **kwargs) -> Sprint`
- `get_status_summary() -> dict` — returns counts and progress percentage

## Frontend Contracts
- N/A

## Deliverables
- `src/adapters/__init__.py`
- `src/adapters/memory.py` — InMemoryAdapter implementing WorkflowBackend
