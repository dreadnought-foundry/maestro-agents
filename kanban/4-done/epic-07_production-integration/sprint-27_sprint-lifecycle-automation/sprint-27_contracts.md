# API Contracts — Sprint 27: Sprint Lifecycle Automation

## Deliverables
- `scripts/sprint_lifecycle.py` — complete CLI for sprint and epic lifecycle management

## CLI Commands

### Sprint Commands
- `create-sprint <num> <title> [--type TYPE] [--epic NUM]` — creates sprint folder + file in backlog or epic
- `start-sprint <num>` — moves to 2-in-progress, sets YAML status, creates state file
- `complete-sprint <num>` — adds --done suffix, updates YAML with completion timestamp and hours
- `block-sprint <num> <reason>` — adds --blocked suffix, records blocker reason
- `resume-sprint <num>` — removes --blocked suffix, resumes in-progress
- `abort-sprint <num> [reason]` — adds --aborted suffix

### Epic Commands
- `create-epic <num> <title>` — creates epic folder with _epic.md in 1-todo
- `start-epic <num>` — moves entire epic folder to 2-in-progress
- `complete-epic <num>` — moves to 3-done (requires all sprints done/aborted)
- `archive-epic <num>` — moves to 6-archived

### Internal Helpers
- `find_sprint(num)` — locates sprint file across all columns
- `find_epic(num)` — locates epic folder across all columns
- `read_yaml(path)` / `update_yaml(path, **fields)` — YAML frontmatter management
- `move_to_column(path, target_col)` — moves files/folders between kanban columns
- `add_suffix(path, suffix)` / `remove_suffix(path, suffix)` — manage --done/--blocked suffixes

## Frontend Contracts
- N/A
