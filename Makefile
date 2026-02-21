.PHONY: claude test test-fast test-all run-sprint kanban

# Start Claude Code with permissions bypass
claude:
	@echo "Starting Claude Code with permissions bypass..."
	claude --dangerously-skip-permissions

# Dev
test:
	uv run pytest tests/ -v

test-fast:
	uv run pytest tests/ -v -n auto

test-all:
	uv run pytest tests/ -v -n auto --run-slow

run-sprint:
	uv run python -m src.execution run $(SPRINT) --project-root .

kanban:
	uv run python -m kanban_tui
