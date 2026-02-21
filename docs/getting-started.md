# Getting Started with Maestro Agents

Maestro Agents is a multi-agent sprint execution system. Install it once as a global tool, then use it in any project.

## Installation

### From Git

```bash
uv tool install git+https://github.com/dreadnought-foundry/maestro-agents.git
```

### From a local clone

```bash
git clone https://github.com/dreadnought-foundry/maestro-agents.git
cd maestro-agents
uv tool install .
```

### Verify

```bash
maestro --help
```

You should see:

```
usage: maestro [-h] {init,run,status,groom,board} ...

Maestro Agents — multi-agent sprint execution system

positional arguments:
  {init,run,status,groom,board}
    init                Initialize a new maestro project
    run                 Run a sprint
    status              Show sprint status
    groom               Run backlog grooming
    board               Launch the interactive kanban board
```

## Initialize a project

Navigate to your project and run:

```bash
cd your-project
maestro init
```

The init command walks you through setup:

1. **Kanban structure** — Creates `kanban/` with 8 column directories (backlog through archived), plus `deferred.md` and `postmortem.md`
2. **CLAUDE.md** (optional) — Asks if you want a workflow instructions file for Claude Code

The command is idempotent — running it again only creates missing items.

### Non-interactive mode

For scripting or CI:

```bash
maestro init --no-interactive
```

This uses all defaults and skips prompts.

## Kanban structure

After init, your project has:

```
kanban/
  0-backlog/       # Ideas and future work
  1-todo/          # Groomed and ready to start
  2-in-progress/   # Currently being worked on
  3-review/        # Awaiting human review
  4-done/          # Completed
  5-blocked/       # Waiting on external dependency
  6-abandoned/     # Cancelled work
  7-archived/      # Historical
  deferred.md      # Items deferred during sprints
  postmortem.md    # Sprint retrospectives
```

## Your first sprint

### 1. Create a sprint

Create a directory and markdown file in the backlog:

```bash
mkdir -p kanban/0-backlog/sprint-01_my-first-sprint
```

Create `kanban/0-backlog/sprint-01_my-first-sprint/sprint-01_my-first-sprint.md`:

```markdown
---
sprint: 1
title: "My First Sprint"
status: backlog
type: feature
created: 2026-02-21
---

# Sprint 01: My First Sprint

## Goal

Describe what this sprint should accomplish.

## Tasks

- [ ] Task 1
- [ ] Task 2

## Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2
```

### 2. View the board

```bash
maestro board
```

This launches an interactive terminal UI. Use arrow keys to navigate, `Enter` to expand epics, `d` to toggle the detail panel.

### 3. Groom the backlog

```bash
maestro groom
```

The grooming agent analyzes your backlog and proposes prioritization and sprint planning.

### 4. Run a sprint

Move your sprint to `1-todo/` (via the board's `m` key or manually), then:

```bash
maestro run sprint-1
```

Or press `s` on the sprint card in the board's Todo column.

The engine runs through phases automatically: Plan, TDD, Build, Validate. When done, the sprint appears in the Review column.

### 5. Review and complete

On the board, navigate to the Review column:
- Press `c` to complete the sprint (moves to Done, generates artifacts)
- Press `x` to reject with feedback (moves back to In Progress)

## Commands

| Command | Description |
|---------|-------------|
| `maestro init` | Scaffold kanban structure in current directory |
| `maestro board` | Launch interactive kanban TUI |
| `maestro run <id>` | Execute a sprint through all phases |
| `maestro status <id>` | Check sprint progress |
| `maestro groom` | Run AI-powered backlog grooming |

### Board keyboard shortcuts

| Key | Action | Context |
|-----|--------|---------|
| `s` | Start sprint | Todo column |
| `c` | Complete sprint | Review column |
| `x` | Reject sprint | Review column |
| `m` | Move card | Any column |
| Left/Right | Navigate columns | |
| Up/Down | Navigate cards | |
| Enter | Expand/collapse epic | |
| `d` | Toggle detail panel | |
| `a` | Show all columns | |
| `r` | Refresh board | |
| `?` | Show help | |
| `q` | Quit | |

## Upgrading

```bash
uv tool upgrade maestro-agents
```

Or to reinstall from git:

```bash
uv tool install --force git+https://github.com/dreadnought-foundry/maestro-agents.git
```

## Uninstalling

```bash
uv tool uninstall maestro-agents
```

This removes the CLI tool. Your project's `kanban/` directory and all sprint data remain untouched.
