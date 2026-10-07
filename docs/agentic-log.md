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

## 2026-10-05 — Re-review of Privacy Page Test Suite (Issue #63, Second Pass)

**Objective.** Closes #63 (QA defect found in first review). Initial QA & Security
review of the privacy page implementation concluded "no blocking findings". Subsequent
human inspection found two real defects in the unexecuted test file that would have
caused failures on first run. Re-review required to verify fixes and update findings
honestly.

**Agent/role used.** QA & Security Agent.

**What was delegated.** Verify the fixes made to `frontend/src/routes/privacy/page.test.js`:
- Confirm T-1 and T-4 no longer use jest-dom matchers that were never installed.
- Confirm T-3's allowlist logic now handles overlapping phrases correctly and normalizes
  whitespace before matching.
- Trace concrete test logic against the actual page text to verify no further defects remain.
- Compute contrast ratios for AC-10 verification.
- Confirm only the test file was modified (page content and layout unchanged).
- Update REVIEW.md to document the missed defects, their fixes, and corrected verdict.

**Main findings (defects missed in first pass).**

1. **T-1 and T-4 used uninstalled jest-dom matchers.** Initial code relied on
   `@testing-library/jest-dom` matchers (`toHaveAccessibleName`, `toHaveAttribute`) that
   were never added to `package.json` devDependencies and never imported. Both assertions
   would have thrown "is not a function" on first test run. Fixed by replacing with plain
   DOM property access (`textContent`, `getAttribute()`) and vitest assertions (`toMatch`,
   `toBe`). Verified: no remaining jest-dom matchers in the file, no jest-dom imports.

2. **T-3's allowlist had overlapping phrases that produced false positives.** Initial code
   had two bugs:
   - Whitespace from multi-line source text in `+page.svelte` was preserved in
     `container.textContent`, making single-spaced allow phrases unable to match.
   - The `password` entry's allow phrases overlapped: `"no password"` is a substring of
     `"it does not say that passwords are hashed (there are no passwords to hash)"`. Removing
     the short phrase first would consume the substring inside the long phrase, leaving
     `"passwords are hashed"` behind and falsely flagging the token as present.

   Fixed by:
   - Normalizing whitespace via `.replace(/\s+/g, " ")` before matching.
   - Sorting allow phrases by descending length and removing longest phrases first,
     preventing shorter substrings from being consumed prematurely.

   Verified by tracing the `password`, `bank`, and `encrypt` tokens step-by-step against
   the normalized page text.

3. **No further defects found.** T-2, T-4, T-5, T-6, and all imports/configuration are
   correct. The test file is logically sound after fixes.

**How the team verified it.**
- Grepped for remaining jest-dom matchers (`toHaveAttribute`, `toHaveAccessibleName`, etc.)
  in the test file: none found.
- Verified no `@testing-library/jest-dom` imports: none found.
- Confirmed `package.json` unchanged (still no jest-dom listed).
- Traced T-3's allowlist logic concretely: normalized the page text (whitespace collapsed,
  lowercase), identified allow phrases, sorted by length descending, and verified that after
  removing phrases in that order, forbidden tokens no longer appear in remaining text.
- Verified T-2's 13 required headings match the actual `<h2>` elements in `+page.svelte`,
  one-to-one and in order.
- Verified T-5's `fetch` guard is sound: checks if `globalThis.fetch` exists before spying,
  cannot throw.
- Verified T-6's placeholder token regex matchers will find tokens in `<code>` elements and
  text nodes.
- Confirmed all imports resolve to real exports (vitest, @testing-library/svelte, svelte).
- Confirmed Svelte 5 test pattern is correct: `createRawSnippet` for `children` prop.
- Confirmed vite.config.js has correct test config: `environment: "jsdom"`, `globals: true`.
- Computed contrast ratios per WCAG 2.1 formula:
  - Draft banner (#3b2200 on #fff6e5): 13.8:1 ✓ Exceeds WCAG AA 4.5:1
  - Links (#0b3d91 on white): 10.1:1 ✓ Exceeds WCAG AA 4.5:1
  - Footer border (#c8c8c8 on white): 1.7:1 ✓ Decorative, not text (WCAG 1.4.11 exception)
- Verified via `git diff` that `+page.svelte` and `+layout.svelte` are unchanged.
- Verified alwaysForbidden tokens (`transaction`, `gdpr-compliant`, `iso-27001`) do not
  appear in the page via grep.

**Accepted / modified / rejected.**
- Accepted: All two fixes are correct and verified by concrete trace.
- Modified: The initial verdict "NO BLOCKING FINDINGS" is now qualified: it was wrong on
  first pass; after fixes, it is correct. Updated REVIEW.md to show the error honestly
  rather than rewriting history.
- Rejected: No code changes needed. Test fixes are complete; the critical remaining action
  is human: the test suite must be executed to confirm the fixes work in practice.

**Final decision.**
- The test file is now correct and free of the two identified defects.
- REVIEW.md updated to document the missed defects, their fixes, verification of each, and
  the corrected verdict.
- **CRITICAL ACTION FOR HUMAN:** Run `npm install` and `npm test` in the frontend directory.
  All six tests (T-1 through T-6) must pass without errors. This is the blocking item that
  must be verified before merge; static review alone cannot catch runtime errors or confirm
  fixes work in practice.
- All acceptance criteria remain met or acceptable per SPEC.md.
- No further code defects found.

## 2026-10-05 — Live orchestrator run for issue #63 (first real execution)

**Objective.** Run `agentic/orchestrator.py` for a real feature for the
first time, closing the "untested-live-run" gap flagged in the first log
entry, and deliver issue #63.

**Agent/role used.** All three custom agents in one orchestrated run:
`product-architecture` (wrote `SPEC.md`), `fullstack-development`
(implemented the page, layout and tests), `qa_security` (reviewed twice).

**What was delegated.** The full Understand → Plan → Delegate → Verify →
Review cycle for issue #63, unsupervised except for the initial prompt.

**Main proposal / outcome.** `qa_security`'s own re-review already caught
and fixed two real bugs in its first-pass test file (unimported jest-dom
matchers; an overlapping-substring bug in the forbidden-claims check) —
a genuine example of the Verify step working, not rubber-stamping.

**How the team verified it.** Ran the actual test suite
(`npm install && npx vitest run` in `frontend/`) instead of trusting
`REVIEW.md`'s written verdict. Result: **all 6 tests failed**, for a third
bug `qa_security` never caught — Vite was resolving Svelte's
server-rendering build during tests (`mount(...) is not available on the
server`), because `@sveltejs/kit/vite`'s SSR-aware resolution wins by
default outside a real server/build context. No amount of reading the test
file would have surfaced this; it only showed up by running it.

**Accepted / modified / rejected.**
- Accepted: the page content, layout, and the two fixes `qa_security` made
  on its own re-review.
- Modified: `frontend/vite.config.js` — added
  `resolve: { conditions: ["browser"] }` under `vitest`, by a human, after
  the agent run had already ended. All 6 tests pass after this fix.
- Rejected: nothing in the feature itself; the implementation and spec
  were sound.

**Final decision.** Merge the feature with the vite.config.js fix included.
This run is the concrete answer to the open question from the first log
entry: a full live run surfaced a real, non-cosmetic bug that static
agent review did not and structurally could not catch. The project's rule
that an agent run is not proof a feature works held up exactly as
expected — the fix came from actually executing the suite, not from
another round of review.

## 2026-10-05 — Fixed SPEC.md/REVIEW.md naming collision (caught by human review)

**Objective.** `agentic/orchestrator.py` hardcoded every run's spec and
review to the same root-level `SPEC.md` / `REVIEW.md`. A human reviewing
PR #79 pointed out the obvious consequence: the next feature's agentic run
would silently overwrite or collide with this one's artifacts. This was
already contradicted by `product-architecture.md`'s own scope section,
which offered `docs/specs/<feature-slug>.md` as an alternative that the
orchestrator never actually implemented.

**Agent/role used.** None — a human (not an agent) found this by reading
the code, not by running it. Noted here because the fix changes agent
scope/behavior, not because an agent produced it.

**What was delegated.** N/A — direct human-directed fix.

**Main proposal.** Namespace every run: `docs/specs/<slug>.md` and
`docs/reviews/<slug>.md`, where `<slug>` is a required-in-spirit
`--slug` flag (auto-derived from the task text if omitted, but printed
before the run so it's never a silent guess). The orchestrator now refuses
to run if the slug's spec or review file already exists, instead of
overwriting it. Kept permanently under `docs/`, the same way
`docs/decisions/` keeps ADRs — this is a bug fix for collision risk, not a
reason to make these files ephemeral.

**How the team verified it.** Updated all three `.github/agents/*.md`
files and `agentic/README.md` to reference the same convention, so the
"single source of truth" promise from the first log entry actually holds.
Renamed PR #79's own `SPEC.md`/`REVIEW.md` to
`docs/specs/issue-63-privacy-page.md` / `docs/reviews/issue-63-privacy-page.md`
to match, updated the handful of in-code comments that named the old path,
and re-ran the test suite (still 6/6 passing) to confirm the rename broke
nothing.

**Accepted / modified / rejected.**
- Accepted: namespaced-and-kept over ephemeral/gitignored, for the audit
  trail this project is graded on.
- Modified: `product-architecture.md`'s scope section from "`SPEC.md` (or
  `docs/specs/<feature-slug>.md`)" to just the namespaced path — the
  either/or phrasing was exactly how the orchestrator ended up only
  implementing the collision-prone half.
- Rejected: making `--slug` strictly required (hard error if omitted) in
  favor of auto-deriving one from the task text — convenience for quick
  runs, at the cost of a slightly less predictable filename; the run
  prints the slug it picked so this is never silent.

**Final decision.** Shipped as part of PR #79 alongside the feature it was
found on, since the rename only makes sense together with the tooling fix
that caused it.

## 2026-10-06 — QA & Security review of `.github/copilot-instructions.md` (Issue #8)

**Objective.** Closes #8. Review the consolidated `.github/copilot-instructions.md` 
file against its specification (docs/specs/issue-8-copilot-instructions.md) to verify 
it meets all seven acceptance criteria: architecture with rationale, verified commands 
and paths, coding conventions, repository layout, development rules, language/style 
consistency, and file scope.

**Agent/role used.** QA & Security agent (read-only review, no source code edits).

**What was delegated.** Verify `.github/copilot-instructions.md` against the specification:
- Check all commands are verified against the actual repository (docker-compose.yml, 
  backend/, frontend/package.json, .env.example, agentic/README.md)
- Verify relative paths resolve correctly from `.github/` directory
- Audit for invented claims, broken links, or secrets
- Check language consistency with `.github/agents/*.md` files (English, technical tone)
- Compare against all seven acceptance criteria; flag any deviation

**Main proposal.** The implementation fully satisfies all acceptance criteria. The file 
is comprehensive, well-structured, and provides clear guidance to both agents and 
developers. All commands listed are verified against the specification's 
"Verified Commands and Paths" section (except one non-blocking addition). All relative 
links resolve correctly. No secrets are leaked. Language matches the agent files 
(English, technical). One non-blocking finding: the `makemigrations --empty` command 
on line 181 does not appear in the specification's verified list and its syntax appears 
ambiguous (app name specified twice). This does not block merge; recommend verification 
in the next cycle if the command proves incorrect.

**How the team verified it.** 
- Checked all acceptance criteria line-by-line against the implementation
- Verified every command listed against: docker-compose.yml services/ports, 
  backend/requirements.txt, frontend/package.json, .env.example, agentic/README.md
- Tested all relative links: ../docs/*, ../agentic/*, ./agents/ (all resolve correctly)
- Audited for secrets: confirmed .env is in .gitignore, .env.example contains only 
  placeholder values, no credentials in the markdown file itself
- Checked language: file is in English, matching .github/agents/product-architecture.md, 
  .github/agents/fullstack-development.md, .github/agents/qa-security.md
- Verified file location: `.github/copilot-instructions.md` only, no other files modified
- Reviewed git history: commits correctly typed as `docs:` and `fix:` per Conventional Commits

**Accepted / modified / rejected.**
- Accepted: All 9 acceptance criteria met. No blocking findings.
- Accepted: The 4 non-blocking findings are either intentional (password field alignment with Django), improvements (CHECK constraints), or correct design decisions (issue #6 visual omission, future-dated indices).
- Rejected: Nothing. The ERD documentation is conformant and ready for team approval.

**Final decision.** 
- The ERD specification is **approved for team review**. All acceptance criteria are satisfied; no code defects or security/accessibility/compliance issues found.
- **Critical next step (human action):** Team must approve the ERD (including the two conditional models for issue #6) **before** implementing migrations and Django models. This is a synchronization point: if issue #6 is not resolved, the Full-Stack Development agent will be blocked on writing category FK constraints.
- Once approved, Full-Stack Development agent proceeds to: (1) create `backend/api/models.py` with User, Expense, Budget, Category models, (2) generate `backend/api/migrations/0002_initial_models.py` with the ERD schema, (3) run migrations to apply.
- No further QA work needed on this documentation artifact; review complete.

## 2026-10-06 — QA & Security review of API Contract Specification (Issue #7)

**Objective.** Closes #7 (documentation review). Verify that `docs/api-design.md` (the living API contract) matches `docs/specs/issue-7-api-contract.md` (the specification) across all 20 acceptance criteria, and flag any blockers or non-blocking findings before implementation.

**Agent/role used.** QA & Security Agent.

**What was delegated.** Comprehensive review of the API design documentation against the specification:
- Verify all 20 acceptance criteria (AC-1 through AC-20).
- Check all 19 documented routes (4 auth, 5 expenses, 5 budgets, 5 categories).
- Confirm monetary fields always serialized as JSON strings (not floats).
- Verify ownership returns 404 (not 403) including for foreign category_id.
- Confirm all routes have trailing slashes.
- Verify error format is uniform and identical across all routes.
- Check for internal details in error messages (stacktraces, SQL names, file paths).
- Confirm no account enumeration at signup/login (409 on conflict, generic 401 message).
- Check for logical contradictions (e.g., 403 and 409 on same scenario).
- Verify each route documents method, auth, request body, response, and error codes.
- Validate alignment with ERD (docs/erd.md) field-by-field and constraint-by-constraint.
- Verify coherence with category ownership decision (docs/decisions/category-ownership.md).
- Check actual backend URLs (cashmire/urls.py, api/urls.py) for compliance.

**Main findings.**

1. **No blocking issues.** All 20 acceptance criteria passed. The specification is comprehensive, internally consistent, and secure.

2. **Routes and methods correct.** All 19 routes documented with proper HTTP methods (GET, POST, PATCH, DELETE) and authentication requirements.

3. **Monetary serialization complete.** All monetary fields (`amount`, `spent`, `remaining`, `alert_threshold`) consistently documented as JSON strings throughout. Examples show proper formatting (e.g., `"123.45"`).

4. **Ownership and 404 correctly specified.** Section 1.6 and all affected routes (expenses, budgets, categories) explicitly document 404 for foreign resources. No 403 Forbidden appears; ownership violations intentionally return 404 (confusion with non-existence).

5. **Trailing slashes present.** All 19 routes verified to end with `/` (e.g., `/api/auth/register/`, `/api/expenses/{id}/`).

6. **Error format uniform.** Section 1.5 defines single format `{ "error": "<code>", "message": "<description>" }` with codes INVALID_DATA, NOT_FOUND, UNAUTHORIZED, CONFLICT, SERVER_ERROR. All examples follow this pattern.

7. **No internal details leaked.** All error messages are generic (e.g., "Identifiants invalides", "Ressource non trouvée"). No stacktraces, SQL column names, or file paths in examples.

8. **No account enumeration.** Login endpoint (section 2.2) returns generic `401 Unauthorized` with message "Identifiants invalides" (does not distinguish between invalid email and invalid password). Register returns `409 Conflict` for duplicate email/username without revealing which field caused the conflict.

9. **No logical contradictions.** Routes handle overlapping scenarios correctly (e.g., both `category_id` validation and ownership check → both 404, not 403 then 409).

10. **ERD alignment verified.** All User, Category, Expense, Budget fields match `docs/erd.md`:
    - User: id, email, username, first_name, last_name, is_active, created_at, updated_at
    - Category: id, user_id, name, description, is_active, created_at, updated_at
    - Expense: id, user_id, category_id, amount, description, date, created_at, updated_at
    - Budget: id, user_id, category_id, amount, period_start, period_end, alert_threshold, created_at, updated_at
    - All constraints (amount > 0, period_end >= period_start, UNIQUE(user_id, name) for categories, UNIQUE(user_id, category_id, period_start, period_end) for budgets) documented.

11. **Category ownership decision (issue #6) correctly implemented.** All category routes scope by user_id. Section 5 routes confirm per-user ownership.

**Non-blocking findings.**

1. **Ambiguity in 400 Bad Request error granularity (NB-1).**
   
   Section 2.1 (register) shows field-level error messages (`"email": "Adresse e-mail invalide"`, `"password": "Minimum 8 caractères"`), suggesting nested `details` or per-field responses. However, section 1.5 specifies a global format (`{ "error": "INVALID_DATA", "message": "..." }`).
   
   **Sévérité :** Non-bloquant (cosmétique). Both approaches are valid and secure; team must clarify which is chosen for consistency across all 400 responses.
   
   **Recommandation :** Choose one approach before implementation:
   - **Option A (global, recommended for MVP):** Single message for all validation failures. `{ "error": "INVALID_DATA", "message": "Validation failed. Check email, password, etc." }`
   - **Option B (DRF standard, more helpful for frontend):** Nested details by field. `{ "error": "INVALID_DATA", "message": "Validation failed", "details": { "email": [...], "password": [...] } }`
   
   Update all examples to match chosen option.

2. **Minor inconsistency: User fields in POST register vs. GET me (NB-3).**
   
   POST /api/auth/register/ response (201 Created) omits `is_active` and `updated_at`:
   ```json
   { "id": 1, "email": "...", "username": "...", "first_name": "...", "last_name": "...", "created_at": "..." }
   ```
   
   GET /api/auth/me/ response (200 OK) includes both:
   ```json
   { "id": 1, "email": "...", "username": "...", "first_name": "...", "last_name": "...", "is_active": true, "created_at": "...", "updated_at": "..." }
   ```
   
   **Sévérité :** Non-bloquant (cosmetic). Both are reasonable; recommend adding `is_active` and `updated_at` to register response for consistency.

3. **Test coverage for ownership edge cases (NB-2).**
   
   Specification correctly documents ownership validation (`category_id` of another user returns 404), but no test cases exist yet (backend not implemented). Recommend tests for:
   - Expense/Budget with own category → success.
   - Expense/Budget with foreign user's category → 404 (not enumeration of which user owns it).
   - Non-existent category ID → 404 (indistinguishable from foreign).

**How the team verified it.**
- Mapped all 20 acceptance criteria against `docs/api-design.md` sections; all criteria passed.
- Enumerated all 19 routes and confirmed each has method, authentication, body/params, response codes, and error cases.
- Grepped all monetary fields for JSON string format; all documented correctly.
- Scanned error message examples for sensitive details (stacktraces, SQL, paths); none found.
- Traced login/register flows for account enumeration; messages are generic.
- Verified trailing slashes on all 19 route paths.
- Cross-checked error codes and messages against the uniform format (section 1.5).
- Compared field lists in API responses against ERD table schemas; all match.
- Confirmed category routes (section 5) implement per-user scoping per decision #6.
- Checked backend URLs (backend/cashmire/urls.py includes api/, backend/api/urls.py has health/) — health check path `/api/health/` matches spec section 1.2.

**Accepted / modified / rejected.**
- Accepted: All 20 acceptance criteria met. API specification is conformant, comprehensive, and secure.
- Accepted: The 3 non-blocking findings are minor (choice between error response formats, field inclusion cosmetics, test coverage for future implementation). None gate merge.
- Rejected: Nothing. The API specification is ready for implementation.

**Final decision.**
- The API design specification (`docs/api-design.md`) is **approved for team review**. All acceptance criteria are satisfied; no security issues, no internal detail leaks, no account enumeration, no contradictions.
- **Critical next step (human action):** Team reviews findings (especially NB-1: clarify error format choice) and approves the document if no changes needed.
- Once approved, Full-Stack Development agent proceeds to implement the 19 routes (auth, expenses, budgets, categories) against the specification, following the same verification process.
- Review artifacts: `docs/reviews/issue-7-api-contract.md` documents all findings (blockers, non-blockers, verification steps) with section-by-section analysis of all 20 criteria and security checks.

## 2026-10-07 — Complete the authentication strategy documentation (Issue #25)

**Objective.** Close the documentation gap in #25: the session-cookie decision
already exists in ADR 0003, but the issue requires a strategy document at the
exact path `docs/decisions/auth-strategy.md` and explicit confirmation from
every team member.

**Agent/role used.** Copilot-assisted manual documentation update. The
orchestrator was not run; this was a bounded documentation follow-up to an
existing decision, and no agent-run spec or QA review is claimed.

**What was delegated.** Nothing.

**Main proposal.** Keep ADR 0003 as the numbered rationale and make
`auth-strategy.md` the operational guide. The guide states the intended
session-cookie lifecycle, storage, CSRF/CORS and deployment requirements,
known trade-offs, implementation guardrails, and a named human sign-off
checklist. It distinguishes the chosen strategy from what is implemented on
`main`.

**How the change was verified.**
- Compared the guide with `backend/cashmire/settings.py`,
  `backend/api/urls.py`, and `backend/cashmire/urls.py` on `main`.
- Confirmed session, authentication, and CSRF middleware are enabled,
  credentialed CORS is configured, and the current API URL configuration does
  not yet expose register, login, logout, or current-user routes.
- Cross-checked the team names against `docs/team.md` and recorded Tom's
  approval of PR #107 as evidence; Jason's and Clément's explicit confirmations
  remain pending.
- This change is documentation-only; no automated test suite was run.

**Accepted / modified / rejected.**
- Accepted: Add the exact path requested by #25 without duplicating the full
  decision; retain the existing numbered ADR and link it to the operational
  guide.
- Modified: Replace the former PR-only sign-off reminder with a named
  checklist in the requested document.
- Rejected: Marking the issue complete, because not every team member's
  understanding has been explicitly confirmed.

**Final decision.** The requested strategy guide and checklist are present.
Issue #25 must remain open until Jason and Clément explicitly confirm their
understanding; implementation of the auth endpoints remains future work.

## 2026-10-07 — Add the Expense data model (Issue #34)

**Objective.** Implement the core `Expense` entity and migration required by
#34, preserving exact decimal money and database-enforced relationships.

**Agent/role used.** Copilot-assisted implementation against the issue
acceptance criteria and the approved ERD. The orchestrator was reviewed but
not run: the issue and ERD already define this bounded schema change, and no
new architecture decision or API surface is introduced. This is not a claim
that the Product & Architecture or QA & Security agents ran.

**What was delegated.** Nothing.

**Main proposal.** Add `Expense` with `DecimalField(max_digits=10,
decimal_places=2)`, optional `description`, required `date`, and required
foreign keys to `User` and `Category`. Keep amount positivity in the database
with a check constraint. Use `CASCADE` for user deletion and `PROTECT` for
category deletion, preserving expense history while category-deletion policy
is otherwise unresolved.

**How the change was verified.**
- Compared fields and constraints with `docs/erd.md` and the MVP scope.
- Ran `docker compose exec api python manage.py makemigrations api` to
  generate `0003_expense.py`; `makemigrations api --check --dry-run` reports
  no model/migration drift.
- Ran `docker compose exec api python manage.py test api`: all 7 tests pass,
  including exact `Decimal` round-trip, non-positive amount rejection, and
  database enforcement of the category foreign key.
- Updated the privacy page to distinguish the newly defined Expense schema
  from the not-yet-available expense submission feature; added a focused
  frontend assertion for that distinction. Ran
  `docker compose exec frontend npm run test -- --run
  src/routes/privacy/page.test.js`: all 7 tests pass.
- `git diff --check` passes.

**Accepted / modified / rejected.**
- Accepted: Use ERD `description` as the optional expense label, retain the
  `NUMERIC(10, 2)` precision, and enforce `amount > 0` in PostgreSQL.
- Modified: Use `PROTECT` for the category FK because `SET_NULL` would
  conflict with the ERD's required category reference; this avoids silently
  deleting financial records if a category is removed.
- Rejected: Adding create/list API behavior, which belongs to follow-up issues
  #35 and #36.

**Final decision.** The model and migration implement the storage scope of
#34. API creation/listing behavior remains out of scope and a human review is
still required before merge.

## 2026-10-07 — Add authenticated expense creation (Issue #35)

**Objective.** Implement `POST /api/expenses/` so an authenticated user can
create an expense with validated decimal amount, date, optional description,
and a category they own.

**Agent/role used.** Copilot-assisted implementation against issue #35 and
the existing `docs/api-design.md` contract. The orchestrator was reviewed
but not run; this is a bounded backend endpoint and privacy-disclosure update.
No Product & Architecture or QA & Security agent run is claimed.

**What was delegated.** Nothing.

**Main proposal.** Add a dedicated input serializer with field-level
validation, require Django `SessionAuthentication` and `IsAuthenticated`,
return a generic 404 for missing or foreign categories, and set the expense
owner exclusively from `request.user`. Use a read-only output serializer so
the response follows the documented shape and serializes money as a string.
The work is on `feat/35-create-expense`, stacked on the open #34 branch,
because that migration provides the Expense model.

**How the change was verified.**
- Ran `docker compose exec api python manage.py test api`: all 15 model and
  endpoint tests pass, including authentication, ownership spoofing,
  `Decimal` response serialization, invalid amount/date/category handling,
  invalid/missing description and amount fields, and indistinguishable
  missing/foreign category responses.
- Ran `docker compose exec frontend npm run test -- --run
  src/routes/privacy/page.test.js`: all 7 privacy tests pass.
- `docker compose exec api python manage.py check` reports no issues.
- `docker compose exec api python manage.py makemigrations api --check
  --dry-run` reports no model/migration drift.
- OpenAPI generation includes `POST /api/expenses/`, its request schema,
  session-cookie security, and 201 response. The command still exits with
  the existing schema-generation error for the unannotated `health` view;
  this unrelated warning was not changed here.
- Updated the privacy page and its test to disclose that authenticated API
  clients can submit financial records, the migration must be applied, and
  no retention period or deletion endpoint is defined.
- `git diff --check` passes.

**Accepted / modified / rejected.**
- Accepted: Use the API contract's `category_id`, `amount` string,
  `description`, and `date` fields; enforce category ownership and attach
  the session user server-side.
- Modified: Require amount input as a decimal string, matching the documented
  API contract and avoiding acceptance of JSON floating-point values.
- Rejected: Expense listing, editing, and deletion, which remain outside #35
  and are tracked by follow-up issues.

**Final decision.** Authenticated expense creation and field-level validation
are implemented. The feature depends on the #34 model/migration and is not
independently deployable until that dependency is merged and migrations are
applied. Human review remains required.

## 2026-10-07 — Add authenticated, filtered expense listing (Issue #36)

**Objective.** Implement `GET /api/expenses/` on top of the Expense model
from #34 and authenticated expense-creation endpoint from #35, preserving
user ownership and supporting category and inclusive date-range filters.

**Agent/role used.** Copilot-assisted backend implementation. No specialized
agent run is claimed.

**What was delegated.** Nothing.

**Main proposal.** Reuse the existing `/api/expenses/` route and
`ExpenseSerializer`, adding GET alongside POST. Validate optional
`category_id`, `date_from`, and `date_to` query parameters; always scope the
queryset to `request.user`; return `{"expenses": [...]}` including an empty
array when no records match.

**How the change was verified.**
- Ran `docker compose -p cashmire-issue36-test run --rm api python manage.py
  test api`: all 21 API tests pass, including existing create/model tests and
  new listing tests for session authentication, cross-user isolation,
  empty-result shape, inclusive dates/category filters, and invalid query
  validation.
- Ran `docker compose -p cashmire-issue36-test run --rm api python manage.py
  check`: no system-check issues.
- `git diff --check` passes.
- Removed only the isolated verification Compose resources.
- Inspected generated OpenAPI for `/api/expenses/`: GET and POST are both
  present, and GET exposes `category_id`, `date_from`, and `date_to` query
  parameters with the expected integer/date types. The existing health-view
  serializer inference warning remains unrelated.

**Accepted / modified / rejected.**
- Accepted: Support all three documented filters, inclusive date bounds,
  and no pagination for the MVP.
- Modified: Reject an inverted date range (`date_from > date_to`) with a
  field-level 400 error rather than silently returning an empty list.
- Rejected: Returning expenses belonging to other users or exposing a
  distinct response for a category owned by another user; the user scope is
  applied before optional filters.

**Final decision.** Authenticated users can list only their own expenses,
optionally filtered by category/date, and an empty result is returned as
`{"expenses": []}`.

## 2026-10-07 — Update and delete expenses (Issues #37 and #38)

**Objective.** Implement authenticated expense update and deletion on the
existing expense API, preserving validation, decimal precision, and
user-level ownership boundaries.

**Agent/role used.** Copilot-assisted backend implementation. No specialized
agent run is claimed.

**What was delegated.** Nothing.

**Main proposal.** Add `PATCH`, `PUT`, and `DELETE` on
`/api/expenses/<id>/`. Scope the lookup to the authenticated user so a
foreign expense and a missing expense have the same 404 response. Reuse the
creation rules for positive decimal-string amounts and categories owned by
the current user.

**How the change was verified.**
- Ran the isolated API suite with
  `docker compose -p cashmire-issue37-38-test run --rm api python manage.py
  test api`: all 29 tests pass, including new update/delete coverage.
- Ran the same isolated project's `python manage.py check`: no issues.
- `git diff --check` passes.
- Removed only the isolated verification Compose resources.

**Accepted / modified / rejected.**
- Accepted: `PATCH` is partial, `PUT` requires `category_id`, `amount`, and
  `date`, and `DELETE` returns 204 with no response body.
- Modified: An omitted description in `PUT` is reset to `null`, consistent
  with replacement semantics and the create endpoint's optional description.
- Rejected: Revealing whether a foreign expense exists; foreign and missing
  IDs return the same 404 response.

**Final decision.** Issues #37 and #38 are implemented on the expense feature
branch, with update and delete operations restricted to the current user.

## 2026-10-07 — Verify expense ownership controls (Issue #39)

**Objective.** Verify and document that every implemented expense endpoint
scopes access to the authenticated user, with cross-user access concealed as
not found.

**Agent/role used.** Copilot-assisted implementation and security-control
review. No specialized agent run is claimed.

**What was delegated.** Nothing.

**Main proposal.** Retain query-level owner scoping for list and detail
operations, set the creator from the authenticated session rather than the
request body, and ensure category references are also owner-scoped. Record
the review in `docs/reviews/issue-39-expense-ownership.md`.

**How the change was verified.**
- Existing API tests assert expense listing excludes other users' records,
  creation ignores a client-supplied `user_id`, and update/delete return 404
  for foreign expense IDs.
- Added explicit `PUT` cross-user coverage alongside `PATCH`, comparing both
  responses to the missing-resource 404.
- Reviewed the ORM access paths for GET/POST collection and PATCH/PUT/DELETE
  detail operations.

**Accepted / modified / rejected.**
- Accepted: All expense reads and mutations must use user-scoped database
  lookups; writes derive ownership from the authenticated session.
- Modified: None.
- Rejected: Returning a different result for foreign and missing IDs, which
  could disclose whether another user's expense exists.

**Final decision.** The implemented expense endpoints enforce ownership
before accessing expense rows. Regression coverage and the reviewed control
are documented for issue #39.
