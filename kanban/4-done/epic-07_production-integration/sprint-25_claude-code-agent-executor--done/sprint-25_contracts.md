# API Contracts — Sprint 25: Claude Code Agent Executor

## Deliverables
- `src/agents/execution/claude_code.py` — ClaudeCodeExecutor
- Updated agent files wired to executor
- `tests/test_claude_code_executor.py` — SDK + mock tests

## Backend Contracts

### ClaudeCodeExecutor
- `ClaudeCodeExecutor(model="sonnet", permission_mode="acceptEdits", max_turns=25)`
- `async run(prompt, working_dir, timeout=300, allowed_tools=None) -> AgentResult`
- Uses `claude_agent_sdk.query()` internally
- Parses `AssistantMessage` (TextBlock, ToolUseBlock) and `ResultMessage`
- Tracks file operations: Write -> files_created, Edit -> files_modified

### Agent Wiring
- `ProductEngineerAgent(executor=None)` — optional executor injection
- `TestRunnerAgent(executor=None)` — optional executor injection
- `QualityEngineerAgent(executor=None)` — optional executor injection
- Without executor: returns `AgentResult(success=False, output="No ClaudeCodeExecutor")`
- With executor: delegates to `executor.run()` with agent-specific prompt

## Frontend Contracts
- N/A
