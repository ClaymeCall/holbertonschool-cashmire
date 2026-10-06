# Specification: Write `.github/copilot-instructions.md` with verified project context

**Issue:** #8  
**Status:** Specification only — implementation by Full-Stack Development agent

## Problem Statement

Coding agents working on Cashmire need accessible, verified documentation of the project's architecture, conventions, commands, and rules. Currently, this context is scattered across multiple files and agent definitions. A single `.github/copilot-instructions.md` file should consolidate the information every agent needs to know before writing code: why the stack was chosen, how to run tests and migrations, critical security/data rules, and the exact commands that work in the Docker environment.

## Acceptance Criteria

1. **Architecture section** describes the chosen stack (Python/Django for the API in `backend/`, SvelteKit for the front-end in `frontend/`, PostgreSQL for persistence, Docker Compose for local orchestration) and briefly states **why** each was chosen (not just a list).

2. **Commands and operations** section lists every command a developer or agent needs to run, verified against the actual repository:
   - Docker Compose startup and teardown
   - Database migrations (create, apply, rollback)
   - Running tests (backend, frontend)
   - Local development server startup
   - All paths are absolute or relative from the repository root, not invented

3. **Coding conventions** section lists:
   - Monetary values must use `Decimal` / `NUMERIC` (never float)
   - Ownership checks on every query touching user-owned resources (no unauthorized data access)
   - No secrets or credentials ever committed to the repository
   - Branch naming and commit message format (reference to Conventional Commits per `docs/git-workflow.md`)
   - Test files colocated with code they test

4. **Repository layout** section shows the directory structure with a brief description of each top-level directory and key subdirectories:
   - `backend/` → Django app structure, apps, migrations
   - `frontend/` → SvelteKit routes and components
   - `docs/` → Specs, decisions, API design, agentic log
   - `.github/agents/` → Agent definitions

5. **Development rules** section states:
   - Human review is required before any PR is merged (no agent-generated code ships unreviewed)
   - All tests must pass locally before submitting code
   - The three agentic agents (Product & Architecture, Full-Stack Development, QA & Security) and the orchestrator workflow are explained briefly
   - Breaking changes require explicitly documented `BREAKING CHANGE:` footer in commits

6. **Language and style** matches the existing agent files (English, technical tone, consistent formatting with the `.github/agents/*.md` files).

7. **File location and scope** is `.github/copilot-instructions.md` only; this is a documentation-only task for agents to reference before writing code, not a piece of application code.

## Verified Commands and Paths

All commands listed in the output file must be tested against the actual repository structure. The following have been verified:

### Docker Compose
- **Startup (build and start all services):** `docker compose up -d --build`
- **View logs:** `docker compose logs -f`
- **Stop services:** `docker compose down`
- **Services running:** `db` (PostgreSQL 16), `api` (Django on port 8000), `frontend` (SvelteKit on port 5173)
- **Environment file:** `.env` (see `.env.example` for all variables)

### Django Management Commands (inside the `api` service)
- **Apply migrations:** `docker compose exec api python manage.py migrate`
- **Create migrations from models:** `docker compose exec api python manage.py makemigrations api`
- **Run backend tests:** `docker compose exec api python manage.py test`
- **Inspect Django shell:** `docker compose exec api python manage.py shell`
- **Manage static files:** `docker compose exec api python manage.py collectstatic`

### Frontend (Node/npm, inside the `frontend` service)
- **Dev server:** `docker compose exec frontend npm run dev` (or already running on port 5173)
- **Build:** `docker compose exec frontend npm run build`
- **Run tests:** `docker compose exec frontend npm run test`
- **Install dependencies:** `docker compose exec frontend npm install` (auto-run at container startup)

### Database Access
- **PostgreSQL client:** `docker compose exec db psql -U cashmire -d cashmire` (username and database default to "cashmire")
- **Connection string:** `postgresql://cashmire:cashmire@db:5432/cashmire` (inside containers)

### Outside Docker (if running locally with Python/Node installed)
- **Backend:** Commands above run from `backend/` directory with `.env` file present and PostgreSQL available on `POSTGRES_HOST` (default localhost)
- **Frontend:** Commands above run from `frontend/` directory with `VITE_API_URL=http://localhost:8000` set

### Repository Layout (Verified Paths)

```
holbertonschool-cashmire/
├── backend/                           # Django REST API
│   ├── cashmire/                      # Project settings and routing
│   │   ├── settings.py                # Django configuration (DB, apps, middleware, CORS)
│   │   ├── urls.py                    # Root URL router
│   │   ├── asgi.py / wsgi.py          # ASGI/WSGI application entry points
│   │   └── __init__.py
│   ├── api/                           # Main API app
│   │   ├── models.py                  # Database models (User, Expense, Budget, Category)
│   │   ├── views.py                   # DRF viewsets and views
│   │   ├── serializers.py             # DRF serializers (when created)
│   │   ├── urls.py                    # API routes
│   │   ├── apps.py                    # App config
│   │   ├── migrations/                # Versioned schema changes
│   │   │   ├── 0001_initial.py
│   │   │   └── __init__.py
│   │   └── __init__.py
│   ├── manage.py                      # Django CLI entry point
│   ├── requirements.txt                # Python dependencies (Django, DRF, psycopg2, cors-headers)
│   ├── Dockerfile                     # Builds Python 3.12 image, runs migrate and runserver
│   └── __pycache__/ (gitignored)
│
├── frontend/                          # SvelteKit web UI
│   ├── src/
│   │   ├── app.html                   # HTML template
│   │   ├── routes/
│   │   │   ├── +layout.js             # Root layout config (ssr = false)
│   │   │   ├── +layout.svelte         # Root layout (app shell with footer)
│   │   │   ├── +page.svelte           # Home page
│   │   │   ├── privacy/
│   │   │   │   ├── +page.svelte       # Privacy/terms page
│   │   │   │   └── page.test.js       # Privacy page tests (vitest + @testing-library/svelte)
│   │   │   └── [future routes here]
│   │   └── lib/                       # Shared components and utilities (starts empty, grows as needed)
│   ├── package.json                   # Node dependencies (SvelteKit, Vite, Svelte, vitest, testing-library)
│   ├── vite.config.js                 # Vite bundler config (jsdom for tests, browser condition resolution)
│   ├── svelte.config.js               # SvelteKit config
│   ├── Dockerfile                     # Builds Node 22-alpine image, runs npm install and npm run dev
│   ├── node_modules/ (gitignored)
│   ├── build/ (gitignored)
│   └── .svelte-kit/ (gitignored)
│
├── docs/                              # Project documentation
│   ├── specs/                         # Agentic feature specifications (one per feature)
│   │   ├── issue-3-git-workflow.md
│   │   ├── issue-8-copilot-instructions.md (this file)
│   │   ├── issue-63-privacy-page.md
│   │   └── [future specs]
│   ├── reviews/                       # Agentic QA reviews (one per feature)
│   │   ├── issue-63-privacy-page.md
│   │   └── [future reviews]
│   ├── decisions/                     # Architecture decision records
│   │   ├── 0001-shared-app-shell-layout.md (SvelteKit +layout.svelte design)
│   │   ├── 0002-privacy-claims-must-be-code-verifiable.md
│   │   └── [future ADRs]
│   ├── api-design.md                  # REST API contract (created as needed)
│   ├── mvp-scope.md                   # What is/isn't in MVP (created as needed)
│   ├── agentic-log.md                 # Log of meaningful agentic work and decisions
│   └── [other documentation]
│
├── .github/
│   ├── agents/                        # Agentic agent definitions (read by orchestrator)
│   │   ├── product-architecture.md    # Spec writer agent
│   │   ├── fullstack-development.md   # Implementation agent
│   │   ├── qa-security.md             # Review agent
│   │   └── [future agents]
│   └── copilot-instructions.md        # ← This file (context for all agents)
│
├── agentic/                           # Agentic orchestration (SDK + scripts)
│   ├── orchestrator.py                # Main orchestrator (parses .github/agents/*.md and runs all three agents)
│   ├── tracing.py                     # Langfuse integration for observability
│   ├── requirements.txt                # Python deps for orchestrator (claude-agent-sdk, langfuse)
│   ├── README.md                      # Usage guide (how to invoke orchestrator)
│   └── [other orchestration code]
│
├── docker-compose.yml                 # Local development environment (db, api, frontend services)
├── .env.example                       # Environment variables template (PostgreSQL, Django, Vite, Anthropic API, Langfuse)
├── .gitignore                         # Gitignored: .env, __pycache__, node_modules, .venv, etc.
├── README.md                          # Project overview and migration quick-start
└── [other repository files]
```

## Key Development Rules

### Money / Decimal
- All monetary fields in the database must use `NUMERIC` / `Decimal` in Python, never `FloatField`.
- This applies to amounts in `Expense`, `Budget`, and related models.

### Ownership & Authorization
- Every query that touches user-owned data (expenses, budgets, categories) must filter by the authenticated user.
- No endpoint should allow one user to read, create, update, or delete another user's resources.
- This must be verified in every PR that touches user data.

### Secrets & Credentials
- Never commit `.env` to the repository.
- All secrets (API keys, database passwords, Django secret keys) go in `.env`, not in code.
- `.env.example` lists all required variables with placeholder values only.
- `.env` is in `.gitignore` and must not be added to version control under any circumstances.

### Branch & Commit Conventions
- Branch name format: `<type>/<issue>-<slug>` (e.g., `feat/8-copilot-instructions`, `fix/42-budget-rounding`)
- Commit message format: Conventional Commits (see `docs/git-workflow.md` for full spec)
  - Example: `feat(api): add budget warning endpoint`
  - Breaking changes: add `!` before the colon or use `BREAKING CHANGE:` footer
- One issue = one branch; one logical change = one commit; one feature = one PR targeting `main`

### Human Review Required
- No code is merged to `main` without human review and approval (status "Approve" on GitHub)
- Agents can propose changes, but a human must decide whether to merge
- The agentic workflow (Understand → Plan → Delegate → Verify → Review) is not a bypass for human judgment
- A failing test in an agent review is evidence, not proof — the team runs the full suite before merge

### Testing
- **Backend:** `docker compose exec api python manage.py test` must pass before submitting
- **Frontend:** `docker compose exec frontend npm run test` must pass before submitting
- Test files are colocated with the code they test:
  - Backend: `backend/api/` app, alongside models/views (typically via Django's TestCase)
  - Frontend: `frontend/src/routes/` next to `.svelte` files (vitest + @testing-library/svelte)
- Every new or changed endpoint must have tests covering:
  - Happy path (success case)
  - Error cases (validation failure, not found, unauthorized, forbidden)

### Agentic Workflow
- The project uses three specialized agents orchestrated by `agentic/orchestrator.py`:
  1. **Product & Architecture:** Writes specs (`docs/specs/<slug>.md`)
  2. **Full-Stack Development:** Implements code based on specs
  3. **QA & Security:** Reviews implementation against specs and writes findings (`docs/reviews/<slug>.md`)
- To run a feature through the workflow:
  ```bash
  python agentic/orchestrator.py "<task description>" --slug issue-<number>-<short-name>
  ```
- Every meaningful agent-assisted work is logged in `docs/agentic-log.md`

### API Design
- REST conventions: `GET`, `POST`, `PUT`, `PATCH`, `DELETE` on RESTful paths
- Authentication: TBD (see spec when created)
- Response format: JSON only (configured in Django settings: `JSONRenderer`)
- CORS: Configured for `http://localhost:5173` in development (see `DJANGO_CORS_ALLOWED_ORIGINS` in settings.py)
- Error responses must not leak stack traces, database errors, or configuration values

## Content for `.github/copilot-instructions.md`

The file to be created at `.github/copilot-instructions.md` must include:

1. **Introduction** — Who should read this (coding agents and developers) and what it covers

2. **Architecture & Stack** section with:
   - Chosen technologies and why (Django for robustness, DRF for REST, SvelteKit for modern UI, PostgreSQL for ACID, Docker Compose for reproducibility)
   - High-level system diagram (text or ASCII is fine)
   - Key design decisions (client-side rendering by default per decision 0001, CORS for SPA-to-API)

3. **Repository Layout** section:
   - The directory tree above, with brief descriptions
   - Links to key files (`docs/git-workflow.md`, `docs/decisions/`, `docs/mvp-scope.md` when it exists)

4. **Commands That Work** section:
   - All verified commands listed above, grouped by context (Docker Compose, Django, frontend, database access)
   - Notes on when to use each (development vs. production mentality, though this is dev-only for now)

5. **Coding Conventions** section:
   - Monetary values → `Decimal` / `NUMERIC`
   - Ownership checks required on user data queries
   - No secrets committed
   - Branch naming and Conventional Commits format
   - Test cohabitation with code

6. **Development Rules** section:
   - Human review requirement before merge
   - All tests must pass locally
   - Agentic workflow overview (what the orchestrator does, where specs and reviews live)
   - Breaking changes require explicit `BREAKING CHANGE:` footer

7. **How to Contribute** section (brief):
   - Read the relevant spec in `docs/specs/<issue-slug>.md` before starting
   - Create a branch per `docs/git-workflow.md`
   - Run tests, commit with Conventional Commits, open a PR targeting `main`
   - Wait for human review before merge

8. **Troubleshooting / FAQ** (optional, can grow over time):
   - Common setup issues (Docker not running, port conflicts, etc.)
   - How to reset the database, rebuild containers, clear caches
   - Where to log issues (GitHub Issues)

9. **Links to Reference Documents**:
   - `docs/git-workflow.md` — Full git and PR workflow
   - `docs/agentic-log.md` — Log of agentic decisions and past runs
   - `docs/decisions/` — Architecture decision records
   - `.github/agents/*.md` — Agent definitions
   - `agentic/README.md` — How to run the orchestrator

## Out of Scope

- **Application code changes** — This is documentation only; no code is written as part of this task.
- **Code generation tools configuration** — GitHub Copilot (the GitHub autocomplete tool) is separate from this project's agentic workflow and is not configured here.
- **IDE / editor setup** — This file documents project context, not individual developer environments.
- **Deployment or CI/CD** — The project is in local development; production deployment rules are out of scope.
- **Changes to `.github/agents/*.md`** — These agent definitions are maintained separately; this task consolidates their outputs.

## Risks & Open Questions

1. **Language & audience overlap:** The file must be clear to both humans (first-time developers) and agents reading it as context. An early draft should be reviewed by a human developer unfamiliar with the project to confirm it is understandable.

2. **Maintenance:** As the project grows (new frameworks, new agents, new conventions), this file must be kept in sync. It is easier for humans to remember to update if it is treated as a living document and linked from the main README and agent files.

3. **Example commands in containers:** All commands are shown using `docker compose exec`, which assumes the container is already running. A note should clarify this, plus the outside-Docker alternative for developers running natively.

4. **Test framework details:** The spec assumes `unittest` for Django and `vitest` for SvelteKit but does not detail how to write tests. That belongs in the Full-Stack Development agent's scope; this file just lists what commands work.

## Implementation Notes for Full-Stack Development Agent

When writing `.github/copilot-instructions.md`:

1. **Verify every command** by running it in the actual Docker environment or describing exactly what it does.
2. **Keep the file concise** — agents and humans both have finite context windows; verbose prose is less useful than clear structure and examples.
3. **Use consistent formatting** with the existing `.github/agents/*.md` files (YAML frontmatter is not needed; Markdown headers and lists are fine).
4. **Include at least one complete example** of a common workflow (e.g., "Add a new API endpoint":
   - Read `docs/specs/issue-X-your-feature.md`
   - Create branch `feat/X-short-name`
   - Edit `backend/api/models.py`, create a migration, run it
   - Edit `backend/api/views.py` and `urls.py` for the new route
   - Write tests in the same app
   - Run `docker compose exec api python manage.py test`
   - Edit `frontend/src/routes/[feature]/+page.svelte` if needed
   - Commit, push, open PR with `Closes #X` in the description)
5. **Link to references** rather than duplicating rules from `docs/git-workflow.md` or `.github/agents/*.md`.

## Files to be Created

- **`.github/copilot-instructions.md`** — The consolidated context file for agents and developers (this is the only file created).

No other files are modified or created by this task.
