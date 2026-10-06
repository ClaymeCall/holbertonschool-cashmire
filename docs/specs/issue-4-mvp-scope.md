# SPEC — MVP scope documentation

- **Issue:** #4 "Write MVP scope documentation"
- **Status:** Proposal. Not approved. A human must read this spec before implementation.
- **Author:** Product & Architecture agent
- **Scope:** Documentation only. No code, no migrations, no backend or frontend changes.
- **Output artifact:** `docs/mvp-scope.md` (single document, in French)

---

## 0. Purpose of this spec

This spec describes the plan and expected content for `docs/mvp-scope.md`, a reference document that explicitly defines the Cashmire MVP — what is built, what is explicitly out of scope, and the user journey at the heart of the product. This document is:

1. A **boundary marker** for the Product & Architecture agent: every spec must reference it to stay in scope.
2. A **team contract** about what success means for this 4-day project.
3. A **design guide** for future agents (Full-Stack Development, QA & Security) — they read this before starting work.

The spec itself is not the MVP scope; it is a blueprint for authoring it. The Full-Stack Development agent reads *this* spec and writes the actual `docs/mvp-scope.md` document.

---

## 1. Problem statement and acceptance criteria

### 1.1 User story

> As a team member on Cashmire, I want one authoritative document that lists every feature and constraint in the MVP, so that all feature specs can reference it consistently and we never argue about scope again.

### 1.2 Acceptance criteria (testable)

| ID | Criterion | How it is checked |
|----|-----------|-------------------|
| AC-1 | File `docs/mvp-scope.md` exists and is written entirely in French. | File exists; spot-check that no English section appears outside of code references or external tool names. |
| AC-2 | The document lists all **required** MVP features mentioned in the project brief: user authentication, CRUD operations on expenses, budget management with consumption tracking and alert thresholds, expense categories, privacy and legal information page, security posture, accessibility compliance, and Docker-based local development setup. | §2.1 of this spec lists each; final document checks all explicitly. |
| AC-3 | Explicitly separate sections mark features as **out of scope**, with clear justification for why they are not included in the MVP. | §3 of this spec defines the structure; the document contains a dedicated "Hors périmètre MVP" section. |
| AC-4 | The document describes **target users** and their roles (e.g. individual expense tracker, household budget manager). | §4 of this spec outlines; final document §2 includes a "Utilisateurs cibles" subsection. |
| AC-5 | The document describes the **central user journey** in detail: user login → enter an expense → view the impact on budget consumption and any alert thresholds triggered. | §4 of this spec defines the journey; final document §3 walks through it step-by-step. |
| AC-6 | The document is written in a tone consistent with the project's existing specs (`docs/specs/issue-63-privacy-page.md`): formal, precise, no marketing language, and verifiable claims only. | Human review against the reference spec. |
| AC-7 | The document references constraints already established in decision records (e.g. `Decimal` / `NUMERIC` for monetary values from `product-architecture.md`, privacy-page rule from `decisions/0002`, layout rule from `decisions/0001`). | Spot-check for citations of existing decisions. |
| AC-8 | The document is short, focused and proportionate — roughly 1500–2500 words, not a design spec for the entire platform. | Word count; reading to confirm it is a scope marker, not a detailed requirements document. |

---

## 2. Content structure and outline

### 2.1 Required sections and outline

The final `docs/mvp-scope.md` document must contain the sections below, in order. Exact headings and wording are the author's; this spec is prescriptive about *what each section addresses*, not *how it is worded*.

| Section | Heading suggestion | Content description | Notes |
|---------|--------------------|--------------------|-------|
| 0 | (preamble) | A single sentence or two explaining what this document is: "This document defines the scope of the Cashmire minimum viable product for the 4-day project sprint." | Brevity; readers know it exists because they were told to read it. |
| 1 | "Utilisateurs cibles et leur contexte" (Target users and context) | Describe who this MVP is for. Examples: individuals tracking personal expenses and budgets; household members sharing a budget; anyone learning to code an expense tracker. Explain what problem the MVP solves for them, and what is *not* solved (e.g. no multi-currency, no investment tracking). | Reference the project charter / team notes if there is explicit guidance; otherwise define plausibly for a student project. Focus on use cases, not personas. |
| 2 | "Parcours utilisateur central" (Central user journey) | Walk through the **one** user flow that is central to the MVP: 1) User logs in (or creates an account, if auth requires signup), 2) User enters an expense, with amount, category, date, 3) User views their dashboard or budget page, which shows: – total consumption against budget limits, – alert if a threshold is exceeded, – list of recent expenses. Make it concrete: "User sees that they have spent $45 of their $100 monthly groceries budget." | This is the happy path; error cases come later. Use present tense. Tie it to the Acceptance Criteria that follow. |
| 3 | "Fonctionnalités incluses dans le MVP" (Features included in MVP) | Divide into logical subsections. Each subsection names a major feature and lists what is in scope for it. Follow the breakdown in AC-2: **3.1 Authentification et comptes**, **3.2 Gestion des dépenses**, **3.3 Gestion des budgets**, **3.4 Catégories**, **3.5 Page de confidentialité et mentions légales**, **3.6 Sécurité**, **3.7 Accessibilité**, **3.8 Infrastructure Docker**. For each: – State the goal in one sentence. – List the specific capabilities included (e.g. under "Gestion des budgets": set a budget per category or month, see consumption, get alerted if spent ≥ threshold). – Cite the relevant decision record if one applies (e.g. for Decimal rule, privacy rule). | See §2.2 for content of each subsection. |
| 4 | "Hors périmètre MVP" (Out of scope) | List features that are **explicitly not** in the MVP, even though they might seem natural to the product (e.g. multi-user households, bank API integration, mobile app, investment tracking). For each, briefly explain why (e.g. "Requires OAuth and third-party integrations, deferred to post-MVP"). | See §2.3 for this list. |
| 5 | "Constraints et décisions architecturales" (Constraints and architectural decisions) | One or two paragraphs stating the standing constraints from CLAUDE.md and existing decision records: – Monetary values are always `Decimal` / `NUMERIC`, never float. – The privacy page applies decision `0002` — it must stay current with the code. – The shared app shell applies decision `0001`. – Stack is fixed: Django + DRF, SvelteKit, PostgreSQL, Docker Compose. | Cite the files. This is a checklist for future specs. |
| 6 | "Succès du MVP" (Success criteria for the MVP) | Define what "done" looks like. Examples: – All seven features (§3.1–3.7) are implemented and tested. – The privacy page is reviewed and approved by a human (per decision `0002`). – Docker Compose starts all services without error. – All acceptance criteria in feature specs pass (human-verified). – No security defect rated OWASP Top 10 High or above is unresolved. | These are meta-criteria; they set the bar for "ready to show to stakeholders". |

### 2.2 Content for each MVP feature subsection (§3.1–3.8)

Each subsection (3.1–3.8) follows this pattern:

#### 3.1 Authentification et comptes (Authentication and accounts)

**Goal:** Users can register and log in securely.

**In scope:**
- User registration (email + password, or simpler method if agreed).
- User login with session or token-based auth.
- Session logout.
- (Optionally, per team decision:) email verification before account activation, or password reset flow. Flag if this is a team question.

**Data model implications (do not implement; flag for the Full-Stack Development agent):**
- A `User` model with email, password hash, created/updated timestamps.
- Password validators (Django built-in or custom).
- Session/token storage (Django sessions by default, or JWT if the team prefers).

**Security requirements:**
- Passwords stored as hashes, never plaintext.
- No password in API responses or logs.
- CSRF protection on login form (Django default).
- Rate limiting on login endpoint (TBD: team to decide on limits).

**Accessibility:**
- Login form labels associated with inputs.
- Error messages clear and accessible.
- Keyboard navigable.

---

#### 3.2 Gestion des dépenses (Expense management)

**Goal:** Users can record and view their spending.

**In scope:**
- Create an expense: amount (Decimal, validated ≥ 0), description, category, date.
- View a list of recent expenses (all or filtered by category/date range, TBD).
- Edit an expense.
- Delete an expense.
- No attachments, no receipt images, no sharing of individual expenses.

**Data model implications:**
- An `Expense` model with `amount` (Decimal/NUMERIC, mandatory), `description` (text), `category` (foreign key to Category), `date`, `owner` (foreign key to User), timestamps.
- Expense list ordered by date (descending).
- All expenses are user-scoped: User A cannot see or modify User B's expenses.

**In API:**
- `POST /api/expenses/` — create.
- `GET /api/expenses/` — list (optionally filtered, paginated).
- `GET /api/expenses/{id}/` — retrieve one.
- `PATCH /api/expenses/{id}/` — update.
- `DELETE /api/expenses/{id}/` — delete.
- All require authentication. User gets 403 Forbidden if trying to access another user's expense.

**Error cases:**
- 400 Bad Request: amount is negative, amount is not a valid Decimal, category does not exist, date is invalid.
- 401 Unauthorized: no token/session, invalid token.
- 403 Forbidden: user tries to modify another user's expense.
- 404 Not Found: expense ID does not exist.

**Accessibility:**
- Forms are keyboard navigable, labels associated.
- Error messages are clear.

---

#### 3.3 Gestion des budgets (Budget management)

**Goal:** Users set spending limits and see consumption; the app warns them when they approach or exceed a limit.

**In scope:**
- Set a budget amount for a category or globally (TBD: team to decide on granularity).
- (Optional) Set a time period for the budget: monthly, yearly, or rolling 30 days (TBD: team decision, flag in spec).
- View budget consumption: total spent in the period / budget limit, as a ratio or percentage.
- Get an alert (visual or both visual+notification, TBD) when:
  - Spending ≥ 80% of budget (warning threshold).
  - Spending ≥ 100% (overspend).
- No complex forecasting, no rollover logic, no shared budgets across users.

**Data model implications:**
- A `Budget` model with `amount` (Decimal/NUMERIC), `category` (foreign key, or null for global), `period` (e.g. "monthly", enum, TBD), `owner` (foreign key to User), timestamps.
- `Budget.amount` is always >= 0.
- Alert thresholds (80%, 100%) are hardcoded in the code for now; no per-user threshold configuration.

**In API:**
- `POST /api/budgets/` — create.
- `GET /api/budgets/` — list (scoped to logged-in user).
- `PATCH /api/budgets/{id}/` — update.
- `DELETE /api/budgets/{id}/` — delete.
- `GET /api/budgets/{id}/status/` (or similar endpoint, TBD) — return consumption data for a budget.

**UI signals:**
- Dashboard shows each budget with a progress bar or percentage.
- Color coding: green (< 80%), yellow (80–99%), red (≥ 100%).
- No email notifications (out of scope); alerts are visible on the dashboard.

**Accessibility:**
- Color is never the only signal (e.g. show text "Overspent" in addition to red).
- Progress bars have accessible labels.

---

#### 3.4 Catégories (Expense categories)

**Goal:** Users organize expenses by type (groceries, transport, entertainment, etc.).

**In scope:**
- A predefined list of categories (e.g. Groceries, Transport, Entertainment, Utilities, Other; exact list TBD).
- Users cannot create custom categories (out of scope for MVP; revisit if a user request appears).
- Categories are the same for all users (no personalization).
- Every expense must be assigned to exactly one category.

**Data model implications:**
- A `Category` model with `name` and optionally `color` for UI.
- No `owner` field — categories are global/shared.
- `Expense.category` is required (not null).

**In API:**
- `GET /api/categories/` — list all categories (no auth required; they are public/static data).
- Categories are not created, edited or deleted via API in the MVP.

---

#### 3.5 Page de confidentialité et mentions légales (Privacy and legal information page)

**Goal:** Users can read what data the app collects and how it is protected.

**In scope:**
- A static `/privacy` page, front-end only (no backend route).
- Describes: no personal data collected (before auth ships), database is configured but not populated, no cookies, no third-party integrations.
- Lists what *is* planned (accounts, expenses, budgets, categories) in future tense.
- Discloses that the app runs on development defaults (DEBUG=true, etc.).
- Contains visible placeholder tokens for legal information (entity, contact, jurisdiction, effective date) until a human fills them.
- Is accessible without login and with no network requests.
- Applies decision `0002`: all claims must be verifiable against the code.

**In API:** None. The page is static frontend content.

---

#### 3.6 Sécurité (Security)

**Goal:** Protect user data and the integrity of the application.

**In scope:**
- Password hashing (bcrypt or Django's PBKDF2).
- CSRF tokens on all state-changing forms.
- SQL injection protection (via Django ORM parameterization).
- User-scoped queries: User A cannot access User B's data via API manipulation.
- CORS: by default, only the local dev frontend (`http://localhost:5173`) is allowed (see decision `0002`).
- Rate limiting on auth endpoints (login, password reset if applicable; exact limits TBD).
- No sensitive data in logs, error responses, or API responses (e.g. no stack traces in JSON).

**Out of scope (not MVP):**
- TLS/HTTPS termination (handled by deployment infrastructure, not the application).
- OAuth / social login.
- Two-factor authentication.
- Encryption at rest (development database has no encryption configured).
- Backup and disaster recovery.
- Penetration testing.

**Applies to:** Every feature spec and implementation. The Full-Stack Development agent is responsible for implementing these; the QA & Security agent reviews them.

---

#### 3.7 Accessibilité (Accessibility)

**Goal:** The app is usable by people with disabilities, following WCAG 2.1 Level AA.

**In scope:**
- All forms have associated `<label>` elements.
- All images and icons have descriptive `alt` text.
- Color is never the only means of conveying information (e.g. a red alert also says "Overspent").
- Contrast ratio ≥ 4.5:1 for normal text, ≥ 3:1 for large text.
- All interactive elements are keyboard navigable; focus is always visible.
- Headings are real `<h1>`, `<h2>`, etc., not styled divs.
- Forms have clear, associated error messages.
- Landmarks: one `<main>` per page, `<footer>` for site-wide links, `<header>` if nav exists.
- Readable at 200% zoom without horizontal scrolling.
- Reflow and text spacing: readable on mobile and at large zoom.

**Applies to:** Every page and component. The Full-Stack Development agent implements; the QA & Security agent and the team's accessibility specialist (Clément) review.

---

#### 3.8 Infrastructure Docker (Docker-based local development)

**Goal:** Every team member can start the full stack locally with one command.

**In scope:**
- `docker-compose.yml` defines all services: Django API, SvelteKit frontend, PostgreSQL database.
- `docker compose up -d --build` starts the stack.
- `docker compose down` stops it cleanly.
- Both Django and SvelteKit development servers run inside containers.
- Environment variables are passed via `.env` file (never committed; `.env.example` is versioned).
- Database schema is created by Django migrations (run manually via `docker compose exec api python manage.py migrate`).
- Frontend build and dev server use the SvelteKit stack (Vite).

**Not included:**
- Kubernetes, production deployment manifests, CI/CD pipelines, log aggregation.
- Health checks or auto-restart policies (nice-to-have for later).

**Applies to:** The Full-Stack Development and QA & Security agents; all development happens inside containers.

### 2.3 Out-of-scope features (for "Hors périmètre MVP" section)

The final document should list and justify each exclusion. Examples:

| Feature | Why not in MVP | Revisit when |
|---------|----------------|--------------|
| Multi-user households / shared budgets | Requires complex permission model and real-time sync. Single-user MVP is faster and clearer. | After single-user flow is solid. |
| Bank API integration (Plaid, etc.) | Requires OAuth, third-party credentials, PII handling. Major complexity for limited MVP value. | Post-MVP phase 2. |
| Mobile app | Scope of work equivalent to the web app. Web-responsive design covers mobile access for MVP. | If web MVP succeeds. |
| Multiple currencies | Requires exchange rates, rounding rules, localization. Not needed for an initial English-only MVP. | Post-MVP if international. |
| Recurring expenses / bills | Nice feature but not critical for initial launch. Can be added incrementally. | Feature request backlog. |
| Email notifications | Adds SMTP configuration, email templates, unsubscribe logic. Dashboard alerts are sufficient for MVP. | Post-MVP engagement feature. |
| Data export (CSV, etc.) | Out of scope for a 4-day sprint; can be added later. | Backlog. |
| Admin dashboard / reporting | The focus is on user-facing features; admin tools are secondary. | Post-MVP if needed for business operations. |
| Customizable themes / dark mode | Nice-to-have; not core to expense tracking. Accessibility and single theme are sufficient for MVP. | Polish phase. |
| Offline mode / Progressive Web App | Requires service workers, sync logic. Not needed for a prototype. | Future if mobile is a priority. |

---

## 3. Data model overview (informational)

This section is **not** part of `docs/mvp-scope.md`; it is here to guide the Full-Stack Development agent. The MVP requires these tables (to be defined in detail in a separate data model spec):

| Table | Purpose | Key fields |
|-------|---------|-----------|
| `User` | Accounts | email (unique), password_hash, created, updated |
| `Category` | Expense types | name (unique), color (optional) |
| `Expense` | Individual transactions | user_id (FK), category_id (FK), amount (Decimal), date, description, created, updated |
| `Budget` | Spending limits | user_id (FK), category_id (FK, nullable), amount (Decimal), period (enum: month/year/rolling), created, updated |

All monetary amounts use `Decimal` / `NUMERIC` type, never float.

---

## 4. Constraints and standing rules

The following constraints from existing documentation apply to all MVP features and must be cited in `docs/mvp-scope.md`:

1. **Decimal / NUMERIC for money** (from `product-architecture.md`): Every monetary field uses PostgreSQL `NUMERIC` or Django's `DecimalField`, never `FloatField`. This is non-negotiable.

2. **Privacy page stays current** (from `decisions/0002`): Any PR that adds data collection, auth, or third-party integrations must update the privacy page in the same PR. The page must never go stale or false.

3. **Shared app shell** (from `decisions/0001`): The layout is minimal; chrome is added as needed, not in anticipation.

4. **Stack is fixed:** Django + DRF, SvelteKit, PostgreSQL, Docker Compose. Do not propose replacements.

5. **MVP scope is a boundary:** Every feature spec must reference this MVP scope document and stay within it. The Product & Architecture agent uses this to gate scope creep.

---

## 5. Tone and style guidance

The final document must:

- **Be written in French** throughout, except for code references (file paths, model names, API endpoints) and technical terms that are English-only (e.g. "CSRF", "ORM", "Decimal").
- **Be precise and verifiable:** Every claim about what is "in" or "out" of scope must be checkable. No aspirational language ("eventually we might...").
- **Avoid marketing language:** This is a technical scope document, not a pitch. "The app will track your expenses accurately" is not sufficient; say "Users can create, view, edit and delete expenses, with amounts stored as Decimal to ensure precision."
- **Follow the structure of existing specs:** Reference `docs/specs/issue-63-privacy-page.md` for tone and formatting.
- **Be proportionate:** This is a scope marker, not a 50-page requirements document. Roughly 1500–2500 words is appropriate.

---

## 6. Open questions for the team

These questions must be resolved (or flagged as "TBD") in the final document:

| Question | Why it matters | Resolution |
|----------|----------------|-----------|
| **Auth registration:** Does the MVP require email verification, or is signup immediate? | Affects complexity and time budget. | Recommend: immediate signup for speed; email verification is post-MVP. |
| **Budget period granularity:** Are budgets per category only, or can users set a global budget? If per-category, is the period always monthly, or can users choose weekly/monthly/yearly? | Affects data model and business logic. | Recommend: per-category budgets, monthly period only, to keep MVP small. Revisit for post-MVP. |
| **Alert mechanism:** Are budget alerts visual only (dashboard), or do they include in-app notifications or email? | Affects frontend and backend scope. | Recommend: visual dashboard only (color + percentage) for MVP. Notifications are post-MVP. |
| **Category list:** What is the exact list of categories? Who decides? | Affects onboarding and UX. | Recommend: hardcode 6–8 categories (Groceries, Transport, Entertainment, Utilities, Health, Dining, Shopping, Other); team decides the final list. |
| **Password reset:** Is this in MVP, or is it "contact support"? | Affects auth flow. | Recommend: "contact [[CONTACT_EMAIL]]" for MVP; password reset is post-MVP. |

---

## 7. Success criteria for this spec

The spec itself is "done" when:

- [ ] This document (the spec) is approved by the team.
- [ ] The Full-Stack Development agent has read it and confirmed they understand the expected output.
- [ ] `docs/mvp-scope.md` is written and reviewed by at least one team member.
- [ ] All sections §2.1–2.3 are present in the final document.
- [ ] The document is between 1500–2500 words.
- [ ] Every open question in §6 is either resolved (with a definitive answer in the doc) or explicitly flagged as "TBD — team decision pending".
- [ ] The tone and style are consistent with `docs/specs/issue-63-privacy-page.md`.

---

## 8. Related documents

- `docs/team.md` — team roles and responsibilities.
- `.github/agents/product-architecture.md` — how this agent uses MVP scope to gate feature specs.
- `docs/decisions/0001-shared-app-shell-layout.md` — layout rule.
- `docs/decisions/0002-privacy-claims-must-be-code-verifiable.md` — privacy page rule.
- `docs/specs/issue-63-privacy-page.md` — reference for tone and structure.
