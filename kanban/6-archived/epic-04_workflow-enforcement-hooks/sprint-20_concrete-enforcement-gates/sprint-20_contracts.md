# API Contracts — Sprint 20: Concrete Enforcement Gates

## Deliverables
- src/execution/gates.py
- tests/test_gates.py (15 tests)

## Backend Contracts
### Gates (all implement Hook protocol)
- `CoverageGate` — POST_STEP hook, checks AgentResult.coverage >= threshold
- `QualityReviewGate` — PRE_COMPLETION hook, checks review_verdict == "approve"
- `StepOrderingEnforcement` — PRE_STEP hook, validates step dependencies
- `RequiredStepsGate` — PRE_COMPLETION hook, validates all required steps are done

### Factory
- `create_default_hooks(sprint_type) -> list[Hook]` — returns sensible preset hooks

### Coverage Thresholds
- fullstack: 75%
- backend: 85%
- frontend: 70%
- research: 0%
- infrastructure: 60%

## Frontend Contracts
- N/A
