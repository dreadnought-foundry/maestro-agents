# API Contracts — Sprint 03: Tool Handlers

## Backend Contracts

### Handler Signature Pattern
```python
async def handler_name(args: dict[str, Any], backend: WorkflowBackend) -> dict[str, Any]:
    # Returns: {"content": [{"type": "text", "text": "..."}]}
```

### Handlers
- `get_project_status_handler(args, backend)` — returns JSON summary
- `list_epics_handler(args, backend)` — returns all epics
- `get_epic_handler(args, backend)` — requires `epic_id` in args
- `list_sprints_handler(args, backend)` — optional `epic_id` filter
- `get_sprint_handler(args, backend)` — requires `sprint_id` in args
- `create_epic_handler(args, backend)` — requires `title`, `description`
- `create_sprint_handler(args, backend)` — requires `epic_id`, `goal`, `tasks`, `dependencies`, `deliverables`

## Frontend Contracts
- N/A

## Deliverables
- `src/tools/handlers.py` — 7 handler functions
- `tests/test_handlers.py` — Comprehensive tests using InMemoryAdapter
