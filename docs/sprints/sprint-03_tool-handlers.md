# Sprint 3: Tool Handlers

## Goal
Write the core business logic as pure handler functions. This is the most important sprint — all agent capabilities flow through these handlers.

## Deliverables
- `src/tools/handlers.py` — 7 handler functions
- `tests/test_handlers.py` — Comprehensive tests using InMemoryAdapter

## Tasks
1. Implement `get_project_status_handler` — returns JSON summary
2. Implement `list_epics_handler` — returns all epics
3. Implement `get_epic_handler` — returns single epic by ID
4. Implement `list_sprints_handler` — returns sprints, optionally filtered by epic_id
5. Implement `get_sprint_handler` — returns single sprint by ID
6. Implement `create_epic_handler` — creates epic from title + description
7. Implement `create_sprint_handler` — creates sprint from epic_id + goal + tasks + dependencies + deliverables
8. Write tests for each handler (happy path + edge cases)

## Handler Signature
All handlers follow the same pattern:
```python
async def handler_name(args: dict[str, Any], backend: WorkflowBackend) -> dict[str, Any]:
    # Returns: {"content": [{"type": "text", "text": "..."}]}
```

## Acceptance Criteria
- All 7 handlers work with InMemoryAdapter
- Handlers return proper MCP result format
- create_sprint_handler parses JSON strings for tasks/dependencies/deliverables
- Error cases handled (missing epic_id, invalid sprint_id)
- All tests pass

## Dependencies
- Sprint 1 (models)
- Sprint 2 (InMemoryAdapter for testing)
