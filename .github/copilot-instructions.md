# Cashmire: Development Guidance for Coding Agents and Developers

This document consolidates the essential context every developer and coding agent needs before writing code for Cashmire: why the stack was chosen, how to run tests and migrations, critical security and data rules, and the exact commands that work in the Docker environment.

## Architecture & Stack

Cashmire uses a modern, layered architecture optimized for local development and future scale:

- **Backend:** Python + Django + Django REST Framework (DRF) on port 8000
  - Why: Robust ORM, built-in admin, well-tested migration system, and DRF's serializers reduce boilerplate for REST APIs.
  
- **Frontend:** SvelteKit + Vite on port 5173
  - Why: Lightweight server-side kit with an excellent dev experience, fast HMR, and minimal bundle size. Client-side rendering by default (per [decision 0001](../docs/decisions/0001-shared-app-shell-layout.md)).

- **Database:** PostgreSQL 16 on port 5432
  - Why: ACID guarantees, jsonb support for future expansion, and proven reliability for production data.

- **Local Orchestration:** Docker Compose
  - Why: Reproducible environment across devices; no "works on my machine" problems. All containers run the full stack: `db`, `api`, `frontend`.

### High-Level System Diagram

```
┌─────────────────────────────────────────────────┐
│  Web Browser (localhost:5173)                   │
│  SvelteKit + Vite (client-side rendering)       │
└────────────────┬────────────────────────────────┘
                 │ HTTP/JSON
                 ↓
┌─────────────────────────────────────────────────┐
│  Django REST API (localhost:8000)               │
│  - Views, Serializers, Models, Migrations       │
│  - CORS configured for localhost:5173           │
└────────────────┬────────────────────────────────┘
                 │ SQL/TCP
                 ↓
┌─────────────────────────────────────────────────┐
│  PostgreSQL (localhost:5432)                    │
│  - Persisted schema + data                      │
└─────────────────────────────────────────────────┘
```

## Repository Layout

```
holbertonschool-cashmire/
├── backend/                           # Django REST API
│   ├── cashmire/                      # Project settings and routing
│   │   ├── settings.py                # Django config: DB, apps, middleware, CORS
│   │   ├── urls.py                    # Root URL router
│   │   ├── asgi.py / wsgi.py          # ASGI/WSGI entry points
│   │   └── __init__.py
│   ├── api/                           # Main API app
│   │   ├── models.py                  # Database models (User, Expense, Budget, Category)
│   │   ├── views.py                   # DRF viewsets and views
│   │   ├── serializers.py             # DRF serializers (created as features are added)
│   │   ├── urls.py                    # API routes (/api/expenses, etc.)
│   │   ├── apps.py                    # App config
│   │   ├── migrations/                # Versioned schema changes (one per model change)
│   │   │   ├── 0001_initial.py        # Schema foundation (created before models)
│   │   │   └── __init__.py
│   │   └── __init__.py
│   ├── manage.py                      # Django CLI entry point
│   ├── requirements.txt               # Python deps: Django, DRF, psycopg2, cors-headers
│   ├── Dockerfile                     # Builds Python 3.12, runs migrate + runserver
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
│   │   └── lib/                       # Shared components and utilities
│   ├── package.json                   # Node deps: SvelteKit, Vite, vitest, testing-library
│   ├── vite.config.js                 # Vite config (jsdom for tests, browser conditions)
│   ├── svelte.config.js               # SvelteKit config
│   ├── Dockerfile                     # Builds Node 22-alpine, runs npm install + dev
│   ├── node_modules/ (gitignored)
│   ├── build/ (gitignored)
│   └── .svelte-kit/ (gitignored)
│
├── docs/                              # Project documentation
│   ├── specs/                         # Feature specifications (one per GitHub issue)
│   │   ├── issue-3-git-workflow.md
│   │   ├── issue-8-copilot-instructions.md (context for agents)
│   │   ├── issue-63-privacy-page.md
│   │   └── [future specs]
│   ├── reviews/                       # QA & Security review findings (one per spec)
│   │   ├── issue-63-privacy-page.md
│   │   └── [future reviews]
│   ├── decisions/                     # Architecture decision records (ADRs)
│   │   ├── 0001-shared-app-shell-layout.md (SvelteKit +layout.svelte design)
│   │   ├── 0002-privacy-claims-must-be-code-verifiable.md
│   │   └── [future ADRs]
│   ├── agentic-log.md                 # Log of meaningful agentic work
│   ├── git-workflow.md                # Git and PR conventions (Conventional Commits, branch naming)
│   ├── team.md                        # Team roles and decision-making
│   └── [other documentation]
│
├── .github/
│   ├── agents/                        # Agent definitions (read by orchestrator.py)
│   │   ├── product-architecture.md    # Spec-writing agent
│   │   ├── fullstack-development.md   # Implementation agent
│   │   ├── qa-security.md             # Review agent
│   │   └── copilot-instructions.md    # ← This file
│   └── [workflows and other GitHub config]
│
├── agentic/                           # Agentic orchestration (Claude Agent SDK)
│   ├── orchestrator.py                # Main orchestrator: parses agents/*.md and runs cycle
│   ├── tracing.py                     # Langfuse integration for observability
│   ├── requirements.txt               # Python deps: claude-agent-sdk, langfuse
│   ├── README.md                      # How to run the orchestrator
│   └── [other orchestration code]
│
├── compose.yaml                       # Local dev environment (db, api, frontend)
├── .env.example                       # Environment variables template (secrets, API keys, URLs)
├── .gitignore                         # Excluded: .env, __pycache__, node_modules, .venv, build artifacts
├── README.md                          # Quick-start guide and migration hints
└── [other repo files]
```

## Commands That Work

All commands assume the Docker containers are running (`docker compose up -d --build`). Containers run the full development environment with hot-reload; changes to code are reflected immediately.

### Docker Compose (Foundation)

Start all services, build images, and apply migrations:

```bash
docker compose up -d --build
```

View logs from all services in real time:

```bash
docker compose logs -f
```

Follow logs from a specific service (e.g., `api`):

```bash
docker compose logs -f api
```

Stop all services (preserves data):

```bash
docker compose down
```

Destroy all services and reset the database (data lost):

```bash
docker compose down -v
```

### Django Management (Backend)

Apply pending migrations:

```bash
docker compose exec api python manage.py migrate
```

Create a migration from model changes:

```bash
docker compose exec api python manage.py makemigrations api
```

Create a migration without model changes (empty, for data or schema tasks):

```bash
docker compose exec api python manage.py makemigrations <app_name> --empty --name <description>
```

Run the backend test suite:

```bash
docker compose exec api python manage.py test
```

Open the Django interactive shell:

```bash
docker compose exec api python manage.py shell
```

Collect static files (rarely needed in development):

```bash
docker compose exec api python manage.py collectstatic --noinput
```

### Frontend (Node/npm)

The dev server is already running on port 5173 in the frontend container. To install dependencies or run commands inside the container:

```bash
docker compose exec frontend npm install
```

Run the frontend test suite:

```bash
docker compose exec frontend npm run test
```

Build for production:

```bash
docker compose exec frontend npm run build
```

### Database Access

Connect to PostgreSQL directly with `psql`:

```bash
docker compose exec db psql -U cashmire -d cashmire
```

Connection string (for tools inside containers):

```
postgresql://cashmire:cashmire@db:5432/cashmire
```

Inside the `db` container environment, `POSTGRES_HOST=db`, `POSTGRES_USER=cashmire`, `POSTGRES_PASSWORD=cashmire`, `POSTGRES_DB=cashmire`.

### Running Commands Outside Docker

If you have Python, Node, and PostgreSQL installed locally:

**Backend** (from `backend/` directory):

```bash
python manage.py makemigrations api
python manage.py migrate
python manage.py test
```

Set `.env` with `POSTGRES_HOST=localhost` and ensure PostgreSQL is running on port 5432.

**Frontend** (from `frontend/` directory):

```bash
npm install
npm run dev
npm run test
npm run build
```

Set `VITE_API_URL=http://localhost:8000` in `.env` to point to the backend.

## Coding Conventions

### Monetary Values

**Rule:** All monetary fields must use `Decimal` in Python and `NUMERIC` in PostgreSQL. Never use `FloatField`.

```python
# Correct
from decimal import Decimal
from django.db import models

class Expense(models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # PostgreSQL: NUMERIC

# Incorrect (never do this)
class Expense(models.Model):
    amount = models.FloatField()  # Floating-point rounding errors
```

Why: Floating-point arithmetic causes rounding errors; Decimal preserves exactness for financial data.

### Ownership & Authorization

**Rule:** Every query that touches user-owned data (expenses, budgets, categories, etc.) must filter by the authenticated user. No endpoint should allow one user to read, create, update, or delete another user's resources.

```python
# Correct: filter by current user
def get_user_expenses(request):
    return Expense.objects.filter(user=request.user)

# Incorrect: allows one user to see another's data
def get_all_expenses(request):
    return Expense.objects.all()
```

This must be verified in every PR that touches user data. See [QA & Security agent responsibilities](./qa-security.md) for the audit checklist.

### No Secrets in Code

**Rule:** Never commit `.env`, API keys, database passwords, Django secret keys, or any credential to the repository. All secrets go in `.env`, which is in `.gitignore`.

```bash
# Correct: .env (local, never committed)
DJANGO_SECRET_KEY=your-actual-secret-key-here
ANTHROPIC_API_KEY=sk-...

# Correct: .env.example (placeholder values only)
DJANGO_SECRET_KEY=change-me
ANTHROPIC_API_KEY=
```

Before committing, run `git status` to ensure `.env` is untracked (not staged). If `.env` was added by accident, remove it with `git rm --cached .env` and commit that removal.

### Branch Naming & Commit Messages

Follow Conventional Commits as documented in [docs/git-workflow.md](../docs/git-workflow.md):

- **Branch name:** `<type>/<issue>-<slug>` (e.g., `feat/42-budget-warning`, `fix/15-login-redirect`)
  - Types: `feat`, `fix`, `docs`, `refactor`, `chore`, `test`, `style`, `build`, `ci`, `perf`, `revert`
  - Always include the GitHub issue number
  - Slug: 2–5 lowercase words, no accents, no spaces

- **Commit message:** `<type>[scope]: <description>` (e.g., `feat(api): add budget warning endpoint`)
  - Type in lowercase
  - Optional scope in parentheses (e.g., `api`, `frontend`, `db`)
  - Description short and imperative
  - Breaking changes: add `!` before `:` or use `BREAKING CHANGE:` footer

Example:

```
feat(api): add expense filtering by category

Allows users to filter their expenses by category on the API.

Closes #42
```

### Test Cohabitation

**Rule:** Test files live next to the code they test, not in a separate `tests/` directory.

- **Backend:** `backend/api/tests.py` or test methods in the same Django app
- **Frontend:** `frontend/src/routes/+page.test.js` next to `+page.svelte`

Use Django's `TestCase` for backend models and views; use vitest + `@testing-library/svelte` for frontend components.

```python
# backend/api/tests.py
from django.test import TestCase
from .models import Expense

class ExpenseTestCase(TestCase):
    def test_expense_creation(self):
        expense = Expense.objects.create(amount=10.50)
        self.assertEqual(expense.amount, 10.50)
```

```javascript
// frontend/src/routes/privacy/page.test.js
import { render } from "@testing-library/svelte";
import Page from "./+page.svelte";

describe("Privacy page", () => {
  it("renders", () => {
    const { container } = render(Page);
    expect(container).toBeInTheDocument();
  });
});
```

## Development Rules

### Human Review Required

**Rule:** No code is merged to `main` without human review and approval (GitHub "Approve" status).

Agents can propose changes and pass automated tests, but a human must decide whether to merge. The agentic workflow automates delegation, not accountability. An agent test pass is evidence, not proof — the team runs the full suite before merge.

See [docs/git-workflow.md](../docs/git-workflow.md) for the full PR and review process.

### All Tests Must Pass Locally

Before submitting code for review:

```bash
# Backend
docker compose exec api python manage.py test

# Frontend
docker compose exec frontend npm run test
```

Both suites must exit with status 0. A PR with failing tests will be rejected and returned to the implementer.

### Agentic Workflow

The project uses three specialized agents orchestrated by `agentic/orchestrator.py`, working together in a cycle:

1. **Product & Architecture** (`product-architecture.md`)
   - Writes a spec (`docs/specs/<issue-slug>.md`) from a feature request
   - Defines acceptance criteria, data model changes, API routes, and error cases
   - Does not write code

2. **Full-Stack Development** (`fullstack-development.md`)
   - Reads the spec and implements it across `backend/` and `frontend/`
   - Creates models, migrations, views, serializers, routes, and tests
   - Runs tests and reports pass/fail

3. **QA & Security** (`qa-security.md`)
   - Reviews the implementation against the spec
   - Audits for security (OWASP Top 10), accessibility, and ownership checks
   - Writes findings to `docs/reviews/<issue-slug>.md`
   - Does not edit code; findings go to the Full-Stack Development agent for fixes

To run a feature through the full cycle:

```bash
python agentic/orchestrator.py "Add a monthly budget warning banner" --slug issue-42-budget-warning
```

Every meaningful agent-assisted work is logged in `docs/agentic-log.md`. See [agentic/README.md](../agentic/README.md) for full orchestrator documentation.

### Breaking Changes

**Rule:** Any change to an API endpoint, data model, or public interface must be explicitly documented with a `BREAKING CHANGE:` footer in the commit.

```
feat!: rename /api/transactions to /api/expenses

BREAKING CHANGE: all clients must update their requests to use /api/expenses instead of /api/transactions
```

Or equivalently, with a `!` before the colon:

```
feat(api)!: rename /api/transactions to /api/expenses
```

## How to Contribute

1. **Start with a spec:** Read the relevant spec in `docs/specs/issue-<number>-<slug>.md` before writing code. If no spec exists, file a GitHub issue describing the feature; the Product & Architecture agent will create one.

2. **Create a branch:** Follow [docs/git-workflow.md](../docs/git-workflow.md):
   ```bash
   git switch main
   git pull
   git switch -c feat/42-your-feature
   ```

3. **Implement the feature:**
   - Edit `backend/api/` for models, views, serializers, and migrations
   - Edit `frontend/src/` for routes, components, and page logic
   - Write tests cohabiting with the code

4. **Test locally:**
   ```bash
   docker compose exec api python manage.py test
   docker compose exec frontend npm run test
   ```

5. **Commit with Conventional Commits:**
   ```bash
   git add backend/api/models.py backend/api/migrations/...
   git commit -m "feat(api): add expense model

Stores user expenses with amount, date, and category.

Closes #42"
   ```

6. **Push and open a PR:**
   ```bash
   git push -u origin feat/42-your-feature
   ```
   
   On GitHub, open a PR to `main`. In the description:
   ```
   Closes #42

   ## Summary
   Add support for user expenses.

   ## How to test
   docker compose exec api python manage.py test
   docker compose exec frontend npm run test

   ## Spec
   docs/specs/issue-42-expenses.md
   ```

7. **Wait for human review:** At least one team member reviews the diff, runs the tests, and approves before merge.

## API Design

Cashmire follows REST conventions:

- **Methods:** `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- **Paths:** RESTful (e.g., `/api/expenses`, `/api/expenses/<id>`, `/api/categories`)
- **Authentication:** TBD (see the spec when created)
- **Response format:** JSON only (configured in Django: `JSONRenderer`)
- **CORS:** Configured for `http://localhost:5173` in development (see `DJANGO_CORS_ALLOWED_ORIGINS` in `backend/cashmire/settings.py`)
- **Error responses:** Never leak stack traces, database errors, or configuration values. Return a clean error message and HTTP status.

Example error response:

```json
{
  "error": "Expense not found",
  "status": 404
}
```

Not:

```json
{
  "error": "IntegrityError: relation \"api_expense\" does not exist",
  "traceback": "..."
}
```

## Troubleshooting & FAQ

### Docker or Port Conflicts

**Problem:** `docker compose up` fails with "port 5173 already in use" or "cannot connect to db".

**Solution:**
```bash
# Kill containers and volumes, start fresh
docker compose down -v
docker compose up -d --build

# Or manually free ports
lsof -ti :5173 | xargs kill -9  # frontend
lsof -ti :8000 | xargs kill -9  # api
lsof -ti :5432 | xargs kill -9  # db
```

### Database State

**Problem:** Migrations fail or schema is corrupted.

**Solution:**
```bash
# Destroy and recreate the database
docker compose down -v
docker compose up -d --build
docker compose exec api python manage.py migrate
```

### Tests Failing Locally But Pass in CI

**Problem:** Tests pass in the Docker container but fail when run outside.

**Solution:** Ensure environment variables are set correctly:
```bash
# Check .env is present and has POSTGRES_HOST=localhost (or 127.0.0.1)
cat .env | grep POSTGRES
```

### Clear Caches

**Problem:** "Module not found" or stale imports in Python or Node.

**Solution:**
```bash
# Python
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete

# Node
rm -rf frontend/node_modules frontend/.svelte-kit frontend/build
docker compose exec frontend npm install

# Both
docker compose exec api python manage.py migrate --fake-initial  # if schemas mismatch
```

### How to Report Issues

File a GitHub Issue with:
- A clear title (e.g., "Login endpoint returns 500")
- Steps to reproduce
- Expected vs. actual behavior
- Environment (e.g., Docker, local Python 3.12, Node 22)

The Product & Architecture agent reads issues and turns them into specs.

## Reference Links

- **Git & PR Workflow:** [docs/git-workflow.md](../docs/git-workflow.md) — Branch naming, Conventional Commits, PR requirements
- **Agentic Log:** [docs/agentic-log.md](../docs/agentic-log.md) — Record of agent runs, decisions, and outcomes
- **Architecture Decisions:** [docs/decisions/](../docs/decisions/) — Design rationale for key choices (e.g., rendering, privacy)
- **Agent Definitions:** [.github/agents/](./agents/) — Full prompt and scope for each agent
- **Orchestrator Guide:** [agentic/README.md](../agentic/README.md) — How to run the agentic workflow
- **Quick Start:** [README.md](../README.md) — Minimal setup and migration quick-start
