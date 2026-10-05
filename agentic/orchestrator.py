#!/usr/bin/env python3
"""Cashmire agentic workflow orchestrator.

Wires the three specialized agents documented under `.github/agents/`
(Product & Architecture, Full-Stack Development, QA & Security) into a
single Claude Agent SDK run that follows the project's development cycle:

    Understand -> Plan -> Delegate -> Verify -> Review

Usage:
    pip install -r agentic/requirements.txt
    export ANTHROPIC_API_KEY=sk-...
    python agentic/orchestrator.py "Add a monthly budget warning banner"

The three agents are *not* redefined in this file. This script parses the
same `.github/agents/*.md` files that document the team's custom agents for
the project rubric, so each agent's prompt, scope and tool allowlist is
written down in exactly one place. Edit the `.md` files to change agent
behavior; this script only wires them together.

A note on API stability: the Claude Agent SDK's parameter names - notably
the tool used by the orchestrator to spawn subagents, called "Agent" in
current SDK versions and "Task" in older ones - have changed between
releases. If this script errors on an unrecognized field or tool name,
check the installed `claude_agent_sdk` version against
https://docs.claude.com (Agent SDK -> Python reference) before assuming the
orchestration logic itself is wrong.
"""

from __future__ import annotations

import argparse
import asyncio
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, query

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = REPO_ROOT / ".github" / "agents"
SPEC_FILE = "SPEC.md"
REVIEW_FILE = "REVIEW.md"

# Maps the orchestrator's internal subagent key to the `.github/agents/*.md`
# file that is the single source of truth for its prompt/scope/tools.
AGENT_FILES = {
    "architect": "product-architecture.md",
    "developer": "fullstack-development.md",
    "qa_security": "qa-security.md",
}

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


@dataclass
class AgentFile:
    name: str
    description: str
    prompt: str
    tools: list[str]
    model: str | None


def load_agent_file(path: Path) -> AgentFile:
    """Parse a `.github/agents/*.md` file into its frontmatter + prompt body."""
    text = path.read_text()
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(f"{path} is missing the expected '---' YAML frontmatter block")

    meta: dict[str, Any] = yaml.safe_load(match.group(1)) or {}
    body = match.group(2).strip()

    return AgentFile(
        name=meta.get("name") or path.stem,
        description=str(meta.get("description") or "").strip(),
        prompt=body,
        tools=list(meta.get("tools") or []),
        model=meta.get("model"),
    )


def load_agents() -> dict[str, AgentDefinition]:
    agents: dict[str, AgentDefinition] = {}
    for key, filename in AGENT_FILES.items():
        path = AGENTS_DIR / filename
        if not path.exists():
            raise FileNotFoundError(
                f"Expected agent definition at {path} - run this from the repo "
                "root, or check .github/agents/ wasn't renamed."
            )
        agent_file = load_agent_file(path)

        kwargs: dict[str, Any] = {
            "description": agent_file.description,
            "prompt": agent_file.prompt,
            "tools": agent_file.tools,
        }
        if agent_file.model:
            kwargs["model"] = agent_file.model

        agents[key] = AgentDefinition(**kwargs)
    return agents


def resolve_cli_path(explicit: str | None) -> str | None:
    """Find the `claude` CLI binary the SDK shells out to.

    `shutil.which` relies on PATH, which some process managers (background
    jobs, cron, certain sandboxes) start with a much shorter PATH than an
    interactive login shell. Resolving it once up front and passing it to
    `ClaudeAgentOptions.cli_path` avoids the SDK's own PATH lookup failing
    with a bare, hard-to-debug "terminated process" error.
    """
    if explicit:
        return explicit
    return shutil.which("claude")


def build_orchestrator_options(
    cwd: Path, max_turns: int, max_fix_rounds: int, cli_path: str | None = None
) -> ClaudeAgentOptions:
    agents = load_agents()

    system_prompt = f"""You are the orchestrator for the Cashmire agentic development cycle:
Understand -> Plan -> Delegate -> Verify -> Review.

For every task:
1. Ask `architect` to turn the request into a spec written to {SPEC_FILE}.
   Do not proceed until {SPEC_FILE} exists and reads as implementable.
2. Ask `developer` to implement {SPEC_FILE} exactly, with tests alongside
   the code, and to run the relevant test suite itself before reporting back.
3. Ask `qa_security` to review the implementation against {SPEC_FILE} and
   write findings to {REVIEW_FILE}.
4. If {REVIEW_FILE} lists blocking findings, send them back to `developer`
   with the specific findings to fix, then re-run `qa_security`. Repeat
   this step at most {max_fix_rounds} times.
5. Stop and summarize: what was built, what {REVIEW_FILE} says, and
   whether a human still needs to resolve open findings. Never claim the
   feature is "done and safe to merge" - a human review and test run is
   always required before merging, per the project's agentic workflow rules.

Keep every agent inside its documented scope. `architect` never writes
application code. `developer` never edits {REVIEW_FILE} or `.github/agents/`.
`qa_security` never edits application source files."""

    return ClaudeAgentOptions(
        system_prompt=system_prompt,
        agents=agents,
        allowed_tools=["Read", "Agent"],  # "Agent" spawns subagents; was "Task" in older SDK versions.
        permission_mode="acceptEdits",
        cwd=str(cwd),
        max_turns=max_turns,
        cli_path=resolve_cli_path(cli_path),
    )


async def run(task: str, cwd: Path, max_turns: int, max_fix_rounds: int, cli_path: str | None = None) -> None:
    options = build_orchestrator_options(
        cwd=cwd, max_turns=max_turns, max_fix_rounds=max_fix_rounds, cli_path=cli_path
    )
    async for message in query(prompt=task, options=options):
        print(message)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("task", help="Feature or change request to run through the agentic cycle.")
    parser.add_argument(
        "--cwd",
        default=str(REPO_ROOT),
        help="Working directory the subagents operate in (default: repo root).",
    )
    parser.add_argument("--max-turns", type=int, default=40, help="Safety cap on orchestrator turns.")
    parser.add_argument(
        "--max-fix-rounds",
        type=int,
        default=3,
        help="Max developer <-> qa_security fix rounds before stopping.",
    )
    parser.add_argument(
        "--cli-path",
        default=None,
        help="Absolute path to the `claude` CLI binary. Auto-detected via PATH if omitted; "
        "set this explicitly if the SDK reports a 'terminated process' error, which usually "
        "means PATH wasn't resolved in the environment this script is running in.",
    )
    args = parser.parse_args()

    asyncio.run(run(args.task, Path(args.cwd), args.max_turns, args.max_fix_rounds, args.cli_path))


if __name__ == "__main__":
    main()
