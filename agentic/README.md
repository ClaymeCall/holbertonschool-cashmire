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

## Running the cycle

```bash
python agentic/orchestrator.py "Add a monthly budget warning banner"
```

This runs, in order:

1. **architect** (`product-architecture.md`) writes `SPEC.md` for the
   request. Nothing proceeds until a human-readable spec exists.
2. **developer** (`fullstack-development.md`) implements `SPEC.md` across
   `backend/` and `frontend/`, with tests, and runs the test suite.
3. **qa_security** (`qa-security.md`) reviews the implementation against
   `SPEC.md` and writes findings to `REVIEW.md`, without editing source.
4. If `REVIEW.md` has blocking findings, `developer` fixes them and
   `qa_security` re-reviews — up to `--max-fix-rounds` times (default 3).

`SPEC.md` and `REVIEW.md` are the handoff artifacts between agents: each
subagent starts with a clean context window, so passing state through files
is more reliable than relying on conversation history.

Useful flags:

```bash
python agentic/orchestrator.py "<task>" --max-turns 60 --max-fix-rounds 2
```

## What this does not replace

Per the project's agentic workflow rules: an agent run is not proof a
feature works. A human still reads the diff, runs the tests themselves, and
decides whether to merge — this script automates delegation, not
accountability. Log meaningful runs in `docs/agentic-log.md`.
