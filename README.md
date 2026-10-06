# Cashmire

## Local PostgreSQL

The development database runs in the `db` service using PostgreSQL 16. Copy
`.env.example` to `.env` before starting the service. Use
`Copy-Item .env.example .env` in PowerShell or `cp .env.example .env` on
macOS/Linux. The same settings file is loaded by Django when running the API
directly on your machine.

```bash
docker compose up -d db
docker compose exec db pg_isready -U cashmire -d cashmire
```

The example publishes PostgreSQL on `localhost:5432`, so a locally running API
connects to `localhost`. The API container uses the Compose service hostname
`db` and PostgreSQL's internal port `5432`. Set `POSTGRES_DB`,
`POSTGRES_USER`, and `POSTGRES_PASSWORD` in `.env` to configure the database;
set `POSTGRES_PORT` to change the port published on the host.

## Database migrations

Cashmire uses Django's built-in migration framework for PostgreSQL schema
changes. The `api` app's initial migration establishes its migration history;
it has no schema operations because the app does not define models yet.
Versioned migration files belong in `backend/api/migrations/` and should be
committed with the model changes they represent.

Start the database and API services, then apply all pending migrations. The API
waits for PostgreSQL's healthcheck before starting:

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
