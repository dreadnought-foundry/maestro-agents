# API Contracts — Sprint 37: Kanban History Tracking

## Deliverables
- Modified `kanban_tui/scanner.py` — new field and utility function
- Modified `kanban_tui/app.py` — history recording in move flows
- Modified `src/adapters/kanban.py` — replaced status writes with history appends

## Backend Contracts

### SprintInfo (dataclass, modified)
- Added `history: list[dict] = field(default_factory=list)`
- Each history entry: `{"column": str, "timestamp": str}` (ISO 8601)

### write_history_entry(md_path: Path, column: str) -> None
- Reads YAML frontmatter from `md_path`
- Appends `{"column": column, "timestamp": now_utc_iso}` to `history` list
- Removes `status` field from frontmatter if present
- Writes updated YAML back to file preserving markdown body

### _parse_sprint_md (modified behavior)
- Status derived from path suffix via `_status_from_name()` first
- Falls back to `fm.get("status", "unknown")` for backward compat
- Reads `history` from frontmatter: `fm.get("history", [])`

### KanbanAdapter lifecycle methods (modified)
- `start_sprint()` — `_write_history(path, "2-in-progress")` replaces `status="in-progress"`
- `complete_sprint()` — `_write_history(path, "4-done")` replaces `status="done"`
- `move_to_review()` — `_write_history(path, "3-review")` replaces `status="review"`
- `reject_sprint()` — `_write_history(path, "2-in-progress")` replaces `status="in-progress"`
- `block_sprint()` — `_write_history(path, "5-blocked")` replaces `status="blocked"`

## Frontend Contracts
- N/A
