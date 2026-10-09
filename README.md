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

### Run backend tests

With the `db` service available, run the complete API suite—including
registration, login, logout, and protected current-user route tests—with:

```bash
docker compose run --rm api python manage.py test api
```

This single command works from the repository root and is suitable for local
verification or CI.

### Seed local demo data

With the `db` service running and a development `.env` copied from
`.env.example` (`DJANGO_DEBUG=true`), create a synthetic demo account with
sample categories, current-month expenses, and budgets:

```bash
docker compose run --rm api python manage.py seed_demo_data
```

For a newly created account, the command prints the initial credentials:
`demo@cashmire.example` / `CashmireDemo2026!`. The account and amounts are
synthetic, and repeated runs update the same sample records rather than
creating duplicates. The command refuses to run when `DJANGO_DEBUG` is
disabled. Change the demo password before sharing a development environment.

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
docker compose exec api python manage.py migrate
```

The first command removes the existing database volume; PostgreSQL creates a
new empty database when the `db` service starts. The API waits for PostgreSQL's
healthcheck, and Django applies every committed migration in order. The
migration command is safe to run again; Django skips migrations already
recorded as applied.

To start the full application after the migrations have completed:

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
