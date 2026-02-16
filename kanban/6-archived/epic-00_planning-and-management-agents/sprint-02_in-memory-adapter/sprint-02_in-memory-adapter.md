# Sprint 2: In-Memory Adapter

## Goal
Implement a test-friendly backend that stores everything in dictionaries. This unlocks testing for all layers above it.

## Deliverables
- `src/adapters/__init__.py`
- `src/adapters/memory.py` — InMemoryAdapter implementing WorkflowBackend

## Tasks
1. Create `src/adapters/__init__.py`
2. Implement `InMemoryAdapter` with dict-based storage
3. Implement all 9 protocol methods (get/list/create/update)
4. Auto-generate IDs for new epics and sprints
5. Implement `get_status_summary` returning counts and progress percentage

## Acceptance Criteria
- `InMemoryAdapter` satisfies the `WorkflowBackend` protocol
- Can create epics, create sprints within epics, list and retrieve them
- Status summary returns accurate counts
- No file I/O — purely in-memory

## Dependencies
- Sprint 1 (models and interface)
