# Cashmire front-end — SvelteKit (Svelte 5) single-page app.

## Prerequisites

Node 22 or newer. `npm` ships with Node, so no separate install step is
needed for it.

Two supported ways to get Node:

- `devenv shell` from the repo root, which provides `nodejs_26` (see
  `devenv.nix`).
- A local Node install (22+) from [nodejs.org](https://nodejs.org) or your
  platform's package manager.

## Run it locally

```
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173/>. You should see the heading **Cashmire** with
its French tagline — the page rendering means the front-end is up; it does
not depend on the backend. The footer link **Confidentialité et mentions
légales** and the header nav link **Confidentialité** both go to
<http://localhost:5173/privacy>. The footer's **État de l'API** link goes to
<http://localhost:5173/health>, which reports whether the backend is
reachable.

## Note on the port

`vite.config.js` sets `strictPort: true` on port `5173`. If the port is
already in use, the dev server exits with an error instead of silently
choosing `5174`. Free the port rather than looking for another one.

## Note on the backend

The front-end runs standalone; only pages that call the API (login,
register, the `/health` status page, the dashboard once logged in, etc.)
need the backend. Start it with `docker compose up db api` from the repo
root. `backend/cashmire/settings.py` allows the CORS origin
`http://localhost:5173` by default, so the front-end dev server can reach
it without further configuration.

## Configuration

Copy `.env.example` to `.env` (or `.env.local`) inside `frontend/` and set
`VITE_API_URL` to the origin of the API (scheme included, no trailing
slash, no `/api` suffix). It defaults to `http://localhost:8000` when
unset or blank, so the app works with no `.env` file at all. Only
variables prefixed with `VITE_` are visible to client code — that prefix is
what tells Vite to inline the value into the browser bundle. See
`frontend/.env.example` for the full contract.

## Other commands

- `npm run build` — builds a production bundle.
- `npm run preview` — serves the production build locally, for a final
  check before deploying.
- `npm test` — runs the test suite once (`vitest run`).

## Running under Docker Compose

From the repo root:

```
docker compose up frontend
```

Same URL, <http://localhost:5173/>. The difference is which env file is
read: a bare `npm run dev` reads `frontend/.env`, while Compose injects the
repo-root `.env` into the `frontend` container as process environment
variables (`env_file: .env` in `compose.yaml`). Keep both files'
`VITE_API_URL` values the same — see the root `.env.example` for details.
