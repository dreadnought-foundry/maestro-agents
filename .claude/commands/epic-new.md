---
description: "Create a new epic to group related sprints"
allowed-tools: [Read, Write, Glob, Bash]
---

# Create Epic: $ARGUMENTS

Create a new epic folder with metadata file in the kanban board.

## Instructions

### 1. Parse Arguments

Parse $ARGUMENTS to get the epic title (e.g., "Mobile Field Application").

If no title provided, ask the user for one.

### 2. Determine Next Epic Number

Scan all kanban columns for existing epic directories:

```
kanban/*/epic-*
kanban/*/epic-*/
```

Extract the highest epic number (e.g., `epic-08_...` → 8), then use N+1 as the new epic number. Zero-pad to two digits.

### 3. Create Slug

Convert title to slug:
- Lowercase
- Replace spaces with hyphens
- Remove special characters
- Example: "Mobile Field Application" → "mobile-field-application"

### 4. Create Epic Folder and File

Create the epic directory and metadata file:

- Directory: `kanban/1-todo/epic-{NN}_{slug}/`
- File: `kanban/1-todo/epic-{NN}_{slug}/_epic.md`

Use this template for `_epic.md`:

```markdown
---
epic: {N}
title: "{Title}"
created: {TODAY_ISO_DATE}
started: null
completed: null
---

# Epic {NN}: {Title}

## Overview

{To be filled in — describe the strategic initiative}

## Success Criteria

- [ ] {Define measurable outcomes}

## Sprints

| Sprint | Title | Status |
|--------|-------|--------|

## Notes

Created: {TODAY_ISO_DATE}
```

Where:
- `{N}` is the unpadded number (e.g., 9)
- `{NN}` is zero-padded (e.g., 09)
- `{TODAY_ISO_DATE}` is today's date in YYYY-MM-DD format
- `{Title}` is the original title with proper casing

### 5. Report

Output:
```
Created: kanban/1-todo/epic-{NN}_{slug}/_epic.md

Next steps:
1. Fill in the Overview and Success Criteria
2. Use /sprint-new "{title}" --epic={N} to create sprints in this epic
```
