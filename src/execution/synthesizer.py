"""LLM-based synthesis for cumulative artifact files."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Callable

DEFERRED_SYNTHESIS_PROMPT = """\
You are synthesizing a project's cumulative deferred-items file.  The input is \
a raw append log where each sprint added its own section.  Your job is to \
produce a **single, deduplicated, thematically grouped** version with \
importance/size/complexity ratings.

Rules:
1. Deduplicate items that refer to the same concept across sprints \
   (e.g. "Production SDK integration" appearing 5 times becomes one item).
2. Group items under thematic headings \
   (e.g. "Production Integration", "Analytics & Metrics", "UI/UX", \
    "Infrastructure & DevOps", "Advanced Features").
3. For each item, include a tag line with three ratings and the originating sprints:
   - **Importance**: 🔴 High, 🟡 Medium, 🟢 Low
   - **Size**: S (small, <1 sprint), M (medium, ~1 sprint), L (large, multi-sprint)
   - **Complexity**: 1 (straightforward), 2 (moderate), 3 (significant design work)
   Format: `- [ ] Item description` on one line, then \
   `  ↳ 🔴 High · M · Complexity 2 · (S01, S03, S05)` indented on the next line.
4. Remove "No deferred items" sections entirely.
5. Within each thematic group, sort items by importance (High first, then Medium, then Low).
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
    """LLM-based synthesis using the claude CLI."""

    def __init__(self, model: str = "sonnet"):
        self._model = model

    async def synthesize_deferred(self, path: Path) -> str:
        """Read deferred.md, synthesize via claude CLI, write back."""
        content = path.read_text()
        if not content.strip():
            return content
        result = await self._call_claude(DEFERRED_SYNTHESIS_PROMPT, content)
        path.write_text(result)
        return result

    async def synthesize_postmortem(self, path: Path) -> str:
        """Read postmortem.md, synthesize via claude CLI, write back."""
        content = path.read_text()
        if not content.strip():
            return content
        result = await self._call_claude(POSTMORTEM_SYNTHESIS_PROMPT, content)
        path.write_text(result)
        return result

    async def _call_claude(self, system_prompt: str, content: str) -> str:
        import os

        prompt = f"{system_prompt}\n\n---\n\n{content}"
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        proc = await asyncio.create_subprocess_exec(
            "claude",
            "--print",
            "--model", self._model,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await proc.communicate(input=prompt.encode())
        if proc.returncode != 0:
            raise RuntimeError(f"claude CLI failed (exit {proc.returncode}): {stderr.decode()}")
        return stdout.decode().strip()


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
