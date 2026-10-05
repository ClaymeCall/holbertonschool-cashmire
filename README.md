# Cashmire

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
