"""Planning agent — reads sprint spec + codebase and produces planning artifacts.

Acts as the "tech lead" that writes the execution brief before handing work
to implementation agents. Produces 5 structured artifacts: contracts, team_plan,
tdd_strategy, coding_strategy, and context_brief.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from src.agents.execution.types import AgentResult, StepContext
from src.execution.planning_artifacts import ARTIFACT_NAMES, PlanningArtifacts

if TYPE_CHECKING:
    from src.agents.execution.claude_code import ClaudeCodeExecutor

PLANNING_PROMPT_TEMPLATE = """\
You are a senior tech lead planning the implementation of a sprint.

## Sprint
- **Goal**: {goal}
- **Epic**: {epic_title} — {epic_description}
{tasks_section}
{deliverables_section}

## Project Context
{project_context}

{deferred_section}
{postmortem_section}

## Your Task

Produce **exactly 5 planning artifacts** as markdown sections. Each section MUST
start with the exact header shown below. Do NOT skip any section.

### CONTRACTS
Define the API shapes, interfaces, data models, and function signatures that
agents will implement. Be specific — include parameter types and return types.

### TEAM_PLAN
Specify agent composition: how many agents, what each does, execution order,
and any parallelism opportunities.

### TDD_STRATEGY
Define what to test, test structure, fixtures, edge cases, and coverage targets.
Reference specific functions/classes from the contracts.

### CODING_STRATEGY
Specify patterns, naming conventions, module structure, error handling approach,
and any existing codebase patterns to follow.

### CONTEXT_BRIEF
Summarize domain knowledge, existing code patterns, gotchas from prior sprints,
and anything agents need to know before starting.
"""


def _build_project_context(project_root: Path) -> str:
    """Scan project structure and key files for context."""
    lines = []

    # Project structure (top-level dirs)
    if project_root.exists():
        dirs = sorted(
            d.name for d in project_root.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )
        if dirs:
            lines.append("### Directory Structure")
            lines.append("```")
            for d in dirs[:20]:
                lines.append(f"  {d}/")
            lines.append("```")

    # Key config files
    for config_name in ["pyproject.toml", "setup.py", "setup.cfg"]:
        config_path = project_root / config_name
        if config_path.exists():
            try:
                content = config_path.read_text()[:500]
                lines.append(f"\n### {config_name} (excerpt)")
                lines.append(f"```\n{content}\n```")
            except OSError:
                pass

    return "\n".join(lines) if lines else "(no project context available)"


def _parse_artifacts(output: str) -> PlanningArtifacts:
    """Parse the 5 planning artifacts from agent output."""
    sections = {name: "" for name in ARTIFACT_NAMES}

    # Map headers to field names
    header_map = {
        "CONTRACTS": "contracts",
        "TEAM_PLAN": "team_plan",
        "TDD_STRATEGY": "tdd_strategy",
        "CODING_STRATEGY": "coding_strategy",
        "CONTEXT_BRIEF": "context_brief",
    }

    current_field = None
    current_lines: list[str] = []

    for line in output.split("\n"):
        stripped = line.strip().lstrip("#").strip()
        if stripped in header_map:
            # Save previous section
            if current_field is not None:
                sections[current_field] = "\n".join(current_lines).strip()
            current_field = header_map[stripped]
            current_lines = []
        elif current_field is not None:
            current_lines.append(line)

    # Save last section
    if current_field is not None:
        sections[current_field] = "\n".join(current_lines).strip()

    return PlanningArtifacts(**sections)


class PlanningAgent:
    """Execution agent that produces planning artifacts for a sprint."""

    name: str = "planning_agent"
    description: str = "Reads sprint spec and codebase, produces planning artifacts"

    ALLOWED_TOOLS = [
        "Read", "Glob", "Grep",
    ]

    def __init__(
        self,
        executor: ClaudeCodeExecutor | None = None,
    ) -> None:
        self._executor = executor

    async def execute(self, context: StepContext) -> AgentResult:
        prompt = self._build_prompt(context)
        try:
            result = await self._run(prompt, context.project_root)
            # Parse artifacts from output
            artifacts = _parse_artifacts(result.output)
            missing = artifacts.missing()

            if missing:
                return AgentResult(
                    success=False,
                    output=f"Planning incomplete — missing artifacts: {', '.join(missing)}",
                    deferred_items=[f"Missing planning artifact: {m}" for m in missing],
                )

            # Write artifacts to sprint folder
            sprint_dir = self._find_sprint_dir(context)
            if sprint_dir:
                files = artifacts.write_to_dir(sprint_dir)
                result.files_created = [str(f) for f in files]

            result.output = f"Planning complete. Produced {len(ARTIFACT_NAMES)} artifacts."
            return result

        except Exception as e:
            return AgentResult(
                success=False,
                output=f"Planning agent failed: {e}",
            )

    def _build_prompt(self, context: StepContext) -> str:
        """Build the planning prompt from sprint context."""
        tasks_section = ""
        if context.sprint.tasks:
            task_lines = [f"- {t.get('name', t)}" for t in context.sprint.tasks]
            tasks_section = f"**Tasks**:\n" + "\n".join(task_lines)

        deliverables_section = ""
        if context.sprint.deliverables:
            deliverables_section = f"**Deliverables**: {', '.join(context.sprint.deliverables)}"

        deferred_section = ""
        if context.cumulative_deferred:
            deferred_section = (
                "## Deferred Items (from prior sprints)\n"
                f"{context.cumulative_deferred}"
            )

        postmortem_section = ""
        if context.cumulative_postmortem:
            postmortem_section = (
                "## Lessons Learned (from prior sprints)\n"
                f"{context.cumulative_postmortem}"
            )

        project_context = _build_project_context(context.project_root)

        return PLANNING_PROMPT_TEMPLATE.format(
            goal=context.sprint.goal,
            epic_title=context.epic.title,
            epic_description=context.epic.description,
            tasks_section=tasks_section,
            deliverables_section=deliverables_section,
            project_context=project_context,
            deferred_section=deferred_section,
            postmortem_section=postmortem_section,
        )

    def _find_sprint_dir(self, context: StepContext) -> Path | None:
        """Find the sprint's artifact directory."""
        # Look for the sprint folder in the kanban structure
        kanban_dir = context.project_root / "kanban"
        if not kanban_dir.exists():
            return None
        import re
        num_match = re.search(r"(\d+)", context.sprint.id)
        if not num_match:
            return None
        num = int(num_match.group(1))
        pattern = f"**/sprint-{num:02d}_*"
        for match in kanban_dir.glob(pattern):
            if match.is_dir() and not match.name.endswith(".md"):
                return match
        return None

    async def _run(self, prompt: str, project_root: Path) -> AgentResult:
        """Run via ClaudeCodeExecutor."""
        if self._executor is None:
            raise RuntimeError(
                "No ClaudeCodeExecutor provided. "
                "Pass executor= to the constructor for real execution."
            )
        return await self._executor.run(
            prompt=prompt,
            working_dir=project_root,
            allowed_tools=self.ALLOWED_TOOLS,
        )
