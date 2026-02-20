---
sprint: 32
title: "PlanningAgent and Planning Artifacts"
type: backend
epic: 8
status: planning
created: 2026-02-20T19:59:05Z
started: null
completed: null
hours: null
---

# Sprint 32: PlanningAgent & Planning Artifacts

## Goal

Build a PlanningAgent that reads the sprint spec + codebase context and produces rich planning artifacts that guide the execution agents. This is the "tech lead" that writes the execution brief before handing work to the team.

## Problem

Currently agents start coding with only the sprint goal and step name as context. There's no upfront analysis of what interfaces need to be agreed on, how many agents should work, what to test, or what patterns to follow.

## Planning Artifacts

| Artifact | Purpose | Example |
|----------|---------|---------|
| **Contracts** | API shapes, interfaces, data models — the handshake between agents | `UserService.create_user(name, email) -> User` |
| **Team plan** | Agent composition, parallelism, execution order | "2 parallel backend engineers, then 1 test runner" |
| **TDD strategy** | What to test, structure, fixtures, coverage targets | "90% coverage, test public API first, use tmp_path" |
| **Coding strategy** | Patterns, naming, module structure | "Protocol-based interfaces, snake_case, DRY" |
| **Context brief** | Domain knowledge, existing patterns, gotchas from prior sprints | "SDK subprocess calls are slow (~6s), strip CLAUDECODE env var" |

## How It Works

1. PlanningAgent reads: sprint spec, project structure, key source files, prior postmortems/deferred items
2. PlanningAgent produces: 5 markdown artifact files written to sprint folder
3. Subsequent phases read these artifacts:
   - TDD phase reads TDD strategy + contracts
   - BUILD phase reads contracts + coding strategy + team plan
   - VALIDATE phase reads contracts + acceptance criteria

## Tasks

### Phase 1: Planning
- [ ] Design PlanningArtifacts dataclass
- [ ] Design PlanningAgent prompt — what codebase context does it need?
- [ ] Determine how planning artifacts are stored and passed to later phases

### Phase 2: Implementation
- [ ] Create `src/agents/execution/planning_agent.py` — PlanningAgent class
- [ ] Implement codebase analysis: scan project structure, read key files, identify patterns
- [ ] Implement prompt building: sprint spec + codebase context → planning prompt
- [ ] Implement artifact parsing: extract structured artifacts from agent output
- [ ] Create `src/execution/planning_artifacts.py` — PlanningArtifacts dataclass + file I/O
- [ ] Write planning artifacts to sprint folder
- [ ] Create MockPlanningAgent for testing
- [ ] Wire into PLAN phase of the phase-based runner
- [ ] Make planning artifacts available to subsequent phases via StepContext

### Phase 3: Validation
- [ ] Test PlanningAgent produces all 5 artifact types
- [ ] Test artifacts are written to sprint folder
- [ ] Test MockPlanningAgent works for fast testing
- [ ] Test planning artifacts flow through to BUILD phase agents
- [ ] Test PLAN phase gate: blocks if any artifact is empty/missing

## Deliverables

- `src/agents/execution/planning_agent.py` — PlanningAgent + MockPlanningAgent
- `src/execution/planning_artifacts.py` — PlanningArtifacts dataclass + I/O
- `tests/test_planning_agent.py` — full coverage

## Acceptance Criteria

- [ ] PlanningAgent reads sprint spec + codebase and produces 5 planning artifacts
- [ ] Artifacts are written to the sprint folder as markdown files
- [ ] BUILD phase agents receive planning artifacts in their context
- [ ] Contracts artifact defines interfaces that both frontend/backend agents reference
- [ ] Team plan artifact specifies agent composition and parallelism
- [ ] MockPlanningAgent available for fast testing

## Dependencies

- Sprint 31 (Phase-Based Runner — provides the PLAN phase)
