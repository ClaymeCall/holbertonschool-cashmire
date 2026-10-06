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

Open <http://localhost:5173/>. You should see the heading **Cashmire** and
an `API status` line — see `frontend/README.md` for the full reference,
including configuration, other npm scripts, and the Docker Compose
alternative.

## Back-end

Django + DRF, run via `docker compose up db api` from the repo root (or see
`backend/` for a standalone setup). Not documented further here — this is
outside the scope of the front-end skeleton issue that created this file.

## Docs

- [`docs/specs/`](docs/specs/) — feature specs.
- [`docs/decisions/`](docs/decisions/) — architecture decision records.
- [`docs/reviews/`](docs/reviews/) — QA & security review notes.

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
