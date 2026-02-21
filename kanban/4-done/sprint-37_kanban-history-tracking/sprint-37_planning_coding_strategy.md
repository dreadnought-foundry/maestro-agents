---
completed: 2026-02-21 20:12:10+00:00
history:
- column: 4-done
  timestamp: '2026-02-21T20:12:10Z'
---

## Coding Strategy & Patterns

### Module Placement

- `write_history_entry()` lives in `kanban_tui/scanner.py` — both TUI (app.py) and backend (kanban.py) already import from scanner, avoiding circular deps
- kanban.py uses a lazy import wrapper `_write_history()` to avoid circular import at module load time

### YAML Handling

- Use `yaml.safe_load` / `yaml.dump` for history writes (yaml is already a project dependency)
- Do NOT use the regex-based `_update_yaml` helper for history — it can't handle nested structures
- Keep `_update_yaml` for simple scalar fields (timestamps, rejection reasons)

### Status Derivation

- Path suffix (`--done`, `--blocked`) takes priority via `_status_from_name()`
- YAML `status:` field is the fallback for backward compatibility during migration
- `write_history_entry()` actively removes `status:` when writing — clean migration

### Error Handling

- `write_history_entry()` returns silently if no frontmatter found (no-op for non-YAML files)
- Existing `parse_frontmatter()` already handles OSError and YAMLError gracefully

### Naming

- Follow existing project patterns: snake_case functions, `_` prefix for internal helpers
- History entries use ISO 8601 UTC timestamps matching existing `_now_iso()` format
