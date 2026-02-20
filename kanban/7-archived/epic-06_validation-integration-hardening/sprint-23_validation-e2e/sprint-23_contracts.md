# API Contracts — Sprint 23: Validation E2E

## Deliverables
- `tests/test_validation_e2e.py` (10 tests)

## Backend Contracts
### E2E Test Coverage
- `test_multi_type_sprint_with_hooks` — implement/test/review through runner with hooks
- `test_coverage_gate_blocks` — coverage gate blocks low-coverage sprint via runner
- `test_quality_review_gate_blocks` — quality review gate blocks unapproved sprint
- `test_12_step_sprint` — sprint with 12 steps completes correctly
- `test_empty_sprint` — empty sprint completes immediately
- `test_deferred_items_collected` — deferred items collected across mixed agent types
- `test_create_default_registry` — handles all standard step types
- `test_previous_outputs_accumulate` — previous outputs accumulate across steps
- `test_full_lifecycle` — epic -> sprint -> run -> DONE
- `test_default_hooks_happy_path` — all default hooks with approve verdict

## Frontend Contracts
- N/A
