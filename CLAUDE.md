# Maestro Agents — Development Guide

## Running Tests

Always use `uv run` to ensure tests run inside the project virtualenv with all
dependencies (including `claude-agent-sdk`):

```bash
# Standard run
uv run pytest tests/ -v

# Parallel (faster)
uv run pytest tests/ -v -n auto

# Including slow tests (real SDK calls)
uv run pytest tests/ -v -n auto --run-slow
```

**Never use bare `pytest`** — the system Python may lack required packages.

## Project Structure

- `src/` — main source (execution engine, agents, adapters, workflow models, kanban)
- `tests/` — pytest suite (asyncio_mode = auto)
- `kanban_tui/` — Textual-based kanban board TUI
- `Makefile` — common shortcuts (`make test`, `make test-fast`, `make test-all`)

## Slash Commands

Project-local commands live in `.claude/commands/`:

- `/epic-new <title>` — Create a new epic folder in `kanban/1-todo/` with `_epic.md`
- `/sprint-new <title> [--epic=N] [--type=TYPE]` — Create a new sprint dir + spec file
- `/create-spec <title> [--dir=PATH]` — Create a standalone spec document

All commands auto-number by scanning existing `kanban/` directories.

## Key Conventions

- `claude-agent-sdk` is a **required** dependency, not optional. Do not use
  `pytest.importorskip("claude_agent_sdk")` in tests.
- The sprint runner stops at **REVIEW** status (not DONE) for human review.
  Tests should expect `SprintStatus.REVIEW` after `runner.run()`.
- Kanban folders use the numbering: `0-backlog`, `1-todo`, `2-in-progress`,
  `3-review`, `4-done`, `5-blocked`, `6-abandoned`, `7-archived`.
