# API Contracts — Sprint 29: KanbanAdapter

## Deliverables
- `src/adapters/kanban.py` — KanbanAdapter (full WorkflowBackend implementation)
- `tests/test_kanban_adapter.py` — 36 tests

## API

### `KanbanAdapter(kanban_dir: Path | str = "kanban")`
Constructor. Raises `FileNotFoundError` if kanban directory doesn't exist.

### WorkflowBackend Methods (all async)
- `get_project_state()` → `ProjectState`
- `get_epic(epic_id)` → `Epic`
- `get_sprint(sprint_id)` → `Sprint`
- `list_epics()` → `list[Epic]`
- `list_sprints(epic_id=None)` → `list[Sprint]`
- `create_epic(title, description)` → `Epic`
- `create_sprint(epic_id, goal, tasks, dependencies, deliverables)` → `Sprint`
- `update_sprint(sprint_id, **fields)` → `Sprint`
- `get_status_summary()` → `dict`
- `start_sprint(sprint_id)` → `Sprint`
- `advance_step(sprint_id, step_output)` → `Sprint`
- `complete_sprint(sprint_id)` → `Sprint`
- `block_sprint(sprint_id, reason)` → `Sprint`
- `get_step_status(sprint_id)` → `dict`

### Filesystem Layout
- Sprints: `kanban/{column}/epic-NN_slug/sprint-NN_slug/sprint-NN_slug.md`
- Epics: `kanban/{column}/epic-NN_slug/_epic.md`
- State: `.claude/sprint-N-state.json`
- Suffixes: `--done`, `--blocked` on both file and directory names
