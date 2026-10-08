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

## 2026-10-07 — QA & Security review of Budget Model (Issue #45)

**Objective.** Closes #45 (QA review). Verify the Budget model implementation against its 
specification (`docs/specs/issue-45-budget-model.md`) across all 14 acceptance criteria (AC-1 through 
AC-14), focusing on data validation, database constraints, ORM configuration, test coverage, and 
security.

**Agent/role used.** QA & Security agent (read-only review, no source code edits).

**What was delegated.** Verify Budget model implementation against specification:
- Confirm model exists in `backend/api/models.py` with all fields and metadata
- Verify migration `0003_budget.py` creates table with complete structure (fields, constraints, indices)
- Run test suite (`python manage.py test api.tests.BudgetModelTests`) and verify all tests pass
- Audit input validation (amount, alert_threshold, period dates) at both Django and database levels
- Check referential integrity (user CASCADE, category PROTECT)
- Verify no information leaks or security issues
- Compare implementation against spec; flag any deviations
- Document findings in `docs/reviews/issue-45-budget-model.md`

**Main proposal.** All 14 acceptance criteria passed. The implementation is conformant, secure, 
fully tested (23 tests, 100% pass rate), and ready for merge. One non-blocking finding: Django model 
uses `check=` parameter instead of `condition=` for CheckConstraint (deprecated in Django 5.0+ but 
accepted for backward compatibility in 5.1.3). Migration correctly uses `condition=`.

**How the team verified it.**
- Ran full test suite: `python manage.py test api.tests.BudgetModelTests -v 2` → all 23 tests passed
- Verified AC-1: Budget model present in models.py with all required fields (user, category, amount, 
  period_start, period_end, alert_threshold, created_at, updated_at)
- Verified AC-2: Migration file 0003_budget.py creates table with single CreateModel operation 
  (modern Django 5.1 style)
- Verified AC-3: Migration applied without error (test database created and all migrations applied)
- Verified AC-4: amount is DecimalField(max_digits=10, decimal_places=2) with MinValueValidator(Decimal("0.01"))
- Verified AC-5: alert_threshold is DecimalField(max_digits=5, decimal_places=2, null=True, 
  default=Decimal("80.00")) with validators MinValueValidator(0) and MaxValueValidator(100)
- Verified AC-6: period_start and period_end are DateField with CheckConstraint(period_end >= period_start)
- Verified AC-7: UniqueConstraint(fields=['user', 'category', 'period_start', 'period_end'])
- Verified AC-8: ForeignKey to User with on_delete=models.CASCADE (test_user_cascade_delete passed)
- Verified AC-9: ForeignKey to Category with on_delete=models.PROTECT (test_category_protect_delete passed)
- Verified AC-10: Two indexes present: idx_budget_user_id on user, idx_budget_user_period on 
  (user, period_start, period_end)
- Verified AC-11: DateTimeField(auto_now_add=True) for created_at, DateTimeField(auto_now=True) for updated_at
- Verified AC-12: CheckConstraint(check=models.Q(amount__gt=0)) preventing zero/negative amounts
- Verified AC-13 & AC-14: All 23 tests cover required cases:
  - Valid budget creation (4 tests)
  - UNIQUE constraint enforcement (1 test)
  - Amount validation (5 tests covering 0, negative, 0.01, max, precision)
  - Period validation (3 tests covering end < start, end = start, end > start)
  - Alert threshold validation (5 tests covering null, 0, 100, negative, > 100)
  - Referential integrity (3 tests covering cascade/protect)
  - Timestamps (1 test)
- Audited security: No SQL injection (Django ORM used throughout), no information leaks in __str__ 
  method, proper cascading/protection behavior, validators at both ORM and database levels
- Verified no deviations from spec (acknowledged limitation: category.user_id == budget.user_id 
  must be validated at application level, as noted in spec section 6)

**Accepted / modified / rejected.**
- Accepted: All 14 acceptance criteria met. Implementation is conformant to specification.
- Accepted: One non-blocking finding (check= vs condition=) does not block merge; Django 5.1.3 
  accepts both for backward compatibility.
- Rejected: Nothing. The Budget model is ready for merge.

**Final decision.**
- The Budget model implementation is **approved for merge**. All acceptance criteria satisfied; 
  23 tests passing; no security issues, no spec deviations, no blockers.
- **Non-blocking follow-up (future maintenance):** Update CheckConstraint definitions in models.py 
  to use `condition=` instead of `check=` for consistency with Django 5.1.3 convention 
  (migration already correct). This is a maintenance task, not a blocker.
- Review artifacts: `docs/reviews/issue-45-budget-model.md` documents all findings with per-AC 
  verification, security audit results, and non-blocking recommendations.

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

## 2026-10-07 — Document database recreation from an empty instance (Issue #19)

**Objective.** Document the exact Docker Compose steps for rebuilding the
development database from an empty PostgreSQL instance using only committed
Django migrations, including an explicit warning that resetting the volume
deletes its data.

**Agent/role used.** Copilot-assisted documentation update. No specialized
agent run is claimed.

**What was delegated.** Nothing.

**How the change was verified.**
- Started a separate Compose project with a new PostgreSQL volume and applied
  Django migrations with:
  `docker compose -p cashmire-issue19-check run --rm api python manage.py migrate`.
  All built-in and project migrations, including `api.0001_initial`,
  `api.0002_category`, and `api.0003_expense`, applied successfully without
  manual SQL.
- Removed only the isolated verification project's containers, network, and
  volume afterward. The regular development database was not touched.
- `git diff --check` passes.

**Final decision.** The README documents the destructive reset warning and
commands to recreate PostgreSQL and apply all committed migrations from
empty. The procedure was verified against an isolated fresh database; no
existing local database was deleted.

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

## 2026-10-07 — Cashmire design system: visual overhaul (Issue #104, slice)

**Objective.** Apply the "Cashmire design system (draft)" visual brief
(warm-neutral palette, Fraunces/IBM Plex Mono/DM Sans typography, soft
radii, dark mode) to every screen that exists on `main`, as the
design-system bullet of issue #104's acceptance criteria.

**Agent/role used.** Claude Code (Sonnet 5), run directly against the
request rather than through `agentic/orchestrator.py` — this was a single
cross-cutting styling change spanning every existing screen, not a new
feature with its own architect/developer/QA split.

**What was delegated.** The full implementation: token/typography design
(including computing WCAG contrast ratios for every new text/background
pairing before picking values), self-hosting the three type faces,
restyling the shared shell and components, bringing `/health` onto the
shared tokens (the one screen the previous #104 slice had not reached),
and writing `docs/specs/issue-104-cashmire-design-system.md` and this
amendment's companion entry in `docs/decisions/0001-...md`.

**Main proposal.** Repoint existing token names to the new palette rather
than renaming them (avoids touching every call site); add a new
`base.css` global layer for true document-wide defaults only; self-host
fonts instead of a Google Fonts `<link>` to keep decision `0002` and the
privacy page's zero-third-party-request claim true without editing
`/privacy`; deviate from two of the brief's literal hex codes (button
fill, muted text) where they fail AA contrast at face value, documented
in the spec and in `tokens.css`'s own header comment; defer nav
expansion, the dashboard, chart colors, and photography/illustration —
none have a screen or asset pipeline to attach to yet.

**How the change was verified.**
- `npm test` in `frontend/`: all 86 existing tests pass unchanged (no test
  asserted on the removed literal colors).
- Contrast-checked every new text/background token pairing against the
  WCAG relative-luminance formula before picking final hex values (see
  the spec §3.1 table).
- Visually verified `/`, `/login`, `/register`, `/privacy`, `/health` in a
  real browser, in both light and (via `prefers-color-scheme: dark`)
  dark mode, including the register form's error state and the health
  page's error state.
- `grep`-verified no literal hex color remains in `frontend/src/routes` or
  `frontend/src/lib/components` outside `#104` issue references.

**Accepted / modified / rejected.**
- Accepted: the full palette, typography system, soft radii, pill
  buttons, dashed "stitched" dividers, faint weave texture, and automatic
  dark mode from the brief.
- Modified: button-fill and muted-text colors darkened from the brief's
  literal hex to clear WCAG AA contrast (see spec §3.1); fonts self-hosted
  instead of loaded from Google Fonts, for the privacy/decision-0002
  reason above.
- Rejected (deferred, not rejected): macro photography, line illustration,
  and the chart color palette — no asset pipeline or chart screen exists
  yet to attach them to; see spec §3.5.

**Final decision.** The Cashmire visual identity is implemented across
every screen that exists on `main` today, with the remaining #104
acceptance criteria (nav expansion, auth-aware nav, dashboard home)
explicitly left open pending #40/#41/#52/#53.


## 2026-10-07 — Integrate session-auth endpoints with main

**Objective.** Bring the registration, login, and logout endpoints from
`feat/20-user-model` onto current `main`, resolve API-file conflicts, and
preserve a single discoverable Django test package.

**Main proposal.** Merge current `main` into the auth foundation branch,
retain both authentication and expense/category routes, and move the existing
`api/tests.py` coverage into `api/tests/test_expenses.py` beside the
registration/login/logout modules.

**How the change was verified.**
- `docker compose -p cashmire-pr120-foundation run --rm api python manage.py
  test api`: all 53 API tests pass.
- `python manage.py check` reports no issues.
- `python manage.py makemigrations api --check --dry-run` reports no model
  or migration drift.
- The isolated Compose resources were removed; the regular development
  database was not modified.

**Final decision.** The auth endpoints and current main functionality
coexist, and all API tests are discoverable from one `backend/api/tests/`
package without a shadowing `tests.py` module.

## 2026-10-07 — Add reusable session authentication and current-user endpoint (Issue #26)

**Objective.** Provide a shared DRF session-authentication guard that resolves
the user from Django's session, returns 401 for anonymous requests, and can be
reused by function- and class-based protected views.

**Agent/role used.** Copilot-assisted implementation on the authentication
stack from issue #24. No specialized agent run is claimed.

**What was delegated.** Nothing.

**Main proposal.** Add a common `SessionAuthenticatedAPIView` base class and
`session_authenticated_api_view` decorator, backed by one session
authentication class and `IsAuthenticated` permission. Use them for the
logout and current-user views, and expose `GET /api/auth/me/` using the
existing read-only `UserSerializer`.

**How the change was verified.**
- Ran `docker compose -p cashmire-issue26-test run --rm api python manage.py
  test api`: all 27 API tests pass, including anonymous 401, authenticated
  session user serialization, Basic authentication rejection, and logout
  CSRF/session behavior.
- Ran `docker compose -p cashmire-issue26-test run --rm api python manage.py
  check`: no system-check issues.
- Called `GET /api/auth/me/` with `curl` and no session; received 401,
  `WWW-Authenticate: Session`, and the expected JSON error.
- Generated the OpenAPI schema; the custom session cookie authenticator is
  described as a cookie security scheme. Existing health/logout serializer
  generation errors remain outside this issue.
- Removed only the isolated Compose verification volumes and networks.

**Accepted / modified / rejected.**
- Accepted: Use Django sessions, not Basic or JWT, per decision 0003.
- Modified: Provide both a function-view decorator and a class-view base so
  future expense and budget endpoints can share the guard without repeating
  authentication configuration.
- Rejected: Duplicating user fields or exposing password data; the existing
  `UserSerializer` defines the response shape.

**Final decision.** Protected endpoints now share one session-authentication
implementation, anonymous access returns 401, and `GET /api/auth/me/` returns
only the authenticated user's public fields.

## 2026-10-08 — Document and verify auth route tests (Issue #31)

**Objective.** Ensure registration, login, logout, and the protected
current-user route have automated happy-path and failure-case coverage, and
document one command to run the API suite.

**Main proposal.** Reuse the existing auth-route test modules, which already
cover successful registration/login/logout, duplicate registration email,
missing fields, wrong credentials, unauthenticated access, session handling,
CSRF enforcement, and `/api/auth/me/` identity responses. Document a single
suite command in the README instead of duplicating tests.

**How the change was verified.**
- Ran `docker compose -p cashmire-issue31-verify run --rm api python
  manage.py test api`: all 111 API tests passed, including all four auth
  route suites.
- Ran `python manage.py check`: no system-check issues.
- Removed only the isolated Compose verification resources.
- `git diff --check` passes.

**Final decision.** The existing automated tests satisfy the route and
failure-case coverage in issue #31. The README now documents one command for
running the complete API suite locally or in CI.

## 2026-10-07 — QA & Security review of Budget Create Endpoint (Issue #46)

**Objective.** Closes #46 (QA review). Verify the Budget create endpoint implementation against 
its specification (`docs/specs/issue-46-create-budget-endpoint.md`) across all 15 acceptance criteria 
(AC-1 through AC-15), focusing on endpoint routing, authentication, input validation, ownership 
enforcement, duplicate detection, and security.

**Agent/role used.** QA & Security agent (read-only review, no source code edits).

**What was delegated.** Verify Budget endpoint implementation against specification:
- Confirm endpoint `POST /api/budgets/` exists at the correct route with trailing slash
- Verify authentication required (SessionAuthentication + IsAuthenticated)
- Audit input validation (category_id, amount, period_start, period_end, alert_threshold)
- Verify category ownership check returns 404 for foreign/nonexistent categories
- Confirm duplicate detection at application level (returns 409 Conflict before DB touch)
- Verify owner always set to request.user (not from client input)
- Run test suite (`python manage.py test api.tests.BudgetCreateEndpointTests -v 2`) and verify 
  all tests pass
- Audit response serialization (Decimal to JSON string, ISO 8601 timestamps)
- Check for information leaks in error messages
- Verify race condition handling for concurrent duplicates
- Document findings in `docs/reviews/issue-46-create-budget-endpoint.md`

**Main proposal.** 14 of 15 acceptance criteria passed. **1 blocking finding:** `IntegrityError` 
not caught when a race condition creates duplicate budgets (two concurrent requests bypass the 
applicative check and both reach the database). Returns 500 Internal Server Error instead of 409 
Conflict as specified. Requires adding `try/except IntegrityError` around the `Budget.objects.create()` 
call. Additionally, 2 non-blocking findings: (1) HTTP 403 returned for missing authentication instead 
of spec's 401 (consistent with category_list and DRF IsAuthenticated behavior, but spec mismatch); 
(2) duplicate validators in serializer and model (defense in depth, not a bug).

**How the team verified it.**
- Ran full test suite: `python manage.py test api.tests.BudgetCreateEndpointTests -v 2` 
  → all 28 tests passed (4.140s)
- Verified AC-1: Route `POST /api/budgets/` present in `backend/api/urls.py` with trailing slash
- Verified AC-2: SessionAuthentication + IsAuthenticated decorators present; test confirms 403 for 
  unauthenticated requests (DRF standard, not 401 per spec — non-blocking finding)
- Verified AC-3: BudgetSerializer defines all fields (category_id, amount, period_start, period_end, 
  alert_threshold)
- Verified AC-4: DecimalField used for amount; test `test_budget_create_amount_serialized_as_string` 
  confirms JSON serialization as string `"123.45"`, not float
- Verified AC-5: amount > 0 enforced; `validate_amount()` and MinValueValidator in model both check; 
  tests verify 0, negative, and 0.01 (minimum) all handled correctly
- Verified AC-6: DateField validation for YYYY-MM-DD format; `validate()` method checks 
  period_end >= period_start; tests verify invalid dates, inverted ranges, and single-day budgets
- Verified AC-7: Category ownership check at line 124 (`Category.objects.get(id=category_id, user=request.user)`) 
  with DoesNotExist → 404; tests `test_budget_create_nonexistent_category_404` and 
  `test_budget_create_foreign_category_404` confirm 404 for both missing and foreign categories
- Verified AC-8: alert_threshold optional, 0–100 if provided; `validate_alert_threshold()` and 
  model validators both enforce range; tests verify null, 0, 100, and out-of-bounds all correct
- Verified AC-9: Applicative duplicate check at lines 132–144 (`Budget.objects.filter(...).exists()`) 
  before create; test `test_budget_create_duplicate_409` confirms 409 Conflict. **However, no try/except 
  around create() for IntegrityError** — this is the blocking finding.
- Verified AC-10: Owner always `request.user` (line 148); serializer marks user_id as read-only; 
  test confirms created budget's user_id matches authenticated user
- Verified AC-11: 201 Created response includes all fields (id, user_id, category_id, amount, 
  period_start, period_end, alert_threshold, created_at, updated_at); test verifies all present
- Verified AC-12: DecimalField serializes amount and alert_threshold as JSON strings; verified 
  in response
- Verified AC-13: Timestamps include ISO 8601 format ("T" separator, timezone info); test passes
- Verified AC-14: 28 comprehensive tests covering all scenarios (authentication, validation, 
  ownership, duplicates, serialization)
- Verified AC-15: DB UNIQUE constraint `unique_budget_per_user_category_period` exists in migration 
  and enforces the constraint. **Constraint is not caught by endpoint code** (blocking finding).
- Audited security: No SQL injection (Django ORM), no information leaks (generic error messages), 
  ownership not spoofable, Decimal arithmetic (not float), but race condition vulnerability.

**Accepted / modified / rejected.**
- Accepted: 14 of 15 acceptance criteria met. Endpoint is functionally conformant to specification 
  for normal (non-race-condition) operation.
- Rejected: **1 blocking finding must be fixed:** `IntegrityError` not caught. Add try/except block 
  around `Budget.objects.create()` to catch `IntegrityError` and return 409 Conflict (as promised 
  in the spec's "filet de sécurité" section).
- Accepted: 2 non-blocking findings (403 vs 401 authentication status, duplicate validators) do not 
  gate merge once the blocking finding is fixed.

**Final decision.**
- The Budget create endpoint has **1 blocking finding** (IntegrityError handling) that must be fixed 
  before merge.
- The fix is minimal (4–6 lines of code): import IntegrityError, wrap create() in try/except, return 
  409 Conflict on catch.
- Once fixed, the endpoint is approved for merge. All 28 tests pass; specification is conformant; 
  no security issues remain.
- **Critical next action:** Full-Stack Development agent (or human) adds IntegrityError handling 
  to `backend/api/views.py` lines 158–161, then reruns test suite to confirm fix does not break 
  any existing tests.
- Review artifacts: `docs/reviews/issue-46-create-budget-endpoint.md` documents all findings 
  (blocking, non-blocking, verification steps, OWASP audit, data integrity checks) with reproduction 
  steps for the race condition.


## 2026-10-07 — Build the expense list and create/edit screens (Issues #40, #41)

**Objective.** Give the front-end its first expense screens: a list of the
current user's expenses and a form to create or edit one, against the
expense/category endpoints already merged into `main` (#34–#39).

**Agent/role used.** Claude Code-assisted frontend implementation. No
specialized agent run (`agentic/orchestrator.py`) is claimed.

**What was delegated.** Nothing — implemented directly in this session,
driven interactively.

**Main proposal.** Add `frontend/src/lib/api/{expenses,categories}.js` as
thin `apiFetch` wrappers over the documented routes (`docs/api-design.md`
§3, §5.1) — real calls, not a mock layer, following the same "built against
the contract" pattern login/register used before their own backend existed.
Add `/expenses` (list), `/expenses/new` (create) and `/expenses/[id]/edit`
(edit) routes, each self-contained like `login`/`register` rather than
sharing one form component. Amounts stay decimal strings end to end;
`money.js`'s `isValidDecimalString`/`compareDecimal` do the one client-side
check this form needs (amount > 0) without ever coercing to a float.

**How the change was verified.**
- `npm test` in `frontend/`: 103/103 passing, including 17 new tests across
  the two API wrappers and the three new screens.
- Manually traced the edit screen's data flow: since
  `backend/api/urls.py` has no `GET /api/expenses/{id}/` (only list+create
  combined, and PATCH/PUT/DELETE on the detail route), the edit screen reads
  its initial values out of the already-fetched, unpaginated list rather
  than fetching the single resource — the one call the backend actually
  supports.

**Accepted / modified / rejected.**
- Accepted: no shared `ExpenseForm` component between the create and edit
  screens, matching how `login`/`register` stayed separate before #104's
  design-system slice touched them — duplication here is deliberate, not
  an oversight.
- Accepted: deleting an expense is left entirely to issue #42 (confirmation
  flow); the list screen only links to "Edit".
- Rejected: wiring these routes into the shared nav (`+layout.svelte`) —
  decision `0001`'s issue-#104 amendment explicitly defers nav/dashboard
  expansion to that issue, which depends on this one landing first.

**Final decision.** Issues #40 and #41 are implemented on
`feat/40-41-expense-screens`, built directly against the real (already
merged) expense/category API, with no mock layer and no premature shared
form component.

## 2026-10-07 — Build the budget dashboard and create/edit form (Issues #52, #53)

**Objective.** Give the front-end a budget dashboard (spent/remaining,
percentage, status) and a create/edit form, against the budget endpoints
documented in `docs/api-design.md` §4 — not yet merged into `main` at the
time this was written (#45, #115/#121-125 open).

**Agent/role used.** Claude Code-assisted frontend implementation. No
specialized agent run (`agentic/orchestrator.py`) is claimed.

**What was delegated.** Nothing — implemented directly in this session.

**Main proposal.**
- `frontend/src/lib/api/budgets.js`: real `apiFetch` wrappers over
  `/api/budgets/`, plus `monthToPeriod`/`periodToMonth` translating the
  "month/year" picker issue #53 asks for into the `period_start`/
  `period_end` pair the API actually stores.
- `frontend/src/lib/components/BudgetForm.svelte`: **one** form reused for
  both create and edit, per #53's explicit acceptance criterion (unlike
  #40/#41, where create/edit stayed two separate screens) — category and
  month are read-only in edit mode, since the API only accepts
  `amount`/`alert_threshold` on `PATCH` (`docs/api-design.md` §4.4).
- `routes/budgets/+page.svelte` renders each budget's `status` field
  exactly as the API returns it (`ok`/`warning`/`full`/`exceeded`,
  colored + labelled per `docs/decisions/budget-thresholds.md`'s table) —
  it never recomputes the status, only the percentage-for-the-progress-bar
  number, which `money.js`'s `percentOf` exists for.
- Added `--color-success-*`/`--color-full-*` to `tokens.css`: the existing
  two semantic colors (warning, error) don't cover the decision's
  four-status table, so this is a concrete, decision-driven extension, not
  speculative design-system growth.

**How the change was verified.**
- `npm test` in `frontend/`: 122/122 passing (19 new, across the API
  client, the dashboard, and both form screens), including the 409
  duplicate-budget conflict surfacing a specific message (#53's AC) and
  the dashboard's progress bar capping its displayed value at 100 while
  still labelling an over-budget entry as such in text (never color alone,
  per `docs/mvp-scope.md` §3.7).
- Unit-tested `monthToPeriod` against a 31-day month, a leap-year February,
  and a non-leap-year February, since an off-by-one here would silently
  mis-scope every budget's spending window.

**Accepted / modified / rejected.**
- Accepted: issue #52's text says three statuses (ok/warning/exceeded);
  followed the later, more specific `budget-thresholds.md` decision's four
  statuses instead, since it explicitly supersedes that part of
  `docs/mvp-scope.md` and the issue predates it.
- Accepted: no delete-budget action on the dashboard — no issue currently
  asks for one (unlike expenses, which has #42), so it isn't guessed at.
- Rejected: wiring `/budgets` into the shared nav — left to #104, same as
  #40/#41's expense routes.

**Final decision.** Issues #52 and #53 are implemented on
`feat/52-53-budget-screens` (stacked on `feat/40-41-expense-screens`,
since both reuse `lib/api/categories.js`), built against the documented
but not-yet-merged budget API, with one shared create/edit form as the
issue explicitly requires.

## 2026-10-07 — Unify the front-end into one navigable site (Issue #104)

**Objective.** Stitch #40/#41 (expense screens) and #52/#53 (budget
screens) into one coherent site: an auth-aware nav, and a home page that
shows the real budgets/expenses summary instead of the original
health-check placeholder — entirely against the mocked/not-yet-merged
APIs, per #104's explicit scope.

**Agent/role used.** Claude Code-assisted frontend implementation. No
specialized agent run (`agentic/orchestrator.py`) is claimed.

**What was delegated.** Nothing — implemented directly in this session.

**Main proposal.**
- `frontend/src/lib/stores/auth.js`: an in-memory-only auth-state store,
  populated by `login`/`register`'s own success handlers and cleared by a
  new `logout()` (calling `POST /api/auth/logout/`). Deliberately does
  **not** probe `GET /api/auth/me/` on layout mount — `routes/layout.test.js`'s
  existing T-4b asserts the shared layout issues zero fetch calls on
  render, and this keeps that true. Accepted consequence: a hard reload
  reverts the nav to logged-out until the next login/register.
- `+layout.svelte`'s nav now renders one of two link sets based on that
  store (logged-out: Home/Log in/Register/Privacy; logged-in: Dashboard/
  Expenses/Budgets/Privacy + a `Log out` button), with zero changes to
  `login`/`register`'s own existing, already-tested submit logic beyond
  one line each recording that their request succeeded.
- `routes/+page.svelte` (home) now shows a public landing when logged out,
  and the real dashboard — each budget's status via a new, shared
  `BudgetCard` component, plus recent expenses — when logged in, per
  `docs/mvp-scope.md`'s central journey step 3.
- `BudgetCard.svelte` factors the budget-card rendering out of
  `routes/budgets/+page.svelte` (#52) so the home dashboard doesn't
  duplicate it — the second consumer `docs/decisions/0001`'s design-system
  amendment said to wait for before introducing a `Card` style.
- Amended `docs/decisions/0001-shared-app-shell-layout.md` as #104's
  acceptance criteria require.

**How the change was verified.**
- `npm test` in `frontend/`: 134/134 passing. Critically, this includes
  running the **existing, unmodified** `login`/`register`/`layout` test
  files and confirming zero regressions — in particular that
  `layout.test.js`'s T-4b (zero fetch calls on render) and the login
  test's exact-one-fetch-call assertion both still hold after wiring in
  the auth store.
- New coverage: nav rendering for both auth states and the logout flow
  (`layout.test.js`), the home dashboard's logged-out/loading/ready/error/
  empty states (`routes/page.test.js`), and that `routes/budgets/+page.svelte`'s
  existing tests still pass unchanged after the `BudgetCard` extraction
  (same markup, just factored out).

**Accepted / modified / rejected.**
- Accepted: the reload-resets-to-logged-out limitation, rather than adding
  a `/api/auth/me/` check that would break the layout's existing
  zero-fetch-on-render guarantee — flagged in the decision amendment for
  the team to revisit against #26/#27, not silently worked around.
- Rejected: wrapping the "Add budget"/"Create an account" calls-to-action
  in a `<Button>` component — `<Button>` renders a native `<button>`, and
  a `<button>` nested in an `<a>` (or vice versa) is invalid HTML; kept
  these as plain anchors styled to match.

**Final decision.** Issue #104's nav/dashboard slice is implemented on
`feat/104-unify-frontend` (stacked on `feat/52-53-budget-screens`), with
every MVP screen reachable from the shared nav and the home page replaced
by the real summary, while explicitly leaving the mock-to-real API swap
(#92) and the a11y/responsive passes (#64/#65) untouched.

## 2026-10-07 — Fix missing CSRF_TRUSTED_ORIGINS (Issue #130)

**Objective.** Fix a backend gap found while manually testing the #104 PR
stack (#127/#128/#129) end-to-end: every authenticated mutation from the
real frontend was failing with a Django CSRF "Origin checking failed"
error, regardless of a correct session cookie and `X-CSRFToken` header.

**Agent/role used.** Claude Code-assisted backend fix. No specialized
agent run (`agentic/orchestrator.py`) is claimed.

**What was delegated.** Nothing.

**How the gap was found.** While demoing the #104 stack, locally (never
pushed) integrated the then-unmerged auth (#126) and budget (#115,
#121-125) backend branches into a throwaway branch to exercise a real
login → create-budget flow end-to-end. The create request reproducibly
failed with `"CSRF Failed: Origin checking failed - http://localhost:5173
does not match any trusted origins."`, isolated via `curl` with/without an
`Origin` header to confirm it was Django's CSRF middleware's own
cross-origin check — a different, more specific gap than the
"no CSRF-bootstrap-route" one `docs/decisions/0003-session-cookie-auth-strategy.md`
already names, and one that affects endpoints already merged into `main`
(`/api/expenses/`), not just the unmerged branches used to reproduce it.

**Main proposal.** Add `CSRF_TRUSTED_ORIGINS` to
`backend/cashmire/settings.py`, reusing the same `DJANGO_CORS_ALLOWED_ORIGINS`
env var and default `CORS_ALLOWED_ORIGINS` already uses, since both
describe "the frontend's origin(s)" and have never had reason to differ.

**How the change was verified.**
- Reproduced the failure against the real backend via `curl` (session
  cookie + valid `X-CSRFToken` + `Origin: http://localhost:5173` → 403)
  before the fix, and confirmed 201 after.
- Added `CsrfTrustedOriginsTests` to `backend/api/tests.py`, using
  `APIClient(enforce_csrf_checks=True)` (every other test class in this
  file uses the default `APIClient()`, which disables CSRF checking
  entirely — exactly why this gap had zero test coverage until now).
  Proves the setting is both sufficient (succeeds with it) and necessary
  (`@override_settings(CSRF_TRUSTED_ORIGINS=[])` reproduces the original
  403) against the already-merged `/api/expenses/` endpoint.
- `python manage.py test api`: 31/31 passing (2 new). `python manage.py
  check`: no issues.

**Accepted / modified / rejected.** Nothing modified or rejected — this is
a one-setting fix plus the regression test that was missing for it.

**Final decision.** `CSRF_TRUSTED_ORIGINS` is set on `fix/130-csrf-trusted-origins`,
closing #130, with regression coverage proving both the failure mode and
the fix.

## 2026-10-07 — Cover the API health endpoint with a backend test (Issue #17)

**Objective.** Complete issue #17 by adding an automated check for the existing
`GET /api/health/` endpoint, which must return HTTP 200 and JSON
`{"status": "ok"}`.

**Agent/role used.** Copilot-assisted implementation. No specialized agent
run is claimed.

**What was delegated.** Nothing.

**How the change was verified.**
- Ran `docker compose exec -T api python manage.py test
  api.tests.HealthCheckTests`: the targeted test passed.
- Ran `curl.exe --silent --show-error --max-time 5 --include
  http://127.0.0.1:8000/api/health/`: received HTTP 200,
  `Content-Type: application/json`, and `{"status":"ok"}`.
- `git diff --check` passes.

**Final decision.** The existing health route is now covered by a backend
regression test for its successful JSON response. The endpoint was also
verified manually over HTTP.

## 2026-10-08 — Rebase conflict resolution: fix `tests.py`/`tests/` module shadow

**Objective.** Resolve the multi-commit rebase of
`feat/50-budget-consumption-service` onto `main` (bdf9b9b), replaying
registration, login, logout, health-check, database-recreation, and
current-user commits on top of the budget consumption work.

**Agent/role used.** Claude Code-assisted conflict resolution. No
specialized agent run is claimed.

**What was delegated.** Nothing — resolved interactively, commit by commit.

**Main proposal.** Most conflicts in `docs/agentic-log.md` were pure
append-only positional conflicts (two branches adding entries at the same
line): resolved by keeping both sides' entries in chronological order.
`backend/api/{urls,views}.py` conflicts were resolved the same way —
additive route/view blocks kept from both sides, with import lines merged
by hand.

One conflict was not purely cosmetic: resolving the registration commit's
test-restructuring (`backend/api/tests/` package with
`test_registration.py`, `test_login.py`, etc.) left both that package and
the pre-existing `backend/api/tests.py` module on disk simultaneously.
Python/Django only discovers one of the two when both exist beside each
other — the package shadows the module — so every test class that lived in
`tests.py` (health check, categories, expenses, budgets, CSRF trusted
origins) would have silently stopped running. This was caught by comparing
against the original (pre-rebase) branch history, where a later merge
commit's log entry explicitly described moving `tests.py`'s coverage into
the `tests/` package for exactly this reason.

**How the change was verified.**
- `git mv backend/api/tests.py backend/api/tests/test_core.py`, then fixed
  its now-one-level-deeper relative import (`.models` → `..models`); its one
  other import (`api.services.budget_consumption`) was already absolute and
  needed no change.
- `python3 -m py_compile` on every conflict-touched file
  (`backend/api/{urls,views}.py`, `backend/api/tests/test_core.py`).
- Grepped for leftover `<<<<<<<`/`=======`/`>>>>>>>`/`|||||||` markers after
  every resolved file.

**Accepted / modified / rejected.**
- Accepted: keep both sides for every additive conflict (routes, views, log
  entries) rather than picking one.
- Rejected: including the orphaned "Integrate session-auth endpoints with
  main" log entry inherited from a merge commit (`ac3350c`) that this linear
  rebase does not replay — its described actions (a `main` merge, "53 API
  tests pass") don't match what this rebase actually did, so keeping it
  would have misrepresented the history.

**Final decision.** The rebase completed with all tests discoverable from
one `backend/api/tests/` package and no shadowing `tests.py` module. Running
the full backend test suite after the rebase remains a human follow-up, the
same caveat this log has flagged after every prior rebase/merge step.

## 2026-10-08 — Merge `main` into the rebased branch: correct the `test_core.py` detour

**Objective.** The previous entry's rebase (above) replayed this branch onto
a stale local `main` tip (`bdf9b9b`) that was never actually part of
`origin/main` — a divergence that predates this session. Merging the real
`origin/main` (tip `692ef37`) back in surfaced that stale base directly:
duplicate `RegisterView`/`LoginView`/`LogoutView`/`current_user`
implementations (byte-identical to main's, just differently ordered) and a
rename/rename conflict between this branch's `tests/test_core.py` and
main's own, independently-done `tests/test_budgets.py` +
`tests/test_expenses.py` split.

**Agent/role used.** Claude Code-assisted conflict resolution. No
specialized agent run is claimed.

**What was delegated.** Nothing — resolved interactively.

**Main proposal.** Where this branch's code was a verbatim duplicate of
main's (confirmed by diffing both versions directly, not by inspection),
take main's copy and delete ours, rather than keep both. Concretely:
`backend/api/views.py` and `backend/api/urls.py` now match `origin/main`
exactly (the duplicate `RegisterView`/`LoginView`/`LogoutView`/
`current_user` block and the duplicate route lines are gone). For tests,
the previous entry's `test_core.py` is deleted entirely — main's
`test_expenses.py` already covers everything in it except
`BudgetConsumptionServiceTests`, which is this branch's one genuinely
unique contribution (issue #50, not yet on `main` at all: `git grep` found
no `backend/api/services/` directory on `origin/main`'s tip). That one class
was appended to main's `test_budgets.py`, fixing its one new import
(`Expense`, not previously needed by main's budget tests).

**How the change was verified.**
- Diffed this branch's pre-merge `views.py`/`urls.py` against `origin/main`'s
  directly (`git show 692ef37:... | diff -`): confirmed the only
  differences were declaration order and import ordering, not logic —
  justified taking main's copy outright instead of hand-merging.
- Diffed every overlapping test class (`HealthCheckTests`, `CategoryListTests`,
  `ExpenseModelTests`, `ExpenseCreateTests`, `ExpenseListTests`,
  `ExpenseDetailMutationTests`, `CsrfTrustedOriginsTests`, `BudgetModelTests`,
  `BudgetCreateEndpointTests`) line-by-line between this branch's old
  `test_core.py` and main's `test_expenses.py`/`test_budgets.py`: identical
  apart from trivial blank-line differences — confirming nothing unique was
  lost by deleting `test_core.py`.
- `python3 -m py_compile` on the assembled `test_budgets.py` and on
  `views.py`/`urls.py`.
- Grepped every resolved file for leftover conflict markers.

**Accepted / modified / rejected.**
- Accepted: main's canonical "Integrate session-auth endpoints with main"
  (#26) and "Document and verify auth route tests" (#31) log entries as the
  authoritative history for that work, superseding this branch's
  independent reimplementation of the same features.
- Rejected: keeping `test_core.py` as a third parallel copy of tests that
  main already has properly split; that would reintroduce the exact
  module/package shadowing risk the previous entry had just fixed, one
  layer up (three sources of truth instead of two).

**Final decision.** After this merge, `backend/api/views.py` and
`backend/api/urls.py` are identical to `origin/main`'s, and
`backend/api/tests/` contains only `origin/main`'s own test files plus this
branch's unique `BudgetConsumptionServiceTests`, folded into
`test_budgets.py`. Running the full backend test suite remains the
mandatory human (or agent) follow-up before this is considered merge-ready
— static review and `py_compile` do not catch Django/DRF wiring or
migration errors.

## 2026-10-08 — Audit database query safety (Issue #61)

**Objective.** Resolve the SQL injection / unsafe-query audit criteria in #61:
confirm database access is safe, add a regression test for an injection
payload, and record the checklist result.

**Agent/role used.** Copilot-assisted backend implementation and audit.

**What was delegated.** Nothing — the backend audit and test change were
performed directly.

**How the team verified it.**
- Audited Python application code under `backend/`; no raw SQL execution or
  dynamically assembled SQL was found. Database reads, filters, creates, and
  updates use the Django ORM.
- Added `ExpenseListTests.test_category_filter_rejects_sql_injection_payload`
  to verify `1 OR 1=1 --` is rejected with HTTP 400 before filtering and no
  expense data is returned.
- Ran `docker compose run --rm api python manage.py test api.tests.test_expenses`:
  all 33 tests passed.
- Ran `git diff --check`: passed.

**Accepted / modified / rejected.**
- Accepted: keep database reads and filters in the existing ORM-based
  implementation; no raw-SQL rewrite was needed because the audit found no
  unsafe query construction.
- Accepted: document all three issue checklist items as resolved in
  `docs/reviews/issue-61-sql-injection.md`.

**Final decision.** The audited backend has no identified SQL string-building
path. The regression test and issue-specific audit record are in place; no
application behavior changed.

## 2026-10-08 — Audit des routes API (Issue #57)

**Objective.** Passer en revue chaque route pour la validation, les contrôles
de propriété et les réponses d'erreur, et enregistrer le résultat.

**Agent/role used.** Revue directe assistée par Claude Code (lecture de
`views.py`, `serializers.py`, `auth.py`, `settings.py`, des tests).

**What was delegated.** La lecture du code et la rédaction de la checklist;
le tri des écarts reste à l'équipe.

**How the team verified it.**
- Chaque route de `backend/api/urls.py` est dans la checklist de
  `docs/reviews/issue-57-route-audit.md`.
- Le critère « pas de stack trace » est rattaché à `sanitized_exception_handler`
  (#62), `DEBUG=false` par défaut et `api.tests.test_errors`.

**Accepted / modified / rejected.**
- Accepted: aucune route sans contrôle de propriété ou de validation.
- Reported, not fixed: 5 écarts (G1 à G5), dont G1 (403 au lieu de 401 pour un
  anonyme sur categories / expenses / budgets), à transformer en issues.

**Final decision.** Audit enregistré; aucune modification de code.
