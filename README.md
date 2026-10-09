# Cashmire

Cashmire is a budgeting/expense-tracking app built with Django + Django
REST Framework and PostgreSQL on the backend, and a SvelteKit (Svelte 5)
single-page app on the front-end, running together via Docker Compose.

## Quick start (Docker Compose)

```
cp .env.example .env
docker compose up --build
```

- Front-end: <http://localhost:5173>
- API: <http://localhost:8000/api/health/>

## Front-end

```
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173/>. You should see the heading **Cashmire**
with a French tagline, and, once logged in, a dashboard preview of your
recent expenses and budgets — see `frontend/README.md` for the full
reference, including configuration, other npm scripts, and the Docker
Compose alternative.

## Back-end

The API uses Django 5.1 with Django REST Framework (DRF). Django provides the
Python web framework, project settings, ORM, and built-in versioned migrations;
DRF provides the REST API views and responses. This keeps the backend on the
project's PostgreSQL stack without adding a separate migration tool.

Run it via `docker compose up db api` from the repo root (or the full stack
with the quick start above). The API is available at
`http://127.0.0.1:8000/`; its health endpoint is
`http://127.0.0.1:8000/api/health/`.

The OpenAPI schema (`/api/schema/`) and interactive Swagger UI
(`/api/docs/`) are available publicly only when `DJANGO_DEBUG=true`.
Both endpoints return 404 when debug mode is disabled; this does not replace
the authentication and authorization checks on application API routes.

### Run backend tests

With the `db` service available, run the complete API suite—including
registration, login, logout, and protected current-user route tests—with:

```bash
docker compose run --rm api python manage.py test api
```

This single command works from the repository root and is suitable for local
verification or CI.

### Seed local demo data

The `api` container seeds sample data for you automatically: on every
`docker compose up`, its entrypoint (`backend/entrypoint.sh`) applies
migrations, and if `DJANGO_DEBUG=true` and the database has no users yet —
i.e. the first boot against a fresh `pgdata` volume — it also runs
`manage.py seed_dev_data`. That command creates a demo account with a full
year of categorized expenses and budgets, including categories that are only
budgeted ("on budget") for some months and left untracked ("off budget") for
others, so dashboards and line charts have something meaningful to show.
Nothing is seeded on an existing volume, so your own data is never touched.

The account's credentials are printed in the `api` logs the first time it
seeds: `demo@cashmire.example` / `CashmireDemo2026!`. Change this password
before sharing a development environment. `seed_dev_data` assumes a clean
database and isn't safe to run twice (it will hit duplicate-budget errors);
to reseed, rebuild the database as described below.

For a smaller, idempotent dataset — a handful of current-month expenses and
budgets you can safely regenerate at any time — use the original demo
command instead:

```bash
docker compose run --rm api python manage.py seed_demo_data
```

Repeated runs of `seed_demo_data` update the same sample records rather than
creating duplicates. Both commands refuse to run when `DJANGO_DEBUG` is
disabled.

### Run frontend tests

```bash
cd frontend
npm install
npm test
```

`npm test` runs the Vitest suite once (`vitest run`). See `frontend/README.md`
for the other scripts.

### Run the API locally (without the `api` container)

Install Python 3.12 and Docker Compose. Copy `.env.example` to `.env` (in
PowerShell, use `Copy-Item .env.example .env`; on macOS/Linux, use
`cp .env.example .env`) — the same `.env` is used in both cases, see
[Local PostgreSQL](#local-postgresql) below.

From the repository root, create a virtual environment and install the API
dependencies:

```bash
python -m venv .venv
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

On macOS/Linux:

```bash
.venv/bin/python -m pip install -r backend/requirements.txt
```

Start PostgreSQL, apply migrations, and run the API. Use the matching Python
path from above for the last two commands:

```bash
docker compose up -d db
```

```powershell
# Windows PowerShell
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py runserver
```

```bash
# macOS/Linux
.venv/bin/python backend/manage.py migrate
.venv/bin/python backend/manage.py runserver
```

## Known limitations of the MVP

- Single currency: amounts are in euros, no currency field is stored.
- Each user has their own categories, created at registration from a fixed
  default list; categories cannot be created, edited or deleted through the
  API.
- Lists are not paginated.
- Authentication is a Django session cookie. Login is throttled per IP at
  5 requests per minute using a per-process in-memory cache
  (`docs/decisions/0004-login-rate-limiting.md`); there is no per-account
  lockout.
- Registration is not throttled and reveals whether an email is already
  registered.
- Production hardening is not configured: `DJANGO_SECRET_KEY` has a
  development fallback, `DJANGO_ALLOWED_HOSTS` defaults to `*`, and the
  secure-cookie and HTTPS settings are not enabled. Set `DJANGO_DEBUG=false`
  and your own secret outside local development.
- `/api/docs/` and `/api/schema/` are public.

See `docs/mvp-scope.md` for the full out-of-scope list and
`docs/reviews/` for the QA and security findings.

## Docs

- [`docs/specs/`](docs/specs/) — feature specs.
- [`docs/decisions/`](docs/decisions/) — architecture decision records.
- [`docs/reviews/`](docs/reviews/) — QA & security review notes.

## Local PostgreSQL

The development database runs in the `db` service using PostgreSQL 16. Copy
`.env.example` to `.env` before starting the service. Use
`Copy-Item .env.example .env` in PowerShell or `cp .env.example .env` on
macOS/Linux. The same `.env` is loaded by Django whether the API runs in the
`api` container or directly on your machine — leave `POSTGRES_HOST` unset
and Django picks the right one: the Compose hostname `db` when it's
reachable, otherwise `localhost`.

```bash
docker compose up -d db
docker compose exec db pg_isready -U cashmire -d cashmire
```

The example publishes PostgreSQL on `localhost:5432`. Set `POSTGRES_DB`,
`POSTGRES_USER`, and `POSTGRES_PASSWORD` in `.env` to configure the database;
set `POSTGRES_PORT` to change the port published on the host.

## Database migrations

Cashmire uses Django's built-in migration framework for PostgreSQL schema
changes. The versioned migrations in `backend/api/migrations/` create the
project's database schema; no manual SQL setup is required. Commit each
migration with the model changes it represents.

### Rebuild the development database from an empty PostgreSQL instance

The following commands discard the Compose database volume and **permanently
delete all data in that local development database**. Do not run them if you
need to keep its data. Run them from the repository root after creating `.env`
from `.env.example` as described in [Local PostgreSQL](#local-postgresql):

```bash
docker compose down --volumes --remove-orphans
docker compose up -d --build db
docker compose up -d --build api
```

The first command removes the existing database volume; PostgreSQL creates a
new empty database when the `db` service starts. The API waits for PostgreSQL's
healthcheck, then its entrypoint applies every committed migration in order
before the server starts — safe to run again, since Django skips migrations
already recorded as applied — and, in a `DJANGO_DEBUG=true` environment,
seeds the [sample demo data](#seed-local-demo-data) described above because
the fresh volume has no users yet.

To start the full application once the `api` container is up:

```bash
docker compose up -d frontend
```

After changing models, create a migration and apply it:

```bash
docker compose exec api python manage.py makemigrations api
docker compose exec api python manage.py migrate
```

To run these commands outside Docker, execute them from `backend/` with the
Python dependencies installed and PostgreSQL available using the settings in
`.env` (see [Run the API locally](#run-the-api-locally-without-the-api-container)).
