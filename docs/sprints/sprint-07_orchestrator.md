# Sprint 7: Orchestrator and Integration

## Goal
Wire everything together into a working entry point. Set up the orchestrator agent that delegates to specialists, and provide a CLI interface.

## Deliverables
- `src/agents/orchestrator.py` — `run_orchestrator(request, project_root)` + CLI entry
- `src/agents/__init__.py` — re-exports
- Updated `Makefile` with `run` target
- Updated `main.py` to call orchestrator

## Tasks
1. Implement `run_orchestrator()`:
   - Create MaestroAdapter for the given project root
   - Create MCP workflow server from the adapter
   - Register all 4 agents
   - Configure orchestrator with system prompt, tools, and agents
   - Run query loop and print results
2. Implement `main()` CLI wrapper accepting request as argv
3. Update `Makefile` with `run` target
4. End-to-end manual test with real requests

## Test Scenarios
1. `"What's the project status?"` — should use status_report agent
2. `"Break down a user authentication system into epics and sprints"` — should use epic_breakdown agent
3. `"Write a sprint spec for implementing OAuth2"` — should use sprint_spec agent
4. `"Research the current state of Python async web frameworks"` — should use research agent

## Acceptance Criteria
- Orchestrator correctly delegates to the right agent based on request
- Agents can call MCP tools and get results from MaestroAdapter
- `.maestro/` directory gets created with state and spec files
- CLI works: `uv run python -m src.agents.orchestrator "your request"`
- All existing tests still pass

## Dependencies
- All previous sprints (1-6)
