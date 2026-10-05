# Cashmire agentic workflow

This directory runs the three specialized agents required by the project
brief — Product & Architecture, Full-Stack Development, QA & Security —
through the [Claude Agent SDK](https://docs.claude.com), using one
orchestrator script.

The agents themselves are **not** defined here. Their prompts, scope and
tool allowlists live in `.github/agents/*.md` (the same files the course
rubric requires); `orchestrator.py` only parses those files and wires them
into a single run. Edit the `.md` files to change what an agent does.

## Setup

```bash
pip install -r agentic/requirements.txt
export ANTHROPIC_API_KEY=sk-...   # see .env.example
```

### Optional: Langfuse tracing

Set `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` (and `LANGFUSE_HOST` if
self-hosting; see `.env.example`) to send every run to Langfuse as one
trace: a root span for the cycle, an `agent` span per `architect`/
`developer`/`qa_security` delegation, and nested `tool`/`generation` spans
for what each subagent actually did, with per-turn token usage and cost.
`agentic/tracing.py` does this by correlating `ToolUseBlock`/
`ToolResultBlock` pairs and `parent_tool_use_id` from the SDK's message
stream - it isn't a separate wrapper you need to configure. Leave the two
keys unset to run without tracing; `langfuse.get_client()` no-ops in that
case rather than erroring.

## Running the cycle

```bash
python agentic/orchestrator.py "Add a monthly budget warning banner" --slug issue-42-budget-warning
```

Always pass `--slug` tied to the issue (e.g. `issue-<number>-<short-name>`).
Each run gets its own `docs/specs/<slug>.md` and `docs/reviews/<slug>.md` —
**never** a shared `SPEC.md`/`REVIEW.md` at the repo root, which a second
feature would silently overwrite or collide with mid-review. If you omit
`--slug`, one is derived from the first few words of the task and printed
before the run starts; check it before a long run if the name matters. The
script refuses to run if the slug's spec or review file already exists,
rather than silently clobbering a previous feature's record.

This runs, in order:

1. **architect** (`product-architecture.md`) writes `docs/specs/<slug>.md`
   for the request. Nothing proceeds until a human-readable spec exists.
2. **developer** (`fullstack-development.md`) implements it across
   `backend/` and `frontend/`, with tests, and runs the test suite.
3. **qa_security** (`qa-security.md`) reviews the implementation against
   the spec and writes findings to `docs/reviews/<slug>.md`, without
   editing source.
4. If the review has blocking findings, `developer` fixes them and
   `qa_security` re-reviews — up to `--max-fix-rounds` times (default 3).

The spec and review files are the handoff artifacts between agents: each
subagent starts with a clean context window, so passing state through files
is more reliable than relying on conversation history. Unlike `SPEC.md`
and `REVIEW.md` in earlier drafts of this script, they are kept permanently
under `docs/` as a per-feature audit trail, the same way `docs/decisions/`
keeps architecture decision records — not deleted after merge.

Useful flags:

```bash
python agentic/orchestrator.py "<task>" --slug issue-42-budget-warning --max-turns 60 --max-fix-rounds 2
```

## What this does not replace

Per the project's agentic workflow rules: an agent run is not proof a
feature works. A human still reads the diff, runs the tests themselves, and
decides whether to merge — this script automates delegation, not
accountability. Log meaningful runs in `docs/agentic-log.md`.
