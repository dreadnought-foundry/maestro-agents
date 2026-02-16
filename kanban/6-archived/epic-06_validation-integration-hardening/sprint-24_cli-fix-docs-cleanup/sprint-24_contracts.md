# API Contracts — Sprint 24: CLI Fix & Kanban Doc Cleanup

## Deliverables
- Updated `src/agents/definitions.py` with import guard
- `tests/test_cli.py` (5 tests)
- Updated kanban sprint-09 and sprint-10 docs with corrected enum names

## Backend Contracts
### Import Guard
- `src/agents/definitions.py` — claude_agent_sdk import wrapped in try/except; module remains importable without the SDK installed

### CLI Tests
- `test_cli_module_importable` — verifies CLI module imports without error
- `test_all_init_exports` — verifies all __init__.py exports are importable

### Documentation Fixes
- Sprint-09 doc: PENDING -> TODO, COMPLETED -> DONE
- Sprint-10 doc: PLANNED -> TODO, COMPLETED -> DONE

## Frontend Contracts
- N/A
