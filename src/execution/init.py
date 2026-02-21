"""Project scaffolding for maestro init."""

from __future__ import annotations

from pathlib import Path

KANBAN_COLUMNS = [
    "0-backlog",
    "1-todo",
    "2-in-progress",
    "3-review",
    "4-done",
    "5-blocked",
    "6-abandoned",
    "7-archived",
]

DEFERRED_TEMPLATE = """\
# Deferred Items

Items identified during sprints that are out of scope for the current epic.

## Uncategorized

"""

POSTMORTEM_TEMPLATE = """\
# Sprint Postmortems

## Timeline

"""

CLAUDE_MD_TEMPLATE = """\
# Maestro Workflow

This project uses [maestro-agents](https://github.com/dreadnought-foundry/maestro-agents) for sprint execution.

## Commands

- `maestro board` — interactive kanban TUI
- `maestro run <sprint_id>` — execute a sprint
- `maestro status <sprint_id>` — check sprint progress
- `maestro groom` — run backlog grooming

## Kanban Columns

| Column | Purpose |
|--------|---------|
| 0-backlog | Ideas and future work |
| 1-todo | Groomed and ready to start |
| 2-in-progress | Currently being worked on |
| 3-review | Awaiting human review |
| 4-done | Completed |
| 5-blocked | Waiting on external dependency |
| 6-abandoned | Cancelled work |
| 7-archived | Historical |

## Board Actions

| Key | Action | Column |
|-----|--------|--------|
| s | Start sprint | Todo |
| c | Complete sprint | Review |
| x | Reject sprint | Review |
| m | Move card | Any |
"""


def scaffold_project(
    root: Path,
    kanban_dir_name: str = "kanban",
    create_claude_md: bool = False,
    interactive: bool = True,
) -> list[str]:
    """Create the kanban directory structure and support files.

    Returns a list of created paths (for user feedback).
    """
    created: list[str] = []
    kanban_dir = root / kanban_dir_name

    if kanban_dir.exists():
        existing_cols = [d for d in kanban_dir.iterdir() if d.is_dir()]
        if existing_cols:
            print(f"\n  {kanban_dir} already exists with {len(existing_cols)} directories.")
            if interactive:
                response = input("  Continue and fill in missing structure? [Y/n] ")
                if response.strip().lower() == "n":
                    return created

    for col in KANBAN_COLUMNS:
        col_path = kanban_dir / col
        if not col_path.exists():
            col_path.mkdir(parents=True)
            created.append(str(col_path.relative_to(root)))

    deferred_path = kanban_dir / "deferred.md"
    if not deferred_path.exists():
        deferred_path.write_text(DEFERRED_TEMPLATE)
        created.append(str(deferred_path.relative_to(root)))

    postmortem_path = kanban_dir / "postmortem.md"
    if not postmortem_path.exists():
        postmortem_path.write_text(POSTMORTEM_TEMPLATE)
        created.append(str(postmortem_path.relative_to(root)))

    if create_claude_md:
        claude_md_path = root / "CLAUDE.md"
        if not claude_md_path.exists():
            claude_md_path.write_text(CLAUDE_MD_TEMPLATE)
            created.append("CLAUDE.md")
        else:
            print("  CLAUDE.md already exists, skipping.")

    return created
