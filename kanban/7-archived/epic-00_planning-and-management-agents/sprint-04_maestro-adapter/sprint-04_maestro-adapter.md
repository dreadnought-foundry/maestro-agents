# Sprint 4: Maestro Adapter

## Goal
Implement file-based persistence using a `.maestro/` directory structure. This is what real projects will use.

## Deliverables
- `src/adapters/maestro.py` — MaestroAdapter implementing WorkflowBackend
- `tests/test_adapter.py` — Integration tests using pytest tmp_path

## Tasks
1. Implement directory structure creation (`.maestro/`, `.maestro/epics/`, `.maestro/sprints/`)
2. Implement `state.json` read/write for ProjectState
3. Implement epic markdown file creation and reading
4. Implement sprint markdown file creation and reading
5. Implement all 9 protocol methods with file I/O
6. Use `asyncio.to_thread` for sync file operations
7. Write integration tests using `tmp_path` fixture

## File Format
```
.maestro/
    state.json              # {"project_name": "...", "epics": [...], "sprints": [...]}
    epics/epic-01.md        # Markdown with YAML frontmatter
    sprints/sprint-01.md    # Markdown with YAML frontmatter
```

## Acceptance Criteria
- Creates `.maestro/` directory structure on first operation
- State persists across adapter instances (read back what was written)
- Sprint and epic markdown files are human-readable
- All tests pass with tmp_path (no side effects on real filesystem)

## Dependencies
- Sprint 1 (models and interface)
- Sprint 2 (can reference InMemoryAdapter patterns)
