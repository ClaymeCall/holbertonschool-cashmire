# Agentic development log

Lightweight record of meaningful agent-assisted work on Cashmire, per the
project's agentic workflow requirement. Each entry covers: the objective,
the agent/role used, what was delegated, the agent's main proposal, how the
team verified it, what was accepted/modified/rejected, and the final
decision.

---

## 2026-10-05 — Set up the three custom agents and the SDK orchestrator

**Objective.** Closes #9, #10, #11. The project requires at least three
specialized custom agents under `.github/agents/` (Product & Architecture,
Full-Stack Development, QA & Security) with defined responsibilities,
scope, constraints and verification expectations, plus a way to actually
run the Understand → Plan → Delegate → Verify → Review cycle rather than
leaving it as a diagram.

**Agent/role used.** Claude (acting in a combined architect/full-stack
capacity for this meta-task — writing the agents and the tooling that runs
them).

**What was delegated.** Write the three `.github/agents/*.md` definitions
tailored to Cashmire's actual stack (Django + DRF, SvelteKit, PostgreSQL,
Decimal money handling, ownership-scoped queries), and a Python
orchestrator (`agentic/orchestrator.py`) built on the Claude Agent SDK that
parses those same `.md` files into `AgentDefinition`s instead of
duplicating each agent's prompt in a second place.

**Main proposal.** Single source of truth: the `.md` files under
`.github/agents/` are both the human-readable documentation the course
rubric asks for *and* the only place each agent's prompt/scope/tools are
written. The orchestrator reads YAML frontmatter (`name`, `description`,
`tools`, `model`) plus the markdown body as the system prompt, then wires
the three agents into one `ClaudeAgentOptions` run with `SPEC.md` /
`REVIEW.md` as the handoff artifacts between them, capped at a configurable
number of fix rounds (default 3).

**How the team verified it.**
- Read each `.github/agents/*.md` file against the three linked issues'
  acceptance criteria (responsibilities, scope, constraints, expected
  outputs, verification expectations all present).
- Syntax-checked `orchestrator.py` with `python3 -m py_compile`.
- Unit-tested the frontmatter-parsing regex directly against all three
  `.md` files to confirm the YAML block and prompt body are extracted
  correctly.
- Could **not** run a live end-to-end orchestrator call in this session —
  the sandbox has no `pip`/`claude-agent-sdk` installed and no
  `ANTHROPIC_API_KEY` configured. This is flagged explicitly rather than
  claimed as tested: **before relying on this script, run it once against
  a throwaway branch and confirm `SPEC.md`/`REVIEW.md` come out as
  expected.**

**Accepted / modified / rejected.**
- Accepted: the single-source-of-truth design (parse `.md` files instead of
  redefining agents inline in Python), since it avoids the two definitions
  drifting apart.
- Modified from the original sketch: added explicit scope/constraint
  sections per agent beyond a one-line prompt, because the issues required
  "clear responsibility, scope, constraints and expected behavior" — a bare
  prompt string wasn't enough to satisfy that.
- Rejected: hardcoding dated model IDs (e.g. a specific `claude-sonnet-5`
  version string) in the agent frontmatter, in favor of the SDK's model
  aliases (`opus`/`sonnet`/`haiku`), to avoid the config going stale as
  models are retired.

**Final decision.** Ship the three `.md` files and the orchestrator as-is,
with the untested-live-run limitation documented here and in
`agentic/README.md`. Whoever first runs `agentic/orchestrator.py` for a real
feature should update this log with what the live run actually did.
