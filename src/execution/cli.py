"""CLI entry point for sprint execution and backlog grooming.

Usage:
  python -m src.execution run <sprint_id> [--project-root PATH] [--kanban-dir kanban]
  python -m src.execution status <sprint_id> [--kanban-dir kanban]
  python -m src.execution groom [--kanban-dir kanban] [--model sonnet] [--epic NUM]
"""

from __future__ import annotations

import argparse
import asyncio
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Sprint execution CLI")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run a sprint")
    run_parser.add_argument("sprint_id", help="Sprint ID to execute")
    run_parser.add_argument("--project-root", default=".", help="Project root path")
    run_parser.add_argument("--kanban-dir", default="kanban", help="Kanban directory")
    run_parser.add_argument("--mock", action="store_true", help="Use mock agents (skip real execution)")
    run_parser.add_argument("--model", default="sonnet", help="Claude model (default: sonnet)")

    status_parser = subparsers.add_parser("status", help="Show sprint status")
    status_parser.add_argument("sprint_id", help="Sprint ID to check")
    status_parser.add_argument("--kanban-dir", default="kanban", help="Kanban directory")

    groom_parser = subparsers.add_parser("groom", help="Run backlog grooming")
    groom_parser.add_argument("--kanban-dir", default="kanban", help="Kanban directory")
    groom_parser.add_argument("--model", default="sonnet", help="Model to use")
    groom_parser.add_argument("--epic", type=int, default=None, help="Epic number for mid-epic grooming")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "run":
        asyncio.run(_run_command(args))
    elif args.command == "status":
        asyncio.run(_status_command(args))
    elif args.command == "groom":
        asyncio.run(_groom_command(args))


async def _run_command(args) -> None:
    from pathlib import Path

    from src.execution.convenience import run_sprint

    kanban_dir = Path(args.kanban_dir)

    if args.mock:
        from src.adapters.memory import InMemoryAdapter
        backend = InMemoryAdapter(project_name="cli-project")
        kanban_path = None
    else:
        from src.adapters.kanban import KanbanAdapter
        if not kanban_dir.exists():
            print(f"Error: Kanban directory not found: {kanban_dir}", file=sys.stderr)
            print("Use --mock for testing without a kanban directory.", file=sys.stderr)
            sys.exit(1)
        backend = KanbanAdapter(kanban_dir)
        kanban_path = kanban_dir

    def on_progress(status):
        phase = status.get("current_phase", "")
        completed = status.get("phases_completed", status.get("completed_steps", 0))
        total = status.get("phases_total", status.get("total_steps", 0))
        if phase:
            print(f"  Phase: {phase.upper()} ({completed}/{total} phases complete)")
        else:
            pct = status.get("progress_pct", 0)
            print(f"  Progress: {completed}/{total} steps ({pct}%)")

    try:
        result = await run_sprint(
            args.sprint_id,
            backend=backend,
            project_root=Path(args.project_root),
            on_progress=on_progress,
            kanban_dir=kanban_path,
            mock=args.mock,
        )

        status = "SUCCESS" if result.success else "FAILED"
        if result.stopped_at_review:
            status = "IN REVIEW"

        print(f"\nSprint {result.sprint_id}: {status}")

        if result.phase_results:
            print(f"Phases: {len(result.phase_results)} completed")
            for pr in result.phase_results:
                icon = "PASS" if pr.success else "FAIL"
                print(f"  [{icon}] {pr.phase.value.upper()}")
        else:
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
    from pathlib import Path

    kanban_dir = Path(args.kanban_dir)
    if kanban_dir.exists():
        from src.adapters.kanban import KanbanAdapter
        backend = KanbanAdapter(kanban_dir)
    else:
        from src.adapters.memory import InMemoryAdapter
        backend = InMemoryAdapter()

    try:
        status = await backend.get_step_status(args.sprint_id)
        print(f"Sprint {args.sprint_id}")
        print(f"  Current step: {status['current_step']}")
        print(f"  Progress: {status['completed_steps']}/{status['total_steps']} ({status['progress_pct']}%)")
    except KeyError as e:
        print(f"Sprint not found: {e}", file=sys.stderr)
        sys.exit(1)


async def _groom_command(args) -> None:
    from pathlib import Path

    from src.execution.grooming import GroomingAgent

    kanban_dir = Path(args.kanban_dir)
    if not kanban_dir.exists():
        print(f"Kanban directory not found: {kanban_dir}", file=sys.stderr)
        sys.exit(1)

    agent = GroomingAgent(model=args.model)
    try:
        proposal = await agent.propose(kanban_dir, epic_num=args.epic)
        print(f"Grooming proposal written to: {proposal.proposal_path}")
        print(f"Board state: {proposal.board_state_summary}\n")
        print("--- Proposal Preview ---\n")
        lines = proposal.raw_markdown.split("\n")
        for line in lines[:50]:
            print(line)
        if len(lines) > 50:
            print(f"\n... ({len(lines) - 50} more lines in {proposal.proposal_path})")
    except Exception as e:
        print(f"Grooming failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
