# Sprint 6: Agent Definitions

## Goal
Define the four specialized agents as AgentDefinition instances with carefully crafted prompts, tool scoping, and model selection.

## Deliverables
- `src/agents/definitions.py` — 4 AgentDefinition instances + shared constants

## Tasks
1. Define `TOOL_PREFIX` and `WORKFLOW_TOOLS` constants
2. Define `epic_breakdown_agent` — breaks big ideas into epics and sprints
3. Define `sprint_spec_agent` — writes detailed sprint specifications
4. Define `research_agent` — conducts market/technical research
5. Define `status_report_agent` — generates progress reports

## Agent Specifications

### epic_breakdown_agent
- **Tools:** All workflow tools + Read (for project file context)
- **Model:** sonnet
- **Prompt focus:** Dependency ordering, task specificity, both technical and non-technical work

### sprint_spec_agent
- **Tools:** All workflow tools
- **Model:** sonnet
- **Prompt focus:** Acceptance criteria, task breakdown, actionable specs anyone can execute

### research_agent
- **Tools:** get_project_status + WebSearch + WebFetch + Read
- **Model:** sonnet
- **Prompt focus:** Structured deliverables, source citation, objectivity

### status_report_agent
- **Tools:** All workflow tools
- **Model:** sonnet
- **Prompt focus:** Honesty about problems, quantification, actionable next steps

## Acceptance Criteria
- All 4 agents importable from definitions.py
- Each agent has description, prompt, tools, and model set
- Tool lists correctly reference MCP tool names with prefix
- Prompts are clear and domain-agnostic (not coding-specific)

## Dependencies
- Sprint 5 (need to know exact tool names for allowed_tools lists)
