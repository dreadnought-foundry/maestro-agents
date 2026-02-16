"""LLM-based synthesis for cumulative artifact files."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import anthropic

DEFERRED_SYNTHESIS_PROMPT = """\
You are synthesizing a project's cumulative deferred-items file.  The input is \
a raw append log where each sprint added its own section.  Your job is to \
produce a **single, deduplicated, thematically grouped** version.

Rules:
1. Deduplicate items that refer to the same concept across sprints \
   (e.g. "Production SDK integration" appearing 5 times becomes one item).
2. Group items under thematic headings \
   (e.g. "Production Integration", "Analytics & Metrics", "UI/UX", \
    "Infrastructure & DevOps", "Advanced Features").
3. For each item, note the originating sprint(s) in parentheses, e.g. \
   `(S01, S03, S05)`.
4. Remove "No deferred items" sections entirely.
5. Keep checkbox format: `- [ ]` for open items.
6. Output must start with exactly `# Deferred Items` on the first line.
7. Output ONLY the synthesized markdown — no commentary, no code fences.
"""

POSTMORTEM_SYNTHESIS_PROMPT = """\
You are synthesizing a project's cumulative postmortem file.  The input is a \
raw append log where each sprint added a full postmortem section.  Your job is \
to produce a **condensed, thematically organized** version.

Rules:
1. Start with a **Timeline** section: one line per sprint showing \
   `- **S##** [goal] — [pass/fail] [steps]`.  Keep it compact.
2. Below the timeline, create thematic sections for lessons learned \
   (e.g. "Architecture & Design Patterns", "Testing Strategy", \
    "Integration Lessons", "Common Pitfalls").
3. Merge redundant lessons into single authoritative statements.  \
   Cite the sprint(s) they came from, e.g. `(S09, S11)`.
4. Preserve unique insights that apply going forward.
5. Do NOT repeat per-sprint "What Was Built" details — the timeline covers status.
6. Do NOT repeat deferred items — those live in deferred.md.
7. Output must start with exactly `# Sprint Postmortems` on the first line.
8. Output ONLY the synthesized markdown — no commentary, no code fences.
"""


class Synthesizer:
    """LLM-based synthesis for cumulative artifact files."""

    def __init__(self, model: str = "claude-sonnet-4-5-20250929"):
        self._client = anthropic.AsyncAnthropic()
        self._model = model

    async def synthesize_deferred(self, path: Path) -> str:
        """Read deferred.md, synthesize via LLM, write back."""
        content = path.read_text()
        if not content.strip():
            return content
        result = await self._call_llm(DEFERRED_SYNTHESIS_PROMPT, content)
        path.write_text(result)
        return result

    async def synthesize_postmortem(self, path: Path) -> str:
        """Read postmortem.md, synthesize via LLM, write back."""
        content = path.read_text()
        if not content.strip():
            return content
        result = await self._call_llm(POSTMORTEM_SYNTHESIS_PROMPT, content)
        path.write_text(result)
        return result

    async def _call_llm(self, system_prompt: str, content: str) -> str:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": content}],
        )
        return response.content[0].text


class MockSynthesizer:
    """Test double that passes content through unchanged or applies a transform."""

    def __init__(self, transform: Callable[[str], str] | None = None):
        self._transform = transform or (lambda x: x)
        self.call_count = 0

    async def synthesize_deferred(self, path: Path) -> str:
        self.call_count += 1
        content = path.read_text()
        result = self._transform(content)
        path.write_text(result)
        return result

    async def synthesize_postmortem(self, path: Path) -> str:
        self.call_count += 1
        content = path.read_text()
        result = self._transform(content)
        path.write_text(result)
        return result
