# API Contracts — Sprint 13: Product Engineer Agent

## Deliverables
- src/agents/execution/product_engineer.py
- src/agents/execution/mocks.py (MockProductEngineerAgent)
- tests/test_product_engineer.py (8 tests)

## Backend Contracts
### Agents
- `ProductEngineerAgent` — implements ExecutionAgent, uses Claude SDK with tools: Read, Write, Edit, Glob, Grep, Bash
- `MockProductEngineerAgent` — returns canned AgentResult for testing

### Behavior
- Receives StepContext describing what code to write
- Follows TDD approach: writes tests first, then implementation
- Returns AgentResult with files_modified and files_created populated

## Frontend Contracts
- N/A
