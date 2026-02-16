"""Tests for the cumulative context filtering layer."""

from __future__ import annotations

import pytest

from src.execution.context_selector import (
    SelectedContext,
    _filter_markdown,
    _parse_sections,
    _score_section,
    _tokenize,
    select_context,
)


# ---------------------------------------------------------------------------
# Sample content
# ---------------------------------------------------------------------------

DEFERRED = """\
# Deferred Items

## Production Integration

- [ ] Production SDK integration (Claude Agent SDK for real agent execution)
  ↳ 🔴 High · L · Complexity 3 · (S01, S03, S05, S06, S13)
- [ ] Real Claude API calls (move from mocks/InMemory to production)
  ↳ 🔴 High · M · Complexity 2 · (S01, S13)

## Analytics & Metrics

- [ ] Agent execution metrics (tokens, duration) on AgentResult
  ↳ 🟡 Medium · M · Complexity 2 · (S12, S16)
- [ ] Test result trending across sprints
  ↳ 🟡 Medium · M · Complexity 2 · (S14)

## UI & User Experience

- [ ] Web UI for sprint monitoring
  ↳ 🟡 Medium · L · Complexity 3 · (S21)
- [ ] Filtering by epic or status (Kanban TUI)
  ↳ 🟢 Low · S · Complexity 1 · (S22b)

## Testing & Quality

- [ ] Performance benchmarking suite
  ↳ 🟡 Medium · M · Complexity 2 · (S08)
- [ ] Mutation testing integration
  ↳ 🟡 Medium · M · Complexity 2 · (S08)

## Operations & Resilience

- [ ] Exponential backoff on retries
  ↳ 🟡 Medium · S · Complexity 1 · (S18)
"""

POSTMORTEM = """\
# Sprint Postmortems

## Timeline
- **S01** [Workflow Models] — Success 5/5 steps
- **S14** [Test Runner Agent] — Success 3/3 steps

## Architecture & Design Patterns

**Protocol-First Design** (S01): Define protocol before implementation.

## Testing Strategy

**Test Pyramid** (S08, S23): Unit tests, integration tests, e2e tests.
**Edge Case Testing** (S08): Test empty strings, unicode, long inputs.

## Common Pitfalls

**Mutable Defaults** (S01): Use field(default_factory=list).
**Subprocess Output Parsing** (S14): Pytest output has multiple formats.
"""


# ---------------------------------------------------------------------------
# Tokenizer tests
# ---------------------------------------------------------------------------


class TestTokenize:
    def test_extracts_lowercase_words(self):
        tokens = _tokenize("Build Agent Infrastructure")
        assert "build" in tokens
        assert "agent" in tokens
        assert "infrastructure" in tokens

    def test_filters_short_words(self):
        tokens = _tokenize("a to do it by me")
        assert len(tokens) == 0

    def test_filters_stop_words(self):
        tokens = _tokenize("the and for with from")
        assert len(tokens) == 0

    def test_handles_mixed_content(self):
        tokens = _tokenize("Production SDK integration (S01, S03)")
        assert "production" in tokens
        assert "sdk" in tokens
        assert "integration" in tokens


# ---------------------------------------------------------------------------
# Section parsing tests
# ---------------------------------------------------------------------------


class TestParseSections:
    def test_parses_h2_sections(self):
        sections = _parse_sections(DEFERRED)
        headings = [h for h, _ in sections]
        assert "Production Integration" in headings
        assert "Analytics & Metrics" in headings
        assert "UI & User Experience" in headings

    def test_excludes_h1(self):
        sections = _parse_sections(DEFERRED)
        headings = [h for h, _ in sections]
        assert "Deferred Items" not in headings

    def test_body_contains_items(self):
        sections = _parse_sections(DEFERRED)
        prod_section = [body for h, body in sections if h == "Production Integration"][0]
        assert "Production SDK integration" in prod_section

    def test_empty_content(self):
        assert _parse_sections("") == []

    def test_no_sections(self):
        assert _parse_sections("# Just a title\nSome text") == []


# ---------------------------------------------------------------------------
# Scoring tests
# ---------------------------------------------------------------------------


class TestScoreSection:
    def test_high_overlap_scores_higher(self):
        goal_tokens = _tokenize("Build production SDK integration")
        prod_score = _score_section(
            "Production Integration",
            "Production SDK integration",
            goal_tokens,
        )
        ui_score = _score_section(
            "UI & User Experience",
            "Web UI for sprint monitoring",
            goal_tokens,
        )
        assert prod_score > ui_score

    def test_high_importance_gets_bonus(self):
        goal_tokens = _tokenize("something unrelated entirely")
        score_with_high = _score_section(
            "Production Integration",
            "- [ ] Item\n  ↳ 🔴 High · L",
            goal_tokens,
        )
        score_without_high = _score_section(
            "UI Section",
            "- [ ] Item\n  ↳ 🟢 Low · S",
            goal_tokens,
        )
        assert score_with_high > score_without_high

    def test_zero_overlap_with_no_high(self):
        goal_tokens = _tokenize("completely unrelated topic xyz")
        score = _score_section(
            "Operations",
            "Exponential backoff on retries\n  ↳ 🟡 Medium",
            goal_tokens,
        )
        assert score == 0


# ---------------------------------------------------------------------------
# Markdown filtering tests
# ---------------------------------------------------------------------------


class TestFilterMarkdown:
    def test_returns_relevant_sections(self):
        goal_tokens = _tokenize("Build production SDK integration")
        result = _filter_markdown(DEFERRED, goal_tokens, max_sections=2)
        assert result is not None
        assert "Production Integration" in result
        # H1 is preserved
        assert result.startswith("# Deferred Items")

    def test_limits_to_max_sections(self):
        goal_tokens = _tokenize("testing quality metrics analytics agent production")
        result = _filter_markdown(DEFERRED, goal_tokens, max_sections=2)
        assert result is not None
        # Count ## headings in result
        section_count = result.count("\n## ")
        assert section_count <= 2

    def test_irrelevant_goal_still_includes_high_importance(self):
        """High-importance (🔴) sections are always included even without keyword match."""
        goal_tokens = _tokenize("xyzzy plugh completely alien")
        result = _filter_markdown(DEFERRED, goal_tokens, max_sections=3)
        # Production Integration has 🔴 High items so it surfaces regardless
        assert result is not None
        assert "Production Integration" in result
        # Low-relevance sections without 🔴 should be excluded
        assert "UI & User Experience" not in result

    def test_returns_none_for_content_without_high_or_overlap(self):
        """Returns None when no sections have keyword overlap or high importance."""
        content = """\
# Items

## Mundane Section

- [ ] Something boring
  ↳ 🟢 Low · S · Complexity 1 · (S99)
"""
        goal_tokens = _tokenize("xyzzy plugh completely alien")
        result = _filter_markdown(content, goal_tokens, max_sections=3)
        assert result is None

    def test_returns_none_for_empty_content(self):
        result = _filter_markdown("", _tokenize("anything"), max_sections=3)
        assert result is None


# ---------------------------------------------------------------------------
# Step-type routing tests
# ---------------------------------------------------------------------------


class TestSelectContext:
    def test_implement_gets_both(self):
        ctx = select_context(
            step_type="implement",
            sprint_goal="Build production SDK integration",
            cumulative_deferred=DEFERRED,
            cumulative_postmortem=POSTMORTEM,
        )
        assert ctx.deferred is not None
        assert ctx.postmortem is not None

    def test_review_gets_both(self):
        ctx = select_context(
            step_type="review",
            sprint_goal="Build production SDK integration",
            cumulative_deferred=DEFERRED,
            cumulative_postmortem=POSTMORTEM,
        )
        assert ctx.deferred is not None
        assert ctx.postmortem is not None

    def test_test_step_gets_neither(self):
        ctx = select_context(
            step_type="test",
            sprint_goal="Build production SDK integration",
            cumulative_deferred=DEFERRED,
            cumulative_postmortem=POSTMORTEM,
        )
        assert ctx.deferred is None
        assert ctx.postmortem is None

    def test_run_tests_gets_neither(self):
        ctx = select_context(
            step_type="run_tests",
            sprint_goal="Build production SDK integration",
            cumulative_deferred=DEFERRED,
            cumulative_postmortem=POSTMORTEM,
        )
        assert ctx.deferred is None
        assert ctx.postmortem is None

    def test_write_code_gets_both(self):
        ctx = select_context(
            step_type="write_code",
            sprint_goal="Build test runner infrastructure",
            cumulative_deferred=DEFERRED,
            cumulative_postmortem=POSTMORTEM,
        )
        assert ctx.deferred is not None
        assert ctx.postmortem is not None

    def test_none_inputs_produce_none_outputs(self):
        ctx = select_context(
            step_type="implement",
            sprint_goal="Build something",
            cumulative_deferred=None,
            cumulative_postmortem=None,
        )
        assert ctx.deferred is None
        assert ctx.postmortem is None

    def test_unknown_step_type_gets_neither(self):
        ctx = select_context(
            step_type="deploy",
            sprint_goal="Deploy to production",
            cumulative_deferred=DEFERRED,
            cumulative_postmortem=POSTMORTEM,
        )
        assert ctx.deferred is None
        assert ctx.postmortem is None


# ---------------------------------------------------------------------------
# Relevance quality tests — verify filtering selects the right sections
# ---------------------------------------------------------------------------


class TestRelevanceQuality:
    def test_production_goal_selects_production_deferred(self):
        ctx = select_context(
            step_type="implement",
            sprint_goal="Integrate production SDK and API calls",
            cumulative_deferred=DEFERRED,
            cumulative_postmortem=POSTMORTEM,
        )
        assert ctx.deferred is not None
        assert "Production Integration" in ctx.deferred
        # UI section should NOT be included (low relevance)
        assert "UI & User Experience" not in ctx.deferred

    def test_testing_goal_selects_testing_sections(self):
        ctx = select_context(
            step_type="implement",
            sprint_goal="Build testing infrastructure and quality gates",
            cumulative_deferred=DEFERRED,
            cumulative_postmortem=POSTMORTEM,
        )
        assert ctx.deferred is not None
        assert "Testing & Quality" in ctx.deferred
        assert ctx.postmortem is not None
        assert "Testing Strategy" in ctx.postmortem

    def test_filtered_deferred_is_smaller_than_raw(self):
        ctx = select_context(
            step_type="implement",
            sprint_goal="Build production SDK",
            cumulative_deferred=DEFERRED,
            cumulative_postmortem=POSTMORTEM,
        )
        assert ctx.deferred is not None
        assert len(ctx.deferred) < len(DEFERRED)

    def test_filtered_postmortem_is_smaller_than_raw(self):
        ctx = select_context(
            step_type="review",
            sprint_goal="Review testing strategy",
            cumulative_deferred=DEFERRED,
            cumulative_postmortem=POSTMORTEM,
        )
        assert ctx.postmortem is not None
        assert len(ctx.postmortem) < len(POSTMORTEM)
