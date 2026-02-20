# API Contracts — Sprint 12: Agent Base Infrastructure

## Deliverables
- New src/agents/execution/ package
- tests/test_agent_infrastructure.py (10 tests)

## Backend Contracts
### Protocol
- `ExecutionAgent` — name: str, description: str, async execute(context: StepContext) -> AgentResult

### Dataclasses
- `StepContext` — step, sprint, epic, project_root, previous_outputs
- `AgentResult` — success, output, files_modified, files_created, test_results, coverage, review_verdict, deferred_items

### Registry
- `AgentRegistry.register(step_type: str, agent: ExecutionAgent) -> None`
- `AgentRegistry.get_agent(step_type: str) -> ExecutionAgent` — raises KeyError if unregistered
- `AgentRegistry.list_agents() -> dict[str, ExecutionAgent]`

## Frontend Contracts
- N/A
