#!/usr/bin/env python3
"""Langfuse tracing for the orchestrator's agentic cycle.

The Claude Agent SDK's `query()` yields a flat stream of messages; this
module reconstructs the orchestrator's actual call tree from it and sends
that tree to Langfuse as a single trace:

    agentic-cycle (root span)       <- tagged with slug, user_id, session_id
    +-- agent: architect        (one "Agent" tool call)
    |   +-- tool: Write          (SPEC.md)
    |   +-- assistant (model)    (a turn's text/tool-call summary + usage)
    +-- agent: developer
    |   +-- tool: Edit
    |   +-- ...
    +-- agent: qa_security
        +-- ...

Nesting is derived from two things the SDK already gives us:
  - `ToolUseBlock.id` / `ToolResultBlock.tool_use_id` pair up a tool call
    with its result, so a span can be opened on the call and closed on the
    result.
  - `parent_tool_use_id` on assistant/user messages says which tool call
    (an "Agent" invocation, in this orchestrator) produced that message, so
    its spans nest under the right agent instead of all landing flat under
    the root.

Every span in the trace is also tagged with the feature `slug` and
attributed to a `user_id` (see `resolve_user_id`), so Langfuse's cost/usage
dashboards can be filtered or grouped per feature and per team member - see
`propagate_attributes` in `start()`.

Requires no setup to be safe to import and call unconditionally: the
underlying `langfuse.get_client()` returns a client that no-ops if
`LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` aren't set, so this module is a
silent no-op in that case rather than an error.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)
from langfuse import get_client, propagate_attributes

# App-level env var (not a Langfuse-defined one) for overriding the resolved
# user_id without touching git config - e.g. in CI, where there's no personal
# git identity to read.
USER_ID_ENV_VAR = "LANGFUSE_USER_ID"


def _git_config(cwd: Path, key: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(cwd), "config", "--get", key],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    value = completed.stdout.strip()
    return value or None


def resolve_user_id(cwd: Path, explicit: str | None = None) -> str | None:
    """Resolve the Langfuse `user_id` to attribute a run to.

    Precedence: an explicit override (e.g. a `--actor` CLI flag), then the
    `LANGFUSE_USER_ID` env var, then the local git identity (`user.email`,
    falling back to `user.name`) for the repo at `cwd`. This makes per-team-
    member attribution zero-config for anyone who already has
    `git config user.email` set, which every contributor to a git repo does
    - nothing extra to configure locally. Returns `None` (untagged) if none
    of these resolve, e.g. in an environment with no git identity and no env
    var set.
    """
    if explicit:
        return explicit
    env_value = os.environ.get(USER_ID_ENV_VAR)
    if env_value:
        return env_value
    return _git_config(cwd, "user.email") or _git_config(cwd, "user.name")


def _tool_span_name(tool_use: ToolUseBlock) -> str:
    if tool_use.name == "Agent":
        subagent = tool_use.input.get("subagent_type") or "subagent"
        return f"agent: {subagent}"
    return f"tool: {tool_use.name}"


class AgenticTracer:
    """Maps one `orchestrator.run()` call onto a single Langfuse trace."""

    def __init__(self, name: str = "agentic-cycle") -> None:
        self._client = get_client()
        self._name = name
        self._root: Any = None
        self._root_cm: Any = None
        self._propagate_cm: Any = None
        # tool_use_id -> the Langfuse observation opened for that tool call.
        self._open: dict[str, Any] = {}

    def start(
        self,
        task: str,
        *,
        cwd: Path,
        slug: str,
        max_turns: int,
        max_fix_rounds: int,
        actor: str | None = None,
    ) -> None:
        self._root_cm = self._client.start_as_current_observation(
            name=self._name,
            as_type="span",
            input=task,
            metadata={"cwd": str(cwd), "max_turns": max_turns, "max_fix_rounds": max_fix_rounds},
        )
        self._root = self._root_cm.__enter__()

        # Entered immediately inside the root span (not around its creation)
        # so propagate_attributes can stamp user_id/tags on the root span
        # itself, as well as on every child span created afterwards via
        # OTel baggage - see the "Late propagation" note on
        # `propagate_attributes` for why ordering matters here.
        user_id = resolve_user_id(cwd, actor)
        self._propagate_cm = propagate_attributes(
            user_id=user_id,
            session_id=slug,
            tags=["cashmire-agentic", slug],
        )
        self._propagate_cm.__enter__()

    def _parent_context(self, parent_tool_use_id: str | None) -> dict[str, str]:
        parent = self._open.get(parent_tool_use_id) if parent_tool_use_id else None
        target = parent if parent is not None else self._root
        return {"trace_id": self._root.trace_id, "parent_span_id": target.id}

    def handle_message(self, message: Any) -> None:
        if self._root is None:
            return
        if isinstance(message, AssistantMessage):
            self._handle_assistant(message)
        elif isinstance(message, UserMessage):
            self._handle_user(message)

    def _handle_assistant(self, message: AssistantMessage) -> None:
        ctx = self._parent_context(message.parent_tool_use_id)
        text = "".join(b.text for b in message.content if isinstance(b, TextBlock))
        tool_uses = [b for b in message.content if isinstance(b, ToolUseBlock)]

        generation = self._client.start_observation(
            trace_context=ctx,
            name=f"assistant ({message.model})",
            as_type="generation",
            model=message.model,
            output={
                "text": text,
                "tool_calls": [{"name": t.name, "input": t.input} for t in tool_uses],
            },
            usage_details=message.usage or {},
            metadata={"stop_reason": message.stop_reason, "session_id": message.session_id},
        )
        generation.end()

        for tool_use in tool_uses:
            self._open[tool_use.id] = self._client.start_observation(
                trace_context=ctx,
                name=_tool_span_name(tool_use),
                as_type="agent" if tool_use.name == "Agent" else "tool",
                input=tool_use.input,
            )

    def _handle_user(self, message: UserMessage) -> None:
        if not isinstance(message.content, list):
            return
        for block in message.content:
            if not isinstance(block, ToolResultBlock):
                continue
            observation = self._open.pop(block.tool_use_id, None)
            if observation is None:
                continue
            observation.update(output=block.content, level="ERROR" if block.is_error else None)
            observation.end()

    def finish(self, result: ResultMessage | None) -> None:
        if self._root is None:
            return
        if result is not None:
            self._root.update(
                output=result.result,
                metadata={
                    "total_cost_usd": result.total_cost_usd,
                    "num_turns": result.num_turns,
                    "duration_ms": result.duration_ms,
                    "is_error": result.is_error,
                    "model_usage": result.model_usage,
                    "permission_denials": result.permission_denials,
                },
            )
        self._propagate_cm.__exit__(None, None, None)
        self._root_cm.__exit__(None, None, None)
        self._client.flush()
        self._root = None
