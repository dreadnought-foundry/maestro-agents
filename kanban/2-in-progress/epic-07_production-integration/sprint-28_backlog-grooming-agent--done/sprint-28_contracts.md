# API Contracts — Sprint 28: Backlog Grooming Agent

## Deliverables
- `src/execution/grooming.py` — GroomingAgent, GroomingProposal, MockGroomingAgent
- `src/execution/grooming_hook.py` — GroomingHook
- `tests/test_grooming.py` — 21 tests

## Backend Contracts

### GroomingAgent
- `GroomingAgent(model="sonnet")` — uses claude --print subprocess
- `async propose(kanban_dir, epic_num=None) -> GroomingProposal`
- Two modes: full (epic_num=None) proposes next epic, mid-epic (epic_num=N) proposes additional sprints

### GroomingProposal
- `GroomingProposal(proposal_text: str, source_epic: int | None, proposed_items: list[str])`

### MockGroomingAgent
- `MockGroomingAgent(proposal=None)` — configurable test double
- Tracks `call_count` and `last_kanban_dir`

### GroomingHook
- `GroomingHook(kanban_dir, grooming_agent=None)`
- `hook_point = HookPoint.POST_COMPLETION`
- `blocking = False`
- `async evaluate(context) -> HookResult`
- Parses epic number from sprint's epic_id, checks if epic is complete, calls grooming agent

### Updated: create_default_hooks()
- `create_default_hooks(sprint_type="backend", kanban_dir=None, grooming_agent=None)`
- When kanban_dir is provided, adds GroomingHook to the hook list

### Updated: run_sprint()
- Now accepts `kanban_dir`, `synthesizer`, `grooming_agent` keyword arguments

## Frontend Contracts
- N/A
