## API Contracts & Interfaces

### SprintInfo dataclass (kanban_tui/scanner.py)
- Add field: `history: list[dict] = field(default_factory=list)`
- Each dict: `{"column": str, "timestamp": str}`

### write_history_entry(md_path: Path, column: str) -> None
- Location: `kanban_tui/scanner.py`
- Reads YAML frontmatter via `yaml.safe_load`
- Appends `{"column": column, "timestamp": utc_iso_str}` to `fm["history"]`
- Removes `fm["status"]` if present
- Writes back with `yaml.dump`, preserving markdown body

### _parse_sprint_md (modified)
- Derive `status` from `_status_from_name(movable_path.name)` first
- Fallback: `fm.get("status", "unknown")`
- Read: `history=fm.get("history", [])`

### KanbanAdapter._write_history (src/adapters/kanban.py)
- Lazy import wrapper: `from kanban_tui.scanner import write_history_entry`
- Replaces `_update_yaml(path, status=...)` in 5 lifecycle methods

### app.py imports
- Add `write_history_entry` to scanner import block
- Call after `shutil.move()` in MoveScreen, complete fallback, reject fallback
