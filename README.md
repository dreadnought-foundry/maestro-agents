# maestro-agents

Multi-agent sprint execution system built on [claude-agent-sdk](https://github.com/anthropics/claude-agent-sdk).

## What is this?

A team of specialized AI agents that execute software sprints autonomously:

- **Planning Agent** — reads the sprint spec and codebase, produces contracts and strategy
- **Product Engineer** — writes features and implementation code
- **Test Runner** — executes test suites and reports results
- **Quality Engineer** — reviews code for correctness, security, and standards
- **Validation Agent** — verifies against acceptance criteria

A **Sprint Runner** coordinates the agents through phases (Plan → TDD → Build → Validate → Review → Complete), using a kanban board for state management.

## Architecture

```
┌─────────────────────────────────────────────┐
│              Sprint Runner                   │
│   Plan → TDD → Build → Validate → Review    │
├──────────┬───────────┬──────────┬───────────┤
│ Planning │ Product   │  Test    │ Quality   │
│ Agent    │ Engineer  │  Runner  │ Engineer  │
└──────────┴───────────┴──────────┴───────────┘
        │                    │
   ClaudeCodeExecutor    KanbanAdapter
   (SDK sessions)        (filesystem state)
```

- **Execution engine** (`src/execution/`) — CLI + phase-based sprint runner
- **Agent registry** (`src/agents/execution/`) — agent definitions and tool configs
- **Kanban TUI** (`kanban_tui/`) — terminal UI for managing the sprint board

## Installation

```bash
# Install as a global CLI tool
uv tool install git+https://github.com/dreadnought-foundry/maestro-agents.git

# Or for development
git clone https://github.com/dreadnought-foundry/maestro-agents.git
cd maestro-agents
uv sync
```

## Quick start

```bash
# Initialize a project
cd your-project
maestro init

# View the kanban board
maestro board

# Run a sprint
maestro run <sprint_id>
```

## Running sprints

```bash
# Via CLI
make run-sprint SPRINT=42

# Via TUI
make kanban
```

## Kanban board

Sprints and epics live in `kanban/` organized by column:

```
kanban/
  0-backlog/
  1-todo/
  2-in-progress/
  3-review/
  4-done/
  5-blocked/
  6-abandoned/
  7-archived/
```

The interactive TUI (`maestro board`) lets you start, complete, and reject sprints directly from the board.

## Development

```bash
uv sync
make test          # run tests
make test-fast     # parallel execution
make test-all      # includes slow SDK integration tests
make kanban        # launch TUI locally
```

## Lineage

This project evolved from [claude-maestro](https://github.com/dreadnought-foundry/claude-maestro). Reference implementations from maestro are preserved in `docs/reference/maestro-v1/`.
