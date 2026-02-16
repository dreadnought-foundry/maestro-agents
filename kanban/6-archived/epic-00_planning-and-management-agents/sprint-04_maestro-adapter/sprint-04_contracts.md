# API Contracts — Sprint 04: Maestro Adapter

## Backend Contracts

### MaestroAdapter
- Implements `WorkflowBackend` protocol
- `__init__(project_root: Path)` — sets base directory for .maestro/
- All 9 protocol methods implemented with file I/O
- Uses `asyncio.to_thread` for sync file operations
- Auto-creates directory structure on first operation

### File Structure
```
.maestro/
    state.json              # {"project_name": "...", "epics": [...], "sprints": [...]}
    epics/epic-01.md        # Markdown with YAML frontmatter
    sprints/sprint-01.md    # Markdown with YAML frontmatter
```

## Frontend Contracts
- N/A

## Deliverables
- `src/adapters/maestro.py` — MaestroAdapter implementing WorkflowBackend
- `tests/test_adapter.py` — Integration tests using pytest tmp_path
