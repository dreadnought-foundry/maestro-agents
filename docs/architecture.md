# Maestro v2 POC — Architecture

## Problem

Maestro v1 is a sprint workflow system built before the Claude Agent SDK existed. It uses markdown agent definitions, slash commands, Python scripts, and hooks — a CLI configuration system that works around Claude Code rather than with it.

The Agent SDK provides native support for what maestro built manually: agent definitions, tool scoping, multi-agent orchestration, and custom tools via MCP. This POC prototypes maestro v2 using these primitives.

## Goal

Build a universal, domain-agnostic project workflow system powered by SDK agents. Four planning/management agents that work on any project type — coding, marketing, research, design, devops, business analysis.

## System Architecture

```
User request
    │
    ▼
┌─────────────────────────────────────────────────┐
│  Orchestrator Agent                              │
│  Analyzes request, delegates to specialist       │
│  Tools: Task (to spawn subagents)                │
└─────────┬───────────┬──────────┬────────────────┘
          │           │          │
    ┌─────▼───┐ ┌─────▼───┐ ┌───▼─────┐ ┌──────────┐
    │ Epic    │ │ Sprint  │ │Research │ │ Status   │
    │Breakdown│ │ Spec    │ │ Agent   │ │ Report   │
    │ Agent   │ │ Agent   │ │         │ │ Agent    │
    └─────┬───┘ └─────┬───┘ └───┬─────┘ └────┬─────┘
          │           │          │             │
          ▼           ▼          ▼             ▼
    ┌─────────────────────────────────────────────┐
    │  MCP Tools (custom tool layer)               │
    │  get_project_status, list_epics, get_epic,   │
    │  list_sprints, get_sprint, create_epic,      │
    │  create_sprint                               │
    └──────────────────┬──────────────────────────┘
                       │
    ┌──────────────────▼──────────────────────────┐
    │  Tool Handlers (pure Python functions)        │
    │  No SDK dependency — testable independently   │
    └──────────────────┬──────────────────────────┘
                       │
    ┌──────────────────▼──────────────────────────┐
    │  WorkflowBackend Protocol                     │
    │  Abstract interface for project operations    │
    └──────┬───────────────────┬──────────────────┘
           │                   │
    ┌──────▼──────┐     ┌──────▼──────┐
    │ Maestro     │     │ InMemory    │
    │ Adapter     │     │ Adapter     │
    │ (files)     │     │ (tests)     │
    └─────────────┘     └─────────────┘
```

## Layer Descriptions

### Layer 1: Workflow Interface (`src/workflow/`)

Domain models and the abstract protocol that any backend must implement.

**Models** — Plain dataclasses with no business logic:
- `Sprint` — id, goal, status, epic_id, tasks, dependencies, deliverables
- `Epic` — id, title, description, status, sprint_ids
- `ProjectState` — project_name, epics, sprints, active_sprint_id
- `SprintStatus` / `EpicStatus` — enums for lifecycle states

**Protocol** — `WorkflowBackend` defines 9 operations:
- Read: `get_project_state`, `get_epic`, `get_sprint`, `list_epics`, `list_sprints`, `get_status_summary`
- Write: `create_epic`, `create_sprint`, `update_sprint`

This is the abstraction boundary. The protocol is deliberately small — only plan/manage operations for this POC. Sprint execution (start, advance, complete) is phase 2.

### Layer 2: Adapters (`src/adapters/`)

Concrete implementations of `WorkflowBackend`.

**MaestroAdapter** — File-based storage:
```
{project_root}/.maestro/
    state.json           # ProjectState as JSON
    epics/{epic_id}.md   # Epic descriptions as markdown
    sprints/{sprint_id}.md  # Sprint specs as markdown
```

**InMemoryAdapter** — Dict-based storage for tests. Same interface, no file I/O.

### Layer 3: MCP Tools (`src/tools/`)

Two-part design following the pattern from Example 2:

**Handlers** (`handlers.py`) — Pure async functions that take `(args, backend)` and return MCP result format. No SDK dependency. Fully testable with InMemoryAdapter.

**Server Factory** (`server.py`) — `create_workflow_server(backend)` binds handlers to `@tool` decorators and creates an MCP server. Closures capture the backend instance.

### Layer 4: Agents (`src/agents/`)

**Agent Definitions** (`definitions.py`) — Four `AgentDefinition` instances:

| Agent | Purpose | Key Tools | Model |
|-------|---------|-----------|-------|
| `epic_breakdown` | Break big ideas into epics + sprints | All workflow tools + Read | sonnet |
| `sprint_spec` | Write detailed sprint specifications | All workflow tools | sonnet |
| `research` | Market/technical research | WebSearch, WebFetch, Read | sonnet |
| `status_report` | Progress reports across epics | All workflow tools | sonnet |

**Orchestrator** (`orchestrator.py`) — Entry point. Sets up backend, creates MCP server, registers agents, runs the query loop.

## Key Design Decisions

### Protocol over ABC
Structural subtyping — adapters just need the right methods, no inheritance. More Pythonic, less coupling.

### Handler/tool separation
Handlers are pure functions testable without the SDK. The `@tool` decorator wraps functions in `SdkMcpTool` objects that aren't directly callable — separating logic from registration makes everything testable.

### Backend injection via closures
Handlers take `backend` as a parameter. The server factory closes over a specific backend instance when creating tool wrappers. Tests inject InMemoryAdapter; production injects MaestroAdapter.

### Domain-agnostic models
Sprint/Epic models have a `metadata: dict` field for domain-specific data. The core models don't know about "fullstack" vs "research" vs "marketing" — that's metadata.

### Sonnet for subagents
Cost-effective for focused, well-scoped tasks. The orchestrator uses the default model. Research agent could be upgraded to opus for complex analysis if needed.

## File Map

```
src/
    __init__.py
    workflow/
        __init__.py
        models.py              # Dataclasses + enums
        interface.py           # WorkflowBackend protocol
    adapters/
        __init__.py
        memory.py              # InMemoryAdapter
        maestro.py             # MaestroAdapter (file-based)
    tools/
        __init__.py            # Re-exports create_workflow_server
        handlers.py            # 7 pure handler functions
        server.py              # MCP server factory
    agents/
        __init__.py
        definitions.py         # 4 AgentDefinition instances
        orchestrator.py        # run_orchestrator() entry point
tests/
    __init__.py
    test_models.py
    test_handlers.py           # Core logic tests
    test_adapter.py            # File I/O tests
docs/
    architecture.md            # This file
    sprints/                   # Sprint specs for building this POC
```

## Future: Phase 2 — Sprint Execution

Not in scope for this POC, but the architecture supports it:
- Add `start_sprint`, `advance_sprint`, `complete_sprint` to the protocol
- Add execution agents (product-engineer, test-runner, etc.)
- Add hooks for workflow enforcement
- Add state machine transitions to the adapter
