"""
Sprint lifecycle operations.

Handles sprint creation, starting, aborting, blocking, resuming,
and recovery operations.
"""

import json
import re
import shutil
from datetime import datetime
from typing import Optional

from ..exceptions import FileOperationError, ValidationError
from ..registry.manager import update_registry
from ..utils.file_ops import (
    update_yaml_frontmatter,
    find_project_root,
)
from ..utils.project import find_sprint_file, is_epic_sprint


def create_sprint(
    sprint_num: int,
    title: str,
    sprint_type: str = "fullstack",
    epic: Optional[int] = None,
    dry_run: bool = False,
) -> dict:
    """
    Create sprint folder structure and files.

    Creates:
    - For epic sprints: docs/sprints/{status}/epic-{NN}_{slug}/sprint-{NN}_{slug}/sprint-{NN}_{slug}.md
    - For standalone: docs/sprints/{status}/sprint-{NN}_{slug}/sprint-{NN}_{slug}.md

    Also registers in registry if not already registered.

    Args:
        sprint_num: Sprint number to create
        title: Sprint title
        sprint_type: One of: fullstack, backend, frontend, research, spike, infrastructure
        epic: Optional epic number this sprint belongs to
        dry_run: If True, preview without creating

    Returns:
        Dict with created paths

    Example:
        >>> create_sprint(100, "Test Feature", sprint_type="fullstack", epic=99)
    """
    project_root = find_project_root()

    # Create slug from title
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = slug.strip("-")

    today = datetime.now().strftime("%Y-%m-%d")
    today_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    # Determine folder path based on epic
    if epic:
        # Find epic folder
        epic_folder = None
        for status_dir in ["0-backlog", "1-todo", "2-in-progress"]:
            search_path = project_root / "docs" / "sprints" / status_dir
            if search_path.exists():
                for folder in search_path.glob(f"epic-{epic:02d}_*"):
                    if folder.is_dir():
                        epic_folder = folder
                        break
            if epic_folder:
                break

        if not epic_folder:
            raise ValidationError(
                f"Epic {epic} folder not found. Create it first with create-epic."
            )

        sprint_dir = epic_folder / f"sprint-{sprint_num:02d}_{slug}"
    else:
        # Standalone sprint in backlog
        sprint_dir = (
            project_root
            / "docs"
            / "sprints"
            / "0-backlog"
            / f"sprint-{sprint_num:02d}_{slug}"
        )

    sprint_file = sprint_dir / f"sprint-{sprint_num:02d}_{slug}.md"

    if dry_run:
        print(f"[DRY RUN] Would create sprint {sprint_num}:")
        print(f"  Title: {title}")
        print(f"  Type: {sprint_type}")
        print(f"  Epic: {epic or 'None (standalone)'}")
        print(f"  Folder: {sprint_dir.relative_to(project_root)}")
        print(f"  File: {sprint_file.name}")
        return {"sprint_dir": str(sprint_dir), "sprint_file": str(sprint_file)}

    # Create folder
    sprint_dir.mkdir(parents=True, exist_ok=True)

    # Create sprint file content
    sprint_content = f"""---
sprint: {sprint_num}
title: "{title}"
type: {sprint_type}
epic: {epic if epic else 'null'}
status: planning
created: {today_iso}
started: null
completed: null
hours: null
workflow_version: "3.1.0"
---

# Sprint {sprint_num}: {title}

## Overview

| Field | Value |
|-------|-------|
| Sprint | {sprint_num} |
| Title | {title} |
| Type | {sprint_type} |
| Epic | {epic if epic else 'None'} |
| Status | Planning |
| Created | {today} |
| Started | - |
| Completed | - |

## Goal

{{One sentence describing what this sprint accomplishes}}

## Background

{{Why is this needed? What problem does it solve?}}

## Requirements

### Functional Requirements

- [ ] {{Requirement 1}}
- [ ] {{Requirement 2}}

### Non-Functional Requirements

- [ ] {{Performance, security, or other constraints}}

## Dependencies

- **Sprints**: None
- **External**: None

## Scope

### In Scope

- {{What's included}}

### Out of Scope

- {{What's explicitly NOT included}}

## Technical Approach

{{High-level description of how this will be implemented}}

## Tasks

### Phase 1: Planning
- [ ] Review requirements
- [ ] Design architecture
- [ ] Clarify requirements

### Phase 2: Implementation
- [ ] Write tests
- [ ] Implement feature
- [ ] Fix test failures

### Phase 3: Validation
- [ ] Quality review
- [ ] Refactoring

### Phase 4: Documentation
- [ ] Update docs

## Acceptance Criteria

- [ ] All tests passing
- [ ] Code reviewed

## Notes

Created: {today}
"""

    with open(sprint_file, "w") as f:
        f.write(sprint_content)

    # Register in registry
    registry_path = project_root / "docs" / "sprints" / "registry.json"
    with open(registry_path) as f:
        registry = json.load(f)

    sprint_key = str(sprint_num)
    if sprint_key not in registry.get("sprints", {}):
        if "sprints" not in registry:
            registry["sprints"] = {}
        registry["sprints"][sprint_key] = {
            "title": title,
            "status": "planning",
            "epic": epic,
            "type": sprint_type,
            "created": today,
            "started": None,
            "completed": None,
            "hours": None,
        }
        # Update nextSprintNumber if needed
        if registry.get("nextSprintNumber", 1) <= sprint_num:
            registry["nextSprintNumber"] = sprint_num + 1

        with open(registry_path, "w") as f:
            json.dump(registry, f, indent=2)

    # Update epic's totalSprints count
    if epic:
        epic_key = str(epic)
        if epic_key in registry.get("epics", {}):
            registry["epics"][epic_key]["totalSprints"] = (
                registry["epics"][epic_key].get("totalSprints", 0) + 1
            )
            with open(registry_path, "w") as f:
                json.dump(registry, f, indent=2)

    print(f"✓ Created sprint {sprint_num}: {title}")
    print(f"  Type: {sprint_type}")
    print(f"  Epic: {epic or 'None (standalone)'}")
    print(f"  Folder: {sprint_dir.relative_to(project_root)}")

    return {"sprint_dir": str(sprint_dir), "sprint_file": str(sprint_file)}


def start_sprint(sprint_num: int, dry_run: bool = False) -> dict:
    """
    Start a sprint: move to in-progress, create state file, update YAML.

    Args:
        sprint_num: Sprint number to start
        dry_run: If True, preview changes without executing

    Returns:
        Dict with start summary

    Raises:
        FileOperationError: If sprint file not found
        ValidationError: If sprint already started or in wrong state

    Example:
        >>> summary = start_sprint(3)
        >>> print(summary['status'])  # 'started'
    """
    project_root = find_project_root()

    # Find sprint in backlog, todo, or in-progress (for epic sprints)
    sprint_file = None
    already_in_progress = False

    for folder in ["0-backlog", "1-todo"]:
        search_path = project_root / "docs" / "sprints" / folder
        if search_path.exists():
            found = list(search_path.glob(f"**/sprint-{sprint_num:02d}_*.md"))
            if found:
                sprint_file = found[0]
                break

    # If not found in backlog/todo, check if it's an epic sprint already in progress
    if not sprint_file:
        search_path = project_root / "docs" / "sprints" / "2-in-progress"
        if search_path.exists():
            # Look for sprint in epic folders (exclude --done files)
            found = [
                f
                for f in search_path.glob(f"**/sprint-{sprint_num:02d}_*.md")
                if "--done" not in f.name
            ]
            if found:
                sprint_file = found[0]
                already_in_progress = True

    if not sprint_file:
        raise FileOperationError(
            f"Sprint {sprint_num} not found in backlog, todo, or in-progress folders"
        )

    # Check if sprint is in an epic
    is_epic, epic_num = is_epic_sprint(sprint_file)

    # Read content and check for YAML frontmatter
    with open(sprint_file) as f:
        content = f.read()

    import re

    yaml_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)

    if yaml_match:
        # Parse existing frontmatter
        yaml_content = yaml_match.group(1)
        title_match = re.search(r"^title:\s*(.+)$", yaml_content, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip().strip('"')
        else:
            # Try to get title from markdown heading
            heading_match = re.search(
                r"^#\s+Sprint\s+\d+:\s*(.+)$", content, re.MULTILINE
            )
            title = (
                heading_match.group(1).strip()
                if heading_match
                else f"Sprint {sprint_num}"
            )
    else:
        # No frontmatter - extract title from markdown heading and add frontmatter
        heading_match = re.search(r"^#\s+Sprint\s+\d+:\s*(.+)$", content, re.MULTILINE)
        title = (
            heading_match.group(1).strip() if heading_match else f"Sprint {sprint_num}"
        )

        # Read WORKFLOW_VERSION
        version_file = project_root / ".claude" / "WORKFLOW_VERSION"
        workflow_version = (
            version_file.read_text().strip() if version_file.exists() else "3.1.0"
        )

        # Add YAML frontmatter to file
        frontmatter = f"""---
sprint: {sprint_num}
title: "{title}"
epic: {epic_num if is_epic else 'null'}
status: planning
created: {datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")}
started: null
completed: null
hours: null
workflow_version: "{workflow_version}"
---

"""
        with open(sprint_file, "w") as f:
            f.write(frontmatter + content)
        print("✓ Added YAML frontmatter to sprint file")

    if dry_run:
        print(f"[DRY RUN] Would start sprint {sprint_num}:")
        print(f"  Title: {title}")
        print(f"  Epic: {epic_num if is_epic else 'standalone'}")
        if already_in_progress:
            print("  1. Sprint already in 2-in-progress/ (epic sprint)")
        else:
            print("  1. Move to 2-in-progress/")
        print("  2. Update YAML (status=in-progress, started=<now>)")
        print(f"  3. Create state file .claude/sprint-{sprint_num}-state.json")
        return {"status": "dry-run", "sprint_num": sprint_num}

    # Update YAML frontmatter
    started_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    update_yaml_frontmatter(
        sprint_file, {"status": "in-progress", "started": started_time}
    )

    # Move to in-progress (skip if already there - epic sprint case)
    if already_in_progress:
        new_path = sprint_file
        print(f"✓ Sprint already in progress (epic sprint): {sprint_file}")
    else:
        in_progress_dir = project_root / "docs" / "sprints" / "2-in-progress"
        in_progress_dir.mkdir(parents=True, exist_ok=True)

        if is_epic:
            # Find the epic folder (could be parent or grandparent)
            if sprint_file.parent.name.startswith("sprint-"):
                epic_folder = sprint_file.parent.parent
                sprint_folder_name = sprint_file.parent.name
            else:
                epic_folder = sprint_file.parent
                sprint_folder_name = None

            # Check if epic is in 0-backlog or 1-todo - if so, move entire epic
            if "0-backlog" in str(epic_folder) or "1-todo" in str(epic_folder):
                # Move entire epic folder to 2-in-progress
                new_epic_folder = in_progress_dir / epic_folder.name
                if new_epic_folder.exists():
                    # Epic already partially in progress, just move the sprint
                    if sprint_folder_name:
                        old_sprint_dir = sprint_file.parent
                        new_sprint_dir = new_epic_folder / sprint_folder_name
                        shutil.move(str(old_sprint_dir), str(new_sprint_dir))
                        new_path = new_sprint_dir / sprint_file.name
                    else:
                        new_path = new_epic_folder / sprint_file.name
                        shutil.move(str(sprint_file), str(new_path))
                else:
                    # Move entire epic folder
                    shutil.move(str(epic_folder), str(new_epic_folder))
                    print(
                        f"✓ Moved epic folder to: {new_epic_folder.relative_to(project_root)}"
                    )
                    if sprint_folder_name:
                        new_path = (
                            new_epic_folder / sprint_folder_name / sprint_file.name
                        )
                    else:
                        new_path = new_epic_folder / sprint_file.name
            else:
                # Epic already in progress folder
                new_path = sprint_file
        else:
            # Standalone sprint - check if in its own folder
            if sprint_file.parent.name.startswith("sprint-"):
                old_sprint_dir = sprint_file.parent
                new_sprint_dir = in_progress_dir / sprint_file.parent.name
                shutil.move(str(old_sprint_dir), str(new_sprint_dir))
                new_path = new_sprint_dir / sprint_file.name
            else:
                new_path = in_progress_dir / sprint_file.name
                shutil.move(str(sprint_file), str(new_path))

        print(f"✓ Moved to: {new_path}")

    # Create state file
    state_file = project_root / ".claude" / f"sprint-{sprint_num}-state.json"
    state = {
        "sprint_number": sprint_num,
        "sprint_file": str(new_path.relative_to(project_root)),
        "sprint_title": title,
        "status": "in_progress",
        "current_phase": 1,
        "current_step": "1.1",
        "started_at": started_time,
        "workflow_version": "3.0",
        "completed_steps": [],
    }

    state_file.parent.mkdir(parents=True, exist_ok=True)
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)
    print(f"✓ State file created: {state_file.name}")

    summary = {
        "status": "started",
        "sprint_num": sprint_num,
        "title": title,
        "file_path": str(new_path),
        "epic": epic_num if is_epic else None,
    }

    print(f"\n{'='*60}")
    print(f"Sprint {sprint_num}: {title} - STARTED ✓")
    print(f"{'='*60}")
    print(f"File: {new_path.relative_to(project_root)}")
    if is_epic:
        print(f"Epic: {epic_num}")
    print("Next: Begin Phase 1 (Planning)")
    print(f"{'='*60}")

    return summary


def abort_sprint(sprint_num: int, reason: str, dry_run: bool = False) -> dict:
    """
    Abort a sprint: rename with --aborted suffix, update state.

    Args:
        sprint_num: Sprint number to abort
        reason: Reason for aborting
        dry_run: If True, preview changes without executing

    Returns:
        Dict with abort summary

    Raises:
        FileOperationError: If sprint file not found
        ValidationError: If sprint already aborted

    Example:
        >>> summary = abort_sprint(4, "Requirements changed")
        >>> print(summary['status'])  # 'aborted'
    """
    project_root = find_project_root()
    sprint_file = find_sprint_file(sprint_num, project_root)

    if not sprint_file:
        raise FileOperationError(f"Sprint {sprint_num} not found")

    # Check if already aborted
    if "--aborted" in sprint_file.name:
        raise ValidationError(f"Sprint {sprint_num} already aborted: {sprint_file}")

    # Read YAML for metadata
    with open(sprint_file) as f:
        content = f.read()

    import re

    yaml_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not yaml_match:
        raise ValidationError(f"Sprint {sprint_num} missing YAML frontmatter")

    yaml_content = yaml_match.group(1)
    title_match = re.search(r"^title:\s*(.+)$", yaml_content, re.MULTILINE)
    started_match = re.search(r"^started:\s*(.+)$", yaml_content, re.MULTILINE)

    title = title_match.group(1).strip().strip('"') if title_match else "Unknown"

    # Calculate hours if started
    hours = None
    if started_match:
        started_str = started_match.group(1).strip()
        # Only calculate hours if started is not null
        if started_str and started_str.lower() != "null":
            started = datetime.fromisoformat(started_str.replace("Z", "+00:00"))
            aborted = datetime.now().astimezone()
            hours = round((aborted - started).total_seconds() / 3600, 1)

    if dry_run:
        print(f"[DRY RUN] Would abort sprint {sprint_num}:")
        print(f"  Title: {title}")
        print(f"  Reason: {reason}")
        print(f"  Hours: {hours if hours else 'N/A'}")
        print("  1. Update YAML (status=aborted, reason, hours)")
        print("  2. Rename with --aborted suffix")
        print("  3. Update state file")
        return {"status": "dry-run", "sprint_num": sprint_num}

    # Update YAML frontmatter
    aborted_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    updates = {"status": "aborted", "aborted_at": aborted_time, "abort_reason": reason}
    if hours:
        updates["hours"] = hours

    update_yaml_frontmatter(sprint_file, updates)

    # Rename with --aborted suffix
    if sprint_file.parent.name.startswith("sprint-"):
        # Sprint in subdirectory
        sprint_subdir = sprint_file.parent
        new_dir_name = sprint_subdir.name + "--aborted"
        new_subdir = sprint_subdir.with_name(new_dir_name)
        sprint_subdir.rename(new_subdir)

        new_name = sprint_file.name.replace(".md", "--aborted.md")
        new_path = new_subdir / new_name
        (new_subdir / sprint_file.name).rename(new_path)
    else:
        # Sprint file directly in folder
        new_name = sprint_file.name.replace(".md", "--aborted.md")
        new_path = sprint_file.with_name(new_name)
        sprint_file.rename(new_path)

    print(f"✓ Renamed to: {new_path.name}")

    # Update state file
    state_file = project_root / ".claude" / f"sprint-{sprint_num}-state.json"
    if state_file.exists():
        with open(state_file) as f:
            state = json.load(f)
        state["status"] = "aborted"
        state["aborted_at"] = aborted_time
        state["abort_reason"] = reason
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)
        print("✓ State file updated")

    # Update registry
    update_registry(
        sprint_num, status="aborted", abort_reason=reason, hours=hours if hours else 0
    )
    print("✓ Registry updated")

    summary = {
        "status": "aborted",
        "sprint_num": sprint_num,
        "title": title,
        "reason": reason,
        "hours": hours,
        "file_path": str(new_path),
    }

    print(f"\n{'='*60}")
    print(f"Sprint {sprint_num}: {title} - ABORTED")
    print(f"{'='*60}")
    print(f"Reason: {reason}")
    print(f"Hours before abort: {hours if hours else 'N/A'}")
    print(f"File: {new_path.name}")
    print(f"{'='*60}")

    return summary


def block_sprint(sprint_num: int, reason: str, dry_run: bool = False) -> dict:
    """
    Block a sprint: rename with --blocked suffix, update state.

    Args:
        sprint_num: Sprint number to block
        reason: Reason for blocking
        dry_run: If True, preview changes without executing

    Returns:
        Dict with block summary

    Raises:
        FileOperationError: If sprint file not found
        ValidationError: If sprint already blocked

    Example:
        >>> summary = block_sprint(4, "Waiting for API access")
        >>> print(summary['status'])  # 'blocked'
    """
    project_root = find_project_root()
    sprint_file = find_sprint_file(sprint_num, project_root)

    if not sprint_file:
        raise FileOperationError(f"Sprint {sprint_num} not found")

    # Check if already blocked
    if "--blocked" in sprint_file.name:
        raise ValidationError(f"Sprint {sprint_num} already blocked: {sprint_file}")

    # Read YAML for metadata
    with open(sprint_file) as f:
        content = f.read()

    import re

    yaml_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not yaml_match:
        raise ValidationError(f"Sprint {sprint_num} missing YAML frontmatter")

    yaml_content = yaml_match.group(1)
    title_match = re.search(r"^title:\s*(.+)$", yaml_content, re.MULTILINE)
    started_match = re.search(r"^started:\s*(.+)$", yaml_content, re.MULTILINE)

    title = title_match.group(1).strip().strip('"') if title_match else "Unknown"

    # Calculate hours worked so far
    hours = None
    if started_match:
        started_str = started_match.group(1).strip()
        if started_str and started_str.lower() != "null":
            started = datetime.fromisoformat(started_str.replace("Z", "+00:00"))
            blocked = datetime.now().astimezone()
            hours = round((blocked - started).total_seconds() / 3600, 1)

    if dry_run:
        print(f"[DRY RUN] Would block sprint {sprint_num}:")
        print(f"  Title: {title}")
        print(f"  Reason: {reason}")
        print(f"  Hours so far: {hours if hours else 'N/A'}")
        print("  1. Update YAML (status=blocked, blocker, hours_before_block)")
        print("  2. Rename with --blocked suffix")
        print("  3. Update state file")
        return {"status": "dry-run", "sprint_num": sprint_num}

    # Update YAML frontmatter
    blocked_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    updates = {"status": "blocked", "blocked_at": blocked_time, "blocker": reason}
    if hours:
        updates["hours_before_block"] = hours

    update_yaml_frontmatter(sprint_file, updates)

    # Rename with --blocked suffix
    if sprint_file.parent.name.startswith("sprint-"):
        # Sprint in subdirectory
        sprint_subdir = sprint_file.parent
        new_dir_name = sprint_subdir.name + "--blocked"
        new_subdir = sprint_subdir.with_name(new_dir_name)
        sprint_subdir.rename(new_subdir)

        new_name = sprint_file.name.replace(".md", "--blocked.md")
        new_path = new_subdir / new_name
    else:
        # Sprint file directly in folder
        new_name = sprint_file.name.replace(".md", "--blocked.md")
        new_path = sprint_file.with_name(new_name)
        sprint_file.rename(new_path)

    # Update state file
    state_file = project_root / ".claude" / f"sprint-{sprint_num}-state.json"
    if state_file.exists():
        with open(state_file) as f:
            state = json.load(f)
        state["status"] = "blocked"
        state["blocked_at"] = blocked_time
        state["blocker"] = reason
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)

    summary = {
        "sprint_num": sprint_num,
        "title": title,
        "status": "blocked",
        "reason": reason,
        "hours": hours,
        "new_path": str(new_path),
    }

    print(f"\n{'='*60}")
    print(f"Sprint {sprint_num}: {title} - BLOCKED")
    print(f"{'='*60}")
    print(f"Blocker: {reason}")
    print(f"Hours before block: {hours if hours else 'N/A'}")
    print(f"File: {new_path.name}")
    print(f"To resume: /sprint-resume {sprint_num}")
    print(f"{'='*60}")

    return summary


def resume_sprint(sprint_num: int, dry_run: bool = False) -> dict:
    """
    Resume a blocked sprint: remove --blocked suffix, update state.

    Args:
        sprint_num: Sprint number to resume
        dry_run: If True, preview changes without executing

    Returns:
        Dict with resume summary

    Raises:
        FileOperationError: If sprint file not found
        ValidationError: If sprint not blocked

    Example:
        >>> summary = resume_sprint(4)
        >>> print(summary['status'])  # 'resumed'
    """
    project_root = find_project_root()
    sprint_file = find_sprint_file(sprint_num, project_root)

    if not sprint_file:
        raise FileOperationError(f"Sprint {sprint_num} not found")

    # Check if sprint is blocked
    if "--blocked" not in sprint_file.name:
        raise ValidationError(
            f"Sprint {sprint_num} is not blocked. Current state: {sprint_file.name}"
        )

    # Read YAML for metadata
    with open(sprint_file) as f:
        content = f.read()

    import re

    yaml_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not yaml_match:
        raise ValidationError(f"Sprint {sprint_num} missing YAML frontmatter")

    yaml_content = yaml_match.group(1)
    title_match = re.search(r"^title:\s*(.+)$", yaml_content, re.MULTILINE)
    blocker_match = re.search(r"^blocker:\s*(.+)$", yaml_content, re.MULTILINE)
    hours_match = re.search(
        r"^hours_before_block:\s*([0-9.]+)", yaml_content, re.MULTILINE
    )

    title = title_match.group(1).strip().strip('"') if title_match else "Unknown"
    blocker = blocker_match.group(1).strip().strip('"') if blocker_match else "Unknown"
    hours_before = float(hours_match.group(1)) if hours_match else None

    if dry_run:
        print(f"[DRY RUN] Would resume sprint {sprint_num}:")
        print(f"  Title: {title}")
        print(f"  Was blocked by: {blocker}")
        print(f"  Hours before block: {hours_before if hours_before else 'N/A'}")
        print("  1. Update YAML (status=in-progress, resumed_at, previous_blocker)")
        print("  2. Remove --blocked suffix")
        print("  3. Update state file")
        return {"status": "dry-run", "sprint_num": sprint_num}

    # Update YAML frontmatter
    resumed_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    updates = {
        "status": "in-progress",
        "resumed_at": resumed_time,
        "previous_blocker": blocker,
    }
    # Remove blocked-specific fields
    updates["blocker"] = None
    updates["blocked_at"] = None

    update_yaml_frontmatter(sprint_file, updates)

    # Remove --blocked suffix
    if (
        sprint_file.parent.name.startswith("sprint-")
        and "--blocked" in sprint_file.parent.name
    ):
        # Sprint in subdirectory
        sprint_subdir = sprint_file.parent
        new_dir_name = sprint_subdir.name.replace("--blocked", "")
        new_subdir = sprint_subdir.with_name(new_dir_name)
        sprint_subdir.rename(new_subdir)

        new_name = sprint_file.name.replace("--blocked", "")
        new_path = new_subdir / new_name
    else:
        # Sprint file directly in folder
        new_name = sprint_file.name.replace("--blocked", "")
        new_path = sprint_file.with_name(new_name)
        sprint_file.rename(new_path)

    # Update state file
    state_file = project_root / ".claude" / f"sprint-{sprint_num}-state.json"
    if state_file.exists():
        with open(state_file) as f:
            state = json.load(f)
        state["status"] = "in-progress"
        state["resumed_at"] = resumed_time
        state["previous_blocker"] = blocker
        # Remove blocked fields
        state.pop("blocker", None)
        state.pop("blocked_at", None)
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)

    summary = {
        "sprint_num": sprint_num,
        "title": title,
        "status": "resumed",
        "previous_blocker": blocker,
        "hours_before_block": hours_before,
        "new_path": str(new_path),
    }

    print(f"\n{'='*60}")
    print(f"Sprint {sprint_num}: {title} - RESUMED")
    print(f"{'='*60}")
    print(f"Previously blocked by: {blocker}")
    print(f"Hours before block: {hours_before if hours_before else 'N/A'}")
    print(f"File: {new_path.name}")
    print(f"Use /sprint-next {sprint_num} to continue")
    print(f"{'='*60}")

    return summary


def recover_sprint(sprint_num: int, dry_run: bool = False) -> dict:
    """
    Recover a sprint file that ended up in the wrong location.

    Args:
        sprint_num: Sprint number to recover
        dry_run: If True, preview changes without executing

    Returns:
        Dict with recovery summary

    Raises:
        FileOperationError: If sprint file not found
        ValidationError: If sprint is already in correct location

    Example:
        >>> summary = recover_sprint(4)
        >>> print(summary['new_path'])
    """
    project_root = find_project_root()
    sprint_file = find_sprint_file(sprint_num, project_root)

    if not sprint_file:
        raise FileOperationError(f"Sprint {sprint_num} not found")

    # Determine correct location
    is_epic, epic_num = is_epic_sprint(sprint_file)
    has_done_suffix = "--done" in sprint_file.name

    # Determine expected location
    if not has_done_suffix:
        raise ValidationError(
            f"Sprint {sprint_num} is not complete (no --done suffix). Nothing to recover."
        )

    if is_epic:
        # Epic sprint - should be in epic folder (either in-progress or done depending on epic status)
        expected_parent = sprint_file.parent
        if not expected_parent.name.startswith("epic-"):
            expected_parent = expected_parent.parent

        # Check if we need to move
        if "3-done" in str(sprint_file) and "2-in-progress" in str(expected_parent):
            # Epic sprint in wrong location
            correct_path = expected_parent / sprint_file.name
        else:
            raise ValidationError(f"Sprint {sprint_num} is already in correct location")
    else:
        # Standalone sprint - should be in 3-done
        correct_folder = project_root / "docs" / "sprints" / "3-done"
        correct_path = correct_folder / sprint_file.name

        if sprint_file.parent == correct_folder:
            raise ValidationError(f"Sprint {sprint_num} is already in correct location")

    if dry_run:
        print(f"[DRY RUN] Would recover sprint {sprint_num}:")
        print(f"  From: {sprint_file}")
        print(f"  To: {correct_path}")
        return {"status": "dry-run", "sprint_num": sprint_num}

    # Move file
    correct_path.parent.mkdir(parents=True, exist_ok=True)
    sprint_file.rename(correct_path)

    # Update state file if exists
    state_file = project_root / ".claude" / f"sprint-{sprint_num}-state.json"
    if state_file.exists():
        with open(state_file) as f:
            state = json.load(f)
        state["sprint_file"] = str(correct_path)
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)

    summary = {
        "sprint_num": sprint_num,
        "old_path": str(sprint_file),
        "new_path": str(correct_path),
    }

    print(f"\n{'='*60}")
    print(f"Sprint {sprint_num} - RECOVERED")
    print(f"{'='*60}")
    print(f"From: {sprint_file}")
    print(f"To: {correct_path}")
    print(f"{'='*60}")

    return summary
