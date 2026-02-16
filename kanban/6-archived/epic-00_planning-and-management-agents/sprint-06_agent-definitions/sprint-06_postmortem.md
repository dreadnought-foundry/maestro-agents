# Postmortem — Sprint 06: Agent Definitions

**Result**: Success | 5/5 steps | 1m
**Date**: 2026-02-15

## What Was Built
- 4 AgentDefinition instances: epic_breakdown, sprint_spec, research, status_report
- TOOL_PREFIX and WORKFLOW_TOOLS shared constants
- Each agent has description, prompt, tools list, and model selection
- Tool lists reference MCP tool names with correct prefix

## Lessons Learned
- Scoping tool access per agent (read-only for research, full access for breakdown) improves safety
- Domain-agnostic prompts (not coding-specific) make agents reusable across project types

## Deferred Items
- Production SDK integration
- Agent prompt tuning
- Per-project configuration overrides
