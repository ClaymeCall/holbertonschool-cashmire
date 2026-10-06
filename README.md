# Cashmire

## Backend

The API uses Django 5.1 with Django REST Framework (DRF). Django provides the
Python web framework, project settings, ORM, and built-in versioned migrations;
DRF provides the REST API views and responses. This keeps the backend on the
project's PostgreSQL stack without adding a separate migration tool.

### Run the API locally

Install Python 3.12 and Docker Compose. Copy `.env.example` to `.env` (in
PowerShell, use `Copy-Item .env.example .env`; on macOS/Linux, use
`cp .env.example .env`). The local settings load this file automatically.
The example config connects to PostgreSQL on `localhost`; Compose overrides
the host to `db` for the API container.

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

The API is available at `http://127.0.0.1:8000/`; its health endpoint is
`http://127.0.0.1:8000/api/health/`.

## Database migrations

Cashmire uses Django's built-in migration framework for PostgreSQL schema
changes. The `api` app's initial migration establishes its migration history;
it has no schema operations because the app does not define models yet.
Versioned migration files belong in `backend/api/migrations/` and should be
committed with the model changes they represent.

Start the database and API services, then apply all pending migrations:

```bash
docker compose up -d --build
docker compose exec api python manage.py migrate
```

After changing models, create a migration and apply it:

```bash
docker compose exec api python manage.py makemigrations api
docker compose exec api python manage.py migrate
```

To run these commands outside Docker, execute them from `backend/` with the
Python dependencies installed and PostgreSQL available using the settings in
`.env`.
