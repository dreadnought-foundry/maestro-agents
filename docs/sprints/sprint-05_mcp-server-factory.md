# Sprint 5: MCP Server Factory

## Goal
Wire handler functions into @tool decorators and create an MCP server that agents can use. This is the glue between pure logic and the SDK.

## Deliverables
- `src/tools/server.py` — `create_workflow_server(backend)` factory function
- `src/tools/__init__.py` — re-exports

## Tasks
1. Import all handlers from handlers.py
2. Create tool wrappers using `tool()` decorator for each handler
3. Use closures to bind the backend parameter: `lambda args: handler(args, backend)`
4. Define tool names, descriptions, and input schemas
5. Bundle all tools into an MCP server via `create_sdk_mcp_server`
6. Verify tool naming convention: `mcp__maestro__{tool_name}`

## Tool Registry

| Tool Name | Input Schema | Handler |
|-----------|-------------|---------|
| `get_project_status` | `{}` | `get_project_status_handler` |
| `list_epics` | `{}` | `list_epics_handler` |
| `get_epic` | `{epic_id: str}` | `get_epic_handler` |
| `list_sprints` | `{epic_id: str}` (optional) | `list_sprints_handler` |
| `get_sprint` | `{sprint_id: str}` | `get_sprint_handler` |
| `create_epic` | `{title: str, description: str}` | `create_epic_handler` |
| `create_sprint` | `{epic_id: str, goal: str, tasks: str, dependencies: str, deliverables: str}` | `create_sprint_handler` |

## Acceptance Criteria
- `create_workflow_server(backend)` returns a valid MCP server
- All 7 tools are registered with correct names and schemas
- Manual test: create server with InMemoryAdapter, verify tool list

## Dependencies
- Sprint 3 (handlers)
