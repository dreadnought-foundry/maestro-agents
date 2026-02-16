.PHONY: claude example1 example2 example3 run test run-sprint kanban lint

# Start Claude Code with permissions bypass
claude:
	@echo "Starting Claude Code with permissions bypass..."
	claude --dangerously-skip-permissions

# Run examples
example1:
	uv run python examples/01_simple_query.py

example2:
	uv run python examples/02_custom_tools.py

example3:
	uv run python examples/03_multi_agent.py

# Maestro orchestrator
run:
	uv run python -m src.agents.orchestrator $(ARGS)

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

lint:
	uv run python -m py_compile examples/01_simple_query.py
	uv run python -m py_compile examples/02_custom_tools.py
	uv run python -m py_compile examples/03_multi_agent.py
	@echo "All files compile OK"
