---
description: "Create a standalone spec document"
allowed-tools: [Read, Write, Glob]
---

# Create Spec: $ARGUMENTS

Create a standalone specification document.

## Instructions

### 1. Parse Arguments

Parse $ARGUMENTS to get:
- **Title** (required): the spec topic (e.g., "Authentication Redesign")
- **--dir=PATH** (optional): directory to create the spec in (default: current directory)

If no title provided, ask the user for one.

### 2. Create Slug

Convert title to slug:
- Lowercase
- Replace spaces with hyphens
- Remove special characters
- Example: "Authentication Redesign" → "authentication-redesign"

### 3. Create Spec File

Create `{slug}.md` in the target directory.

Use this template:

```markdown
---
title: "{Title}"
created: {TODAY_ISO_DATE}
status: draft
---

# {Title}

## Overview

{What is this spec about? What problem does it solve?}

## Goals

- {Goal 1}
- {Goal 2}

## Non-Goals

- {What is explicitly out of scope}

## Design

### Approach

{Describe the technical approach}

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|

## Implementation Plan

1. {Step 1}
2. {Step 2}
3. {Step 3}

## Open Questions

- {Questions that need answering}
```

Where:
- `{Title}` is the original title with proper casing
- `{TODAY_ISO_DATE}` is today's date in YYYY-MM-DD format

### 4. Report

Output:
```
Created: {path_to_spec_file}

Next steps:
1. Fill in the Overview and Design sections
2. Review with stakeholders
```
