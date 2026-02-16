"""Filters cumulative deferred/postmortem content by relevance to the current step."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class SelectedContext:
    """Filtered cumulative context for a specific agent step."""

    deferred: str | None = None
    postmortem: str | None = None


# Step types that receive each kind of context.
_DEFERRED_STEP_TYPES = frozenset({
    "implement", "write_code",  # builders check for overlap with deferred work
    "review", "quality_review",  # reviewers check if any were addressed
})
_POSTMORTEM_STEP_TYPES = frozenset({
    "implement", "write_code",  # builders apply past lessons
    "review", "quality_review",  # reviewers verify lessons are followed
})

# High-importance items are always included regardless of keyword match.
_HIGH_IMPORTANCE_MARKER = "\u0001\u0001"  # not used in text; real check below
_HIGH_RE = re.compile(r"🔴 High")

# Minimum keyword overlap score to include a section.
_MIN_SCORE = 1


def _tokenize(text: str) -> set[str]:
    """Extract lowercase alpha tokens (3+ chars) from text."""
    return {w for w in re.findall(r"[a-z]{3,}", text.lower()) if w not in _STOP_WORDS}


_STOP_WORDS = frozenset({
    "the", "and", "for", "with", "from", "that", "this", "are", "was", "has",
    "have", "been", "will", "can", "all", "not", "but", "its", "per", "any",
    "use", "each", "new", "one", "two",
})


def _parse_sections(content: str) -> list[tuple[str, str]]:
    """Split markdown into (heading, body) pairs at ## boundaries.

    Returns a list of (heading_text, full_section_text) tuples.
    The H1 heading (# ...) is excluded as a section.
    """
    sections: list[tuple[str, str]] = []
    current_heading = ""
    current_lines: list[str] = []

    for line in content.split("\n"):
        if line.startswith("## "):
            # Flush previous section
            if current_heading:
                sections.append((current_heading, "\n".join(current_lines)))
            current_heading = line[3:].strip()
            current_lines = [line]
        elif line.startswith("# ") and not current_heading:
            # Skip the H1 title
            continue
        else:
            current_lines.append(line)

    # Flush last section
    if current_heading:
        sections.append((current_heading, "\n".join(current_lines)))

    return sections


def _score_section(heading: str, body: str, goal_tokens: set[str]) -> float:
    """Score a section's relevance to the sprint goal.

    Returns a float: number of overlapping tokens + bonus for high-importance items.
    """
    section_tokens = _tokenize(heading) | _tokenize(body)
    overlap = len(goal_tokens & section_tokens)

    # Bonus: sections containing 🔴 High items get +2
    if _HIGH_RE.search(body):
        overlap += 2

    return overlap


def _filter_markdown(
    content: str,
    goal_tokens: set[str],
    max_sections: int,
) -> str | None:
    """Filter a markdown file to the most relevant sections.

    Returns filtered markdown or None if nothing is relevant.
    """
    sections = _parse_sections(content)
    if not sections:
        return None

    # Score and rank
    scored = [
        (score, heading, body)
        for heading, body in sections
        if (score := _score_section(heading, body, goal_tokens)) >= _MIN_SCORE
    ]
    scored.sort(key=lambda x: x[0], reverse=True)

    if not scored:
        return None

    # Take top N sections, reassemble in original order
    top_headings = {heading for _, heading, _ in scored[:max_sections]}
    kept = [body for heading, body in sections if heading in top_headings]

    # Re-add the H1 title from the original content
    first_line = content.split("\n")[0]
    result = first_line + "\n\n" + "\n\n".join(kept)
    return result.strip()


def select_context(
    step_type: str,
    sprint_goal: str,
    cumulative_deferred: str | None,
    cumulative_postmortem: str | None,
    max_deferred_sections: int = 3,
    max_postmortem_sections: int = 2,
) -> SelectedContext:
    """Select relevant cumulative context for a given step.

    Args:
        step_type: The agent step type (e.g. "implement", "test", "review").
        sprint_goal: The current sprint's goal text, used for keyword matching.
        cumulative_deferred: Full deferred.md content, or None.
        cumulative_postmortem: Full postmortem.md content, or None.
        max_deferred_sections: Max number of deferred sections to include.
        max_postmortem_sections: Max number of postmortem sections to include.

    Returns:
        SelectedContext with filtered content (or None for each field).
    """
    goal_tokens = _tokenize(sprint_goal)

    deferred = None
    if step_type in _DEFERRED_STEP_TYPES and cumulative_deferred:
        deferred = _filter_markdown(
            cumulative_deferred, goal_tokens, max_deferred_sections,
        )

    postmortem = None
    if step_type in _POSTMORTEM_STEP_TYPES and cumulative_postmortem:
        postmortem = _filter_markdown(
            cumulative_postmortem, goal_tokens, max_postmortem_sections,
        )

    return SelectedContext(deferred=deferred, postmortem=postmortem)
