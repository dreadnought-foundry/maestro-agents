---
sprint: 34
title: "Validation Phase"
type: backend
epic: 8
created: 2026-02-20T19:59:05Z
started: 2026-02-20T21:25:12Z
completed: 2026-02-20T21:38:31Z
hours: 0.2
---

# Sprint 34: Validation Phase

## Goal

Build a validation phase that goes beyond `pytest` — it spins up services, exercises UIs, hits API endpoints, and verifies the system actually works as a user would experience it.

## Problem

The current TestRunner only runs `pytest`. That catches unit-level bugs but doesn't verify:
- Does the UI render correctly?
- Do API endpoints return expected responses?
- Does the system start up without errors?
- Do components integrate correctly when running together?
- Does the output match the acceptance criteria from the sprint spec?

## What Validation Does

1. **Full test suite** — Run all tests (unit + integration), not just the TDD tests
2. **Service spin-up** — Start the application/service and verify it's healthy
3. **Endpoint verification** — Hit API endpoints and check responses against contracts
4. **UI verification** — Render UI components, take screenshots, verify layout
5. **Acceptance criteria check** — Compare what was built against sprint spec criteria
6. **Smoke test** — Exercise the happy path end-to-end

## Approach

Enhance TestRunner or create a ValidationAgent with expanded tools:
- `Bash` — starting services, running curl/httpie, taking screenshots
- `Read` — checking generated files, configs
- `WebFetch` — hitting HTTP endpoints

The validation prompt includes:
- Contracts from PLAN phase (expected API shapes)
- Acceptance criteria from sprint spec
- Instructions to spin up services, verify endpoints, check UI

## Tasks

### Phase 1: Planning
- [ ] Audit what types of validation are needed for this project's sprints
- [ ] Design validation report format
- [ ] Determine: extend TestRunner or new ValidationAgent?

### Phase 2: Implementation
- [ ] Create or extend validation agent with expanded tool access
- [ ] Implement service spin-up validation (start process, health check, stop)
- [ ] Implement endpoint verification (hit endpoints, check response against contracts)
- [ ] Implement acceptance criteria checking (compare output vs sprint spec)
- [ ] Create validation report generator (structured markdown with pass/fail per criterion)
- [ ] Wire into VALIDATE phase of the runner
- [ ] Implement validation gate: blocks if critical checks fail
- [ ] Create MockValidationAgent for testing
- [ ] Generate draft quality report when moving to Review

### Phase 3: Validation
- [ ] Test validation agent runs full test suite
- [ ] Test service spin-up and health check
- [ ] Test endpoint verification against contracts
- [ ] Test acceptance criteria comparison
- [ ] Test validation gate blocks on critical failure
- [ ] Test validation report is generated and written to sprint folder

## Deliverables

- Validation agent (new or enhanced TestRunner)
- `src/execution/validation.py` — validation report + gate logic
- `tests/test_validation.py` — full coverage
- Draft quality report generated when entering Review

## Acceptance Criteria

- [ ] Validation phase runs the full test suite
- [ ] Validation can spin up a service and verify it's healthy
- [ ] Validation checks API responses against contracts from PLAN phase
- [ ] Validation report shows pass/fail per acceptance criterion
- [ ] Critical failures block the sprint from reaching Review
- [ ] Draft quality report is available for human reviewer

## Dependencies

- Sprint 31 (Phase-Based Runner — provides VALIDATE phase)
- Sprint 33 (Parallel Execution — validation may run concurrent checks)
