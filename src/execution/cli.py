"""CLI entry point for sprint execution.

Usage: python -m src.execution run <sprint_id> [--project-root PATH]
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from src.adapters.memory import InMemoryAdapter
from src.execution.convenience import create_default_registry, run_sprint


def main() -> None:
    parser = argparse.ArgumentParser(description="Sprint execution CLI")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run a sprint")
    run_parser.add_argument("sprint_id", help="Sprint ID to execute")
    run_parser.add_argument("--project-root", default=".", help="Project root path")

    status_parser = subparsers.add_parser("status", help="Show sprint status")
    status_parser.add_argument("sprint_id", help="Sprint ID to check")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "run":
        asyncio.run(_run_command(args))
    elif args.command == "status":
        asyncio.run(_status_command(args))


async def _run_command(args) -> None:
    from pathlib import Path

    # For demo: use InMemoryAdapter with a sample sprint
    # In production, this would use MaestroAdapter
    backend = InMemoryAdapter(project_name="cli-project")

    def on_progress(status):
        completed = status["completed_steps"]
        total = status["total_steps"]
        pct = status["progress_pct"]
        print(f"  Progress: {completed}/{total} steps ({pct}%)")

    try:
        result = await run_sprint(
            args.sprint_id,
            backend=backend,
            project_root=Path(args.project_root),
            on_progress=on_progress,
        )
        print(f"\nSprint {result.sprint_id}: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Steps: {result.steps_completed}/{result.steps_total}")
        print(f"Duration: {result.duration_seconds:.2f}s")
        if result.deferred_items:
            print("Deferred items:")
            for item in result.deferred_items:
                print(f"  - {item}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


async def _status_command(args) -> None:
    backend = InMemoryAdapter()
    try:
        status = await backend.get_step_status(args.sprint_id)
        print(f"Sprint {args.sprint_id}")
        print(f"  Current step: {status['current_step']}")
        print(f"  Progress: {status['completed_steps']}/{status['total_steps']} ({status['progress_pct']}%)")
    except KeyError as e:
        print(f"Sprint not found: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
