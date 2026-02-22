---
description: "Create a new sprint spec inside an epic or standalone"
allowed-tools: [Read, Write, Glob, Bash]
---

# Create Sprint: $ARGUMENTS

Create a new sprint directory with spec file in the kanban board.

## Instructions

### 1. Parse Arguments

Parse $ARGUMENTS to extract:
- **Title** (required): e.g., "Photo Upload Feature"
- **--epic=N** (optional): epic number to nest this sprint under
- **--type=TYPE** (optional, default: "backend"): sprint type (backend, frontend, infrastructure, integration, refactor)

If no title provided, ask the user for one.

### 2. Determine Next Sprint Number

Scan all kanban columns for existing sprint directories:

```
kanban/*/sprint-*
kanban/*/epic-*/sprint-*
```

Extract the highest sprint number (e.g., `sprint-37_...` → 37), then use N+1 as the new sprint number. Zero-pad to two digits.

### 3. Create Slug

Convert title to slug:
- Lowercase
- Replace spaces with hyphens
- Remove special characters
- Example: "Photo Upload Feature" → "photo-upload-feature"

### 4. Locate Parent Directory

- **If --epic=N provided**: Find the epic directory across all columns:
  ```
  kanban/*/epic-{NN}_*/
  ```
  Create the sprint inside that epic directory. If the epic is not found, warn the user and abort.

- **If no epic**: Create as a standalone sprint in `kanban/1-todo/`.

### 5. Create Sprint Directory and Spec File

- Directory: `{parent}/sprint-{NN}_{slug}/`
- Spec file: `{parent}/sprint-{NN}_{slug}/sprint-{NN}_{slug}.md`

Use this template for the spec file:

```markdown
---
sprint: {N}
title: "{Title}"
type: {type}
epic: {epic_number_or_null}
created: {TODAY_ISO_TIMESTAMP}
started: null
completed: null
hours: null
---

# Sprint {N}: {Title}

## Overview

| Field | Value |
|-------|-------|
| Sprint | {N} |
| Title | {Title} |
| Type | {type} |
| Epic | {epic_number or "None"} |

## Goal

{One sentence describing what this sprint accomplishes}

## Background

{Why is this needed? What problem does it solve?}

## Tasks

### Phase 1: Planning
- [ ] Review requirements
- [ ] Design approach

### Phase 2: Implementation
- [ ] Write tests
- [ ] Implement feature

### Phase 3: Validation
- [ ] Run full test suite
- [ ] Quality review

## Acceptance Criteria

- [ ] {Criterion 1}
- [ ] All tests passing

## Dependencies

- **Sprints**: {List prerequisite sprints, or "None"}
- **External**: {External dependencies, or "None"}

## Open Questions

- {Any questions that need answers}
```

Where:
- `{N}` is the unpadded sprint number
- `{NN}` is zero-padded (e.g., 38)
- `{TODAY_ISO_TIMESTAMP}` is today's datetime in ISO 8601 format (e.g., 2026-02-21T00:00:00Z)
- `{type}` defaults to "backend" if not specified
- `{epic_number_or_null}` is the epic number or `null` for standalone sprints

### 6. Update Epic File (if --epic=N provided)

1. Read the epic's `_epic.md` file
2. Add a row to the Sprints table: `| {N} | {Title} | planned |`
3. If the epic file can't be found or parsed, warn but don't fail

### 7. Report

Output:
```
Created: {path_to_spec_file}
Epic: {epic_number and title, or "None (standalone sprint)"}

Next steps:
1. Fill in the Goal, Background, and Acceptance Criteria
2. Run the sprint when ready
```
