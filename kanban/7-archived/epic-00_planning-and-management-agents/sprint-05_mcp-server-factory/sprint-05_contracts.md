# API Contracts — Sprint 05: MCP Server Factory

## Backend Contracts

### Factory Function
- `create_workflow_server(backend: WorkflowBackend) -> MCPServer`

### Tool Registry
| Tool Name | Input Schema | Handler |
|-----------|-------------|---------|
| `get_project_status` | `{}` | `get_project_status_handler` |
| `list_epics` | `{}` | `list_epics_handler` |
| `get_epic` | `{epic_id: str}` | `get_epic_handler` |
| `list_sprints` | `{epic_id: str}` (optional) | `list_sprints_handler` |
| `get_sprint` | `{sprint_id: str}` | `get_sprint_handler` |
| `create_epic` | `{title: str, description: str}` | `create_epic_handler` |
| `create_sprint` | `{epic_id, goal, tasks, dependencies, deliverables}` | `create_sprint_handler` |

## Frontend Contracts
- N/A

## Deliverables
- `src/tools/server.py` — `create_workflow_server(backend)` factory function
- `src/tools/__init__.py` — re-exports
