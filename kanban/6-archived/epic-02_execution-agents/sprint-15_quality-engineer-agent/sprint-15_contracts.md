# API Contracts — Sprint 15: Quality Engineer Agent

## Deliverables
- src/agents/execution/quality_engineer.py
- Updated mocks.py (MockQualityEngineerAgent)
- tests/test_quality_engineer.py (8 tests)

## Backend Contracts
### Agents
- `QualityEngineerAgent` — implements ExecutionAgent, uses Claude SDK with read-only tools: Read, Grep, Glob
- `MockQualityEngineerAgent` — returns configurable verdict for testing

### Behavior
- Receives previous_outputs from StepContext to review what was done
- Returns AgentResult.review_verdict: "approve" or "request_changes"
- Surfaces deferred_items for learning circle
- Read-only tool scoping prevents accidental code modification

## Frontend Contracts
- N/A
