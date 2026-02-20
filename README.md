# maestro-agents

Multi-agent sprint execution system built on [claude-agent-sdk](https://github.com/anthropics/claude-agent-sdk). Evolved from [claude-maestro](https://github.com/dreadnought-foundry/claude-maestro).

## What is this?

A team of specialized AI agents that execute software sprints autonomously:

- **Product Engineer** — writes features and implementation code
- **Test Runner** — executes test suites and reports results
- **Quality Engineer** — reviews code for correctness, security, and standards

An **Orchestrator** coordinates the agents through a sprint's phases (planning → implementation → validation), using the claude-agent-sdk to manage Claude Code sessions.

## Architecture

```
┌─────────────────────────────────────┐
│           Orchestrator              │
│     (claude-agent-sdk query())      │
├──────────┬───────────┬──────────────┤
│ Product  │   Test    │   Quality    │
│ Engineer │  Runner   │  Engineer    │
└──────────┴───────────┴──────────────┘
        │                    │
   ClaudeCodeExecutor   Sprint Lifecycle
   (SDK sessions)       (scripts/sprint_lifecycle.py)
```

- **Agents** use the SDK for reasoning tasks (writing code, running tests, reviewing)
- **Lifecycle script** handles mechanical bookkeeping (move files, update YAML, manage state) — zero tokens, instant execution

## Quick start

```bash
uv sync
make test          # 409+ tests, ~2s
make test-all      # includes slow SDK integration tests
```

## Kanban board

Sprints and epics live in `kanban/` organized by column:

```
kanban/
  0-backlog/
  1-todo/
  2-in-progress/
  3-done/
  4-blocked/
  5-abandoned/
  6-archived/
```

Lifecycle operations via CLI:
```bash
python3 scripts/sprint_lifecycle.py create-sprint 30 "My Feature" --epic 7
python3 scripts/sprint_lifecycle.py start-sprint 30
python3 scripts/sprint_lifecycle.py complete-sprint 30
```

## Lineage

This project evolved from [claude-maestro](https://github.com/dreadnought-foundry/claude-maestro), which provides global Claude configuration and workflow skills. maestro-agents diverged to build a multi-agent execution layer on top of the claude-agent-sdk, replacing the single-agent subprocess model with a coordinated team approach.

Reference implementations from maestro are preserved in `docs/reference/maestro-v1/`.
