"""
Epic lifecycle operations.

Handles epic creation, starting, completion, archiving, and reset operations.
"""

import json
import re
from datetime import datetime

from ..exceptions import FileOperationError, ValidationError
from ..utils.file_ops import find_project_root, update_yaml_frontmatter


def create_epic(
    epic_num: int,
    title: str,
    dry_run: bool = False,
) -> dict:
    """
    Create epic folder structure and files.

    Creates:
    - docs/sprints/1-todo/epic-{NN}_{slug}/
    - docs/sprints/1-todo/epic-{NN}_{slug}/_epic.md

    Also registers in registry if not already registered.

    Args:
        epic_num: Epic number to create
        title: Epic title
        dry_run: If True, preview without creating

    Returns:
        Dict with created paths

    Example:
        >>> create_epic(99, "Test Workflow Validation")
        >>> # Creates: docs/sprints/1-todo/epic-99_test-workflow-validation/
    """
    project_root = find_project_root()

    # Create slug from title
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = slug.strip("-")

    # Epic folder path
    epic_dir = (
        project_root / "docs" / "sprints" / "1-todo" / f"epic-{epic_num:02d}_{slug}"
    )
    epic_file = epic_dir / "_epic.md"

    if dry_run:
        print(f"[DRY RUN] Would create epic {epic_num}:")
        print(f"  Folder: {epic_dir}")
        print(f"  File: {epic_file}")
        return {"epic_dir": str(epic_dir), "epic_file": str(epic_file)}

    # Create folder
    epic_dir.mkdir(parents=True, exist_ok=True)

    # Create _epic.md content
    today = datetime.now().strftime("%Y-%m-%d")
    epic_content = f"""---
epic: {epic_num}
title: "{title}"
status: planning
created: {today}
started: null
completed: null
---

# Epic {epic_num:02d}: {title}

## Overview

{{To be filled in - describe the strategic initiative}}

## Success Criteria

- [ ] {{Define measurable outcomes}}

## Sprints

| Sprint | Title | Status |
|--------|-------|--------|
| -- | TBD | planned |

## Backlog

- [ ] {{Add unassigned tasks}}

## Notes

Created: {today}
"""

    with open(epic_file, "w") as f:
        f.write(epic_content)

    # Register in registry if not already
    registry_path = project_root / "docs" / "sprints" / "registry.json"
    with open(registry_path) as f:
        registry = json.load(f)

    epic_key = str(epic_num)
    if epic_key not in registry.get("epics", {}):
        if "epics" not in registry:
            registry["epics"] = {}
        registry["epics"][epic_key] = {
            "title": title,
            "status": "planning",
            "created": today,
            "started": None,
            "completed": None,
            "totalSprints": 0,
            "completedSprints": 0,
        }
        # Update nextEpicNumber if needed
        if registry.get("nextEpicNumber", 1) <= epic_num:
            registry["nextEpicNumber"] = epic_num + 1

        with open(registry_path, "w") as f:
            json.dump(registry, f, indent=2)

    print(f"✓ Created epic {epic_num}: {title}")
    print(f"  Folder: {epic_dir.relative_to(project_root)}")

    return {"epic_dir": str(epic_dir), "epic_file": str(epic_file)}


def reset_epic(epic_num: int, dry_run: bool = False) -> dict:
    """
    Reset/delete an epic and all its sprints.

    Removes:
    - Epic folder and all contents from any status folder
    - Registry entries for epic and associated sprints
    - State files for associated sprints

    Args:
        epic_num: Epic number to reset
        dry_run: If True, preview without deleting

    Returns:
        Dict with deleted items

    Example:
        >>> reset_epic(99)
        >>> # Removes: epic-99_* folder, registry entries, state files
    """
    project_root = find_project_root()
    deleted = {"folders": [], "registry_entries": [], "state_files": []}

    print(f"{'='*60}")
    print(f"RESET EPIC {epic_num}")
    print(f"{'='*60}")

    # Find and remove epic folders from all status directories
    status_dirs = [
        "0-backlog",
        "1-todo",
        "2-in-progress",
        "3-done",
        "4-blocked",
        "5-abandoned",
        "6-archived",
    ]

    for status_dir in status_dirs:
        search_path = project_root / "docs" / "sprints" / status_dir
        if search_path.exists():
            for epic_folder in search_path.glob(f"epic-{epic_num:02d}_*"):
                if epic_folder.is_dir():
                    print(f"→ Found: {epic_folder.relative_to(project_root)}")
                    if not dry_run:
                        import shutil

                        shutil.rmtree(epic_folder)
                        print("  ✓ Deleted folder")
                    else:
                        print("  [DRY RUN] Would delete folder")
                    deleted["folders"].append(str(epic_folder))

    # Remove from registry
    registry_path = project_root / "docs" / "sprints" / "registry.json"
    if registry_path.exists():
        with open(registry_path) as f:
            registry = json.load(f)

        epic_key = str(epic_num)
        if epic_key in registry.get("epics", {}):
            print(f"→ Found in registry: epic {epic_num}")
            if not dry_run:
                del registry["epics"][epic_key]
                print("  ✓ Removed from registry")
            else:
                print("  [DRY RUN] Would remove from registry")
            deleted["registry_entries"].append(f"epic:{epic_num}")

        # Find and remove associated sprints from registry
        sprints_to_remove = []
        for sprint_key, sprint_data in registry.get("sprints", {}).items():
            if sprint_data.get("epic") == epic_num:
                sprints_to_remove.append(sprint_key)
                print(f"→ Found associated sprint {sprint_key} in registry")
                if not dry_run:
                    print("  ✓ Removed from registry")
                else:
                    print("  [DRY RUN] Would remove from registry")
                deleted["registry_entries"].append(f"sprint:{sprint_key}")

        if not dry_run:
            for sprint_key in sprints_to_remove:
                del registry["sprints"][sprint_key]

            with open(registry_path, "w") as f:
                json.dump(registry, f, indent=2)

    # Remove state files
    claude_dir = project_root / ".claude"
    if claude_dir.exists():
        # Check for epic-specific state files
        for state_file in claude_dir.glob(f"*epic*{epic_num}*"):
            print(f"→ Found state file: {state_file.name}")
            if not dry_run:
                state_file.unlink()
                print("  ✓ Deleted")
            else:
                print("  [DRY RUN] Would delete")
            deleted["state_files"].append(str(state_file))

        # Check for sprint state files (would need to know sprint numbers)
        # For test epic 99, we'll check sprint-99 pattern
        for state_file in claude_dir.glob(f"sprint-{epic_num}-state.json"):
            print(f"→ Found state file: {state_file.name}")
            if not dry_run:
                state_file.unlink()
                print("  ✓ Deleted")
            else:
                print("  [DRY RUN] Would delete")
            deleted["state_files"].append(str(state_file))

    print(f"{'='*60}")
    if dry_run:
        print(
            f"[DRY RUN] Would delete {len(deleted['folders'])} folders, {len(deleted['registry_entries'])} registry entries"
        )
    else:
        print(
            f"✓ Reset complete: {len(deleted['folders'])} folders, {len(deleted['registry_entries'])} registry entries"
        )
    print(f"{'='*60}")

    return deleted


def start_epic(epic_num: int, dry_run: bool = False) -> dict:
    """
    Start an epic: move from backlog/todo to in-progress, update YAML.

    Args:
        epic_num: Epic number to start
        dry_run: If True, preview changes without executing

    Returns:
        Dict with start summary

    Raises:
        FileOperationError: If epic folder not found
        ValidationError: If epic already started

    Example:
        >>> summary = start_epic(3)
        >>> print(summary['status'])  # 'started'
    """
    project_root = find_project_root()

    # Find epic in backlog or todo
    epic_folder = None
    epic_num_str = f"{epic_num:02d}"

    for folder in ["0-backlog", "1-todo"]:
        search_path = project_root / "docs" / "sprints" / folder
        if search_path.exists():
            found = list(search_path.glob(f"epic-{epic_num_str}_*"))
            if found and found[0].is_dir():
                epic_folder = found[0]
                break

    if not epic_folder:
        raise FileOperationError(
            f"Epic {epic_num} not found in backlog or todo folders"
        )

    # Find _epic.md file
    epic_file = epic_folder / "_epic.md"
    if not epic_file.exists():
        raise FileOperationError(f"Epic {epic_num} missing _epic.md file")

    # Read title from YAML
    with open(epic_file) as f:
        content = f.read()

    import re

    yaml_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not yaml_match:
        raise ValidationError(f"Epic {epic_num} missing YAML frontmatter")

    yaml_content = yaml_match.group(1)
    title_match = re.search(r"^title:\s*(.+)$", yaml_content, re.MULTILINE)
    title = title_match.group(1).strip().strip('"') if title_match else "Unknown"

    # Count sprints in epic
    sprint_files = list(epic_folder.glob("**/sprint-*.md"))
    sprint_count = len(sprint_files)

    if dry_run:
        print(f"[DRY RUN] Would start epic {epic_num}:")
        print(f"  Title: {title}")
        print(f"  Sprints: {sprint_count}")
        print("  1. Move to 2-in-progress/")
        print("  2. Update YAML (status=in-progress, started=<now>)")
        return {"status": "dry-run", "epic_num": epic_num}

    # Move to in-progress
    in_progress_dir = project_root / "docs" / "sprints" / "2-in-progress"
    in_progress_dir.mkdir(parents=True, exist_ok=True)

    new_epic_folder = in_progress_dir / epic_folder.name
    epic_folder.rename(new_epic_folder)

    # Update YAML frontmatter
    epic_file = new_epic_folder / "_epic.md"
    started_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    update_yaml_frontmatter(
        epic_file, {"status": "in-progress", "started": started_time}
    )

    summary = {
        "epic_num": epic_num,
        "title": title,
        "status": "started",
        "sprint_count": sprint_count,
        "new_path": str(new_epic_folder),
    }

    print(f"\n{'='*60}")
    print(f"Epic {epic_num}: {title} - STARTED")
    print(f"{'='*60}")
    print(f"Location: {new_epic_folder}")
    print(f"Sprints: {sprint_count}")
    print(f"{'='*60}")

    return summary


def complete_epic(epic_num: int, dry_run: bool = False) -> dict:
    """
    Complete an epic: verify all sprints done/aborted, move to done, calculate stats.

    Args:
        epic_num: Epic number to complete
        dry_run: If True, preview changes without executing

    Returns:
        Dict with completion summary

    Raises:
        FileOperationError: If epic folder not found
        ValidationError: If epic has unfinished sprints

    Example:
        >>> summary = complete_epic(3)
        >>> print(summary['total_hours'])  # 42.5
    """
    project_root = find_project_root()
    epic_num_str = f"{epic_num:02d}"

    # Find epic in in-progress
    in_progress_dir = project_root / "docs" / "sprints" / "2-in-progress"
    found = list(in_progress_dir.glob(f"epic-{epic_num_str}_*"))

    if not found or not found[0].is_dir():
        raise FileOperationError(f"Epic {epic_num} not found in in-progress folder")

    epic_folder = found[0]
    epic_file = epic_folder / "_epic.md"

    if not epic_file.exists():
        raise FileOperationError(f"Epic {epic_num} missing _epic.md file")

    # Read title from YAML
    with open(epic_file) as f:
        content = f.read()

    import re

    yaml_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not yaml_match:
        raise ValidationError(f"Epic {epic_num} missing YAML frontmatter")

    yaml_content = yaml_match.group(1)
    title_match = re.search(r"^title:\s*(.+)$", yaml_content, re.MULTILINE)
    title = title_match.group(1).strip().strip('"') if title_match else "Unknown"

    # Check all sprints are finished
    # Exclude postmortem files (they're metadata, not sprints)
    sprint_files = [
        f for f in epic_folder.glob("**/sprint-*.md") if "_postmortem" not in f.name
    ]
    done_sprints = []
    aborted_sprints = []
    unfinished_sprints = []
    blocked_sprints = []

    for sprint_file in sprint_files:
        name = sprint_file.name
        # Check both file name and parent directory for status suffix
        parent_name = sprint_file.parent.name
        if "--done" in name or "--done" in parent_name:
            done_sprints.append(name)
        elif "--aborted" in name or "--aborted" in parent_name:
            aborted_sprints.append(name)
        elif "--blocked" in name or "--blocked" in parent_name:
            blocked_sprints.append(name)
        else:
            unfinished_sprints.append(name)

    if unfinished_sprints or blocked_sprints:
        error_msg = f"Cannot complete epic {epic_num} - has unfinished sprints:\n"
        if unfinished_sprints:
            error_msg += "\nIn Progress/Pending:\n"
            for sprint in unfinished_sprints:
                error_msg += f"  - {sprint}\n"
        if blocked_sprints:
            error_msg += "\nBlocked:\n"
            for sprint in blocked_sprints:
                error_msg += f"  - {sprint}\n"
        raise ValidationError(error_msg.strip())

    # Calculate total hours
    total_hours = 0.0
    for sprint_file in sprint_files:
        with open(sprint_file) as f:
            sprint_content = f.read()
        yaml_match = re.search(r"^---\n(.*?)\n---", sprint_content, re.DOTALL)
        if yaml_match:
            hours_match = re.search(
                r"^hours:\s*([0-9.]+)", yaml_match.group(1), re.MULTILINE
            )
            if hours_match:
                total_hours += float(hours_match.group(1))

    if dry_run:
        print(f"[DRY RUN] Would complete epic {epic_num}:")
        print(f"  Title: {title}")
        print(f"  Done: {len(done_sprints)}")
        print(f"  Aborted: {len(aborted_sprints)}")
        print(f"  Total hours: {total_hours:.1f}")
        print("  1. Move to 3-done/")
        print("  2. Update YAML (status=done, completed=<now>, total_hours)")
        return {"status": "dry-run", "epic_num": epic_num}

    # Move to done
    done_dir = project_root / "docs" / "sprints" / "3-done"
    done_dir.mkdir(parents=True, exist_ok=True)

    new_epic_folder = done_dir / epic_folder.name
    epic_folder.rename(new_epic_folder)

    # Update YAML frontmatter
    epic_file = new_epic_folder / "_epic.md"
    completed_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    update_yaml_frontmatter(
        epic_file,
        {"status": "done", "completed": completed_time, "total_hours": total_hours},
    )

    summary = {
        "epic_num": epic_num,
        "title": title,
        "status": "done",
        "done_count": len(done_sprints),
        "aborted_count": len(aborted_sprints),
        "total_hours": total_hours,
        "new_path": str(new_epic_folder),
    }

    print(f"\n{'='*60}")
    print(f"Epic {epic_num}: {title} - COMPLETE")
    print(f"{'='*60}")
    print(f"Location: {new_epic_folder}")
    print(f"Sprints completed: {len(done_sprints)}")
    print(f"Sprints aborted: {len(aborted_sprints)}")
    print(f"Total hours: {total_hours:.1f}")
    print(f"{'='*60}")

    return summary


def archive_epic(epic_num: int, dry_run: bool = False) -> dict:
    """
    Archive an epic: move from done to archived, update YAML.

    Args:
        epic_num: Epic number to archive
        dry_run: If True, preview changes without executing

    Returns:
        Dict with archive summary

    Raises:
        FileOperationError: If epic folder not found in done
        ValidationError: If epic not yet complete

    Example:
        >>> summary = archive_epic(3)
        >>> print(summary['status'])  # 'archived'
    """
    project_root = find_project_root()
    epic_num_str = f"{epic_num:02d}"

    # Find epic in done
    done_dir = project_root / "docs" / "sprints" / "3-done"
    found = list(done_dir.glob(f"epic-{epic_num_str}_*"))

    if not found or not found[0].is_dir():
        raise FileOperationError(
            f"Epic {epic_num} not found in done folder. Complete it first with /epic-complete"
        )

    epic_folder = found[0]
    epic_file = epic_folder / "_epic.md"

    if not epic_file.exists():
        raise FileOperationError(f"Epic {epic_num} missing _epic.md file")

    # Read title from YAML
    with open(epic_file) as f:
        content = f.read()

    import re

    yaml_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not yaml_match:
        raise ValidationError(f"Epic {epic_num} missing YAML frontmatter")

    yaml_content = yaml_match.group(1)
    title_match = re.search(r"^title:\s*(.+)$", yaml_content, re.MULTILINE)
    title = title_match.group(1).strip().strip('"') if title_match else "Unknown"

    # Count sprint files
    sprint_files = list(epic_folder.glob("**/sprint-*.md"))
    file_count = len(sprint_files)

    if dry_run:
        print(f"[DRY RUN] Would archive epic {epic_num}:")
        print(f"  Title: {title}")
        print(f"  Files: {file_count} sprints + 1 epic")
        print("  1. Move to 6-archived/")
        print("  2. Update YAML (status=archived, archived_at=<now>)")
        return {"status": "dry-run", "epic_num": epic_num}

    # Move to archived
    archived_dir = project_root / "docs" / "sprints" / "6-archived"
    archived_dir.mkdir(parents=True, exist_ok=True)

    new_epic_folder = archived_dir / epic_folder.name
    epic_folder.rename(new_epic_folder)

    # Update YAML frontmatter
    epic_file = new_epic_folder / "_epic.md"
    archived_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    update_yaml_frontmatter(
        epic_file, {"status": "archived", "archived_at": archived_time}
    )

    summary = {
        "epic_num": epic_num,
        "title": title,
        "status": "archived",
        "file_count": file_count,
        "new_path": str(new_epic_folder),
    }

    print(f"\n{'='*60}")
    print(f"Epic {epic_num}: {title} - ARCHIVED")
    print(f"{'='*60}")
    print(f"Location: {new_epic_folder}")
    print(f"Files: {file_count} sprints + 1 epic")
    print(f"{'='*60}")

    return summary
