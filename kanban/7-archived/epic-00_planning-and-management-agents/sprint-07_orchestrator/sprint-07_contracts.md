# API Contracts — Sprint 07: Orchestrator and Integration

## Deliverables
- `src/agents/orchestrator.py` — run_orchestrator() + CLI entry
- `src/agents/__init__.py` — re-exports

## Backend Contracts

### Functions
- `run_orchestrator(request: str, project_root: Path) -> None` — main entry point
- `main()` — CLI wrapper

### Integration Points
- Creates MaestroAdapter for project root
- Creates MCP workflow server from adapter
- Registers all 4 specialist agents
- Configures orchestrator with system prompt, tools, and agents

## Frontend Contracts
- CLI: `uv run python -m src.agents.orchestrator "your request"`
