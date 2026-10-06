# SPEC — Initialize the SvelteKit front-end project skeleton

- **Issue:** #15 "Initialize the SvelteKit front-end project skeleton"
- **Status:** Proposal. Not approved. A human must read this before the
  Full-Stack Development agent is asked to implement it. The team may accept,
  amend or reject any part of it.
- **Author:** Product & Architecture agent
- **Scope:** `frontend/` only, plus two root-level documentation/config files
  (`.env.example`, and a new root `README.md` section pointer). No backend
  change, no model, no migration, no new dependency.
- **Codebase surveyed at:** worktree branch `agentic/issue-15-svelte-skeleton`,
  tip commit `cc64e87`

---

## 0. What already exists (survey, not assumption)

This issue reads as "create the frontend project", but a SvelteKit app is
already scaffolded and already renders. The work is therefore **completing the
skeleton**, not bootstrapping it. Implementers must not re-run
`npm create svelte@latest` or regenerate the project — that would clobber
working code and the `/privacy` page delivered by issue #63.

Current state, verified file by file:

| Path | Current content | Relevance |
|------|-----------------|-----------|
| `frontend/package.json` | name `cashmire-frontend`, `"type": "module"`. Scripts: `dev` (`vite dev --host 0.0.0.0`), `build`, `preview`, `test` (`vitest run`). devDeps: `@sveltejs/adapter-auto`, `@sveltejs/kit` ^2.9.0, `@sveltejs/vite-plugin-svelte` ^4, `@testing-library/svelte` ^5, `jsdom` ^25, `svelte` ^5.2.3, `vite` ^5.4.11, `vitest` ^2.1.4 | Scripts already exist; the gap is that nothing documents them. **No `typescript`, no `svelte-check`, no `@testing-library/jest-dom`, no lint/format tooling.** |
| `frontend/jsconfig.json` | `allowJs` + `checkJs` + `strict`, extends `./.svelte-kit/tsconfig.json` | The project is **checked JavaScript, not TypeScript**. Drives §4.3. |
| `frontend/svelte.config.js` | `adapter-auto`, nothing else | No `kit.alias` additions needed; `$lib` already resolves to `frontend/src/lib/`. |
| `frontend/vite.config.js` | `sveltekit()` plugin; `server.host 0.0.0.0`, `port 5173`, `strictPort: true`; `test.environment: "jsdom"`, `test.globals: true`; `resolve.conditions: ["browser"]` under `VITEST` | Port is fixed and will **fail loudly** rather than drift if 5173 is taken (`strictPort`). Vitest is configured here, not in a separate config. |
| `frontend/src/app.html` | standard shell, `lang="en"`, `data-sveltekit-preload-data="hover"` | Untouched by this issue. |
| `frontend/src/routes/+layout.js` | `export const ssr = false;` | App is **client-rendered app-wide**. Keep. |
| `frontend/src/routes/+layout.svelte` | Svelte 5 runes: `let { children } = $props();`, `{#if children}{@render children()}{/if}`, then a `<footer>` with one link to `/privacy`, plus scoped `<style>` for the footer | This is the "current minimal footer" the issue refers to. Base for §4.2. |
| `frontend/src/routes/+page.svelte` | `<main><h1>Cashmire</h1><p>API status: {status}</p></main>`; in `onMount`, reads `import.meta.env.VITE_API_URL ?? "http://localhost:8000"` and `fetch`es `` `${apiUrl}/api/health/` `` | **The env var and fallback already exist here, inline and un-shared.** This is the duplication §4.3 removes. |
| `frontend/src/routes/privacy/+page.svelte` | static privacy page, owns its own `<main>`, `<svelte:head>` title | Route that the new nav must link to. |
| `frontend/src/routes/privacy/page.test.js` | vitest + `@testing-library/svelte`; renders the layout with a `createRawSnippet` stub for `children`; T-4 asserts the footer link to `/privacy` | **Existing test convention to follow**, and a test this issue must not break. Note its header comment: it was authored without `npm` available and has never been executed. |
| `frontend/Dockerfile` | `node:22-alpine`, `npm install`, `EXPOSE 5173`, `CMD ["npm","run","dev"]` | Compose path to the dev server. |
| `frontend/.gitignore` | `node_modules`, `.svelte-kit`, `build` | **Does not ignore `.env.local` / `.env.*.local`.** Gap, see §4.4. |
| `docker-compose.yml` | `frontend` service builds `./frontend`, `env_file: .env`, ports `5173:5173`, bind-mounts `./frontend` with an anonymous volume on `/app/node_modules`, `depends_on: api` | Compose injects root `.env` as **process env**, which is why `VITE_API_URL` works there today. |
| `.env.example` (root) | already contains `VITE_API_URL=http://localhost:8000` (line 12) | See §4.4 — this works for Compose but **not** for a bare `npm run dev`. |
| `.gitignore` (root) | pattern `.env` (unanchored, so matches at any depth) | `frontend/.env` is already ignored; `frontend/.env.local` is not. |
| `devenv.nix` | provides `nodejs_26`, `python3`, `postgresql` | Node comes from devenv; document that. |
| **`README.md` (root)** | **does not exist.** Only `agentic/README.md` exists. | There is currently **no documentation anywhere** of how to run the frontend. This is the whole of requirement 1. |
| Backend contract | `backend/cashmire/urls.py` mounts `api/`; `backend/api/urls.py` has `health/`; `backend/api/views.py` returns `{"status": "ok"}` | Health URL is exactly `GET /api/health/`, **with a trailing slash** (Django `APPEND_SLASH`). Drives §4.3's path-joining rule. |
| Models / migrations | `backend/api/` has no `models.py` and no `migrations/` | §2 holds. |

Two findings from the survey that change the shape of the work:

1. **`api.ts` is not implementable as literally requested.** TypeScript is not a
   dependency and the project is configured as checked JS (`jsconfig.json`,
   `checkJs: true`). Adding TS would mean new devDependencies, a `tsconfig`
   migration and preprocessing changes — scope this issue should not absorb. The
   helper is therefore `frontend/src/lib/api.js` with JSDoc types, which
   `checkJs` already type-checks. See §4.3 and open question Q-1.
2. **`VITE_API_URL` in the root `.env.example` is misleading for local dev.**
   Vite's `envDir` defaults to the Vite project root, i.e. `frontend/`. A
   developer running `npm run dev` inside `frontend/` gets **no** value from the
   repo-root `.env`; it only works under Compose because `env_file:` makes it a
   real process env var (Vite does expose `VITE_`-prefixed process env). Today
   that gap is invisible because `+page.svelte` has an inline `?? "http://localhost:8000"`
   fallback. §4.4 fixes the declaration properly instead of relying on the
   fallback by accident.

---

## 1. Problem statement and acceptance criteria

### 1.1 User-facing goal

> As a developer joining Cashmire, I want to clone the repo, follow one
> documented command sequence, and get a running front-end that already has a
> navigable shell and a single configurable place where the API lives — so that
> adding the first real feature page means writing that page, not re-deciding
> how navigation, env config and API calls work.

Secondary, user-visible goal: a visitor can move between every page of the app
using visible navigation, instead of only reaching `/privacy` through a footer
link and `/` through the browser's back button.

### 1.2 Acceptance criteria

Each criterion is pass/fail.

| ID | Criterion | How it is checked |
|----|-----------|-------------------|
| AC-1 | `frontend/README.md` exists and documents, in order: prerequisite Node version, `npm install`, `npm run dev`, the exact URL to open (`http://localhost:5173/`), and what you should see on success. | Manual: follow it verbatim on a clean clone. |
| AC-2 | Root `README.md` exists and contains a "Front-end" section with the install + dev-server commands (including the `cd frontend` step) and a link to `frontend/README.md`. | Manual. |
| AC-3 | Both READMEs document the Docker Compose alternative (`docker compose up frontend`) and state which of the two paths reads which env file. | Manual, cross-checked against `docker-compose.yml` and §4.4. |
| AC-4 | `frontend/src/routes/+layout.svelte` renders a `<header>` containing a `<nav>` with links to every existing route (`/` and `/privacy`), then the page content, then the existing footer. | Automated: §6 T-1, T-2, T-3. Manual: links visible on both pages. |
| AC-5 | The link in the nav matching the current URL is marked as current with `aria-current="page"`, and no other nav link is. | Automated: §6 T-4. |
| AC-6 | The footer still contains a link with an accessible name matching `/privacy/i` whose `href` is exactly `/privacy`. The existing `privacy/page.test.js` T-4 still passes unmodified. | Automated: run `npm test`. |
| AC-7 | `frontend/src/lib/api.js` exists and exports `API_BASE_URL` and an `apiFetch` function per the contract in §4.3. | Automated: §6 T-5 .. T-10. |
| AC-8 | `API_BASE_URL` resolves from `import.meta.env.VITE_API_URL`, falling back to `http://localhost:8000` when that is unset or empty, with any trailing slash stripped. | Automated: §6 T-5, T-6. |
| AC-9 | `frontend/src/routes/+page.svelte` no longer reads `import.meta.env` or calls `fetch` directly; it calls the shared helper and still displays the API status. | Manual diff + automated §6 T-11. Regression: page still shows `ok` with the API up. |
| AC-10 | `frontend/.env.example` exists, declares `VITE_API_URL` with the local-dev default and a comment, and the root `.env.example` entry is annotated to say it is the Compose path. | Manual. |
| AC-11 | `frontend/.gitignore` ignores `.env`, `.env.*` and un-ignores `.env.example`. | Manual: `git status` after creating a local `frontend/.env.local` shows nothing. |
| AC-12 | `npm run build` completes with no error. | Manual / CI. |
| AC-13 | `npm test` runs and every test passes, including the pre-existing privacy tests. | Manual / CI. Note the caveat in §6.0. |
| AC-14 | No new runtime or dev dependency is added to `frontend/package.json`. | Manual diff. Exception requires team sign-off, see Q-1/Q-4. |
| AC-15 | Keyboard-only navigation reaches every nav link and the footer link in DOM order, with a visible focus ring. | Manual, §5.3. |

### 1.3 Explicit non-goals

See §7.

---

## 2. Data model delta

**None.** No table, column, constraint, index or relationship is added, changed
or removed.

Verifiable: `backend/api/` contains `__init__.py`, `apps.py`, `urls.py`,
`views.py` and no `models.py`; there is no `backend/api/migrations/` directory.

The project rule that **monetary values are always `Decimal` / `NUMERIC`, never
float** is not exercised by this issue — it introduces no monetary field. It is
restated here because the API client in §4.3 is the chokepoint through which
every future money-carrying payload will pass: see §4.3.6, which forbids the
helper from doing any numeric coercion for exactly that reason.

---

## 3. API routes delta

**No new or changed backend route.** This issue consumes one route that already
exists:

| Method | Path | Auth | Request | Success response | Error cases the client must handle |
|--------|------|------|---------|------------------|-------------------------------------|
| GET | `/api/health/` | None | — | `200` `{"status": "ok"}` | Network/DNS failure or API down → `TypeError` from `fetch`; wrong origin → CORS failure (also surfaces as a `fetch` rejection); `404` if the path is wrong (e.g. trailing slash dropped and `APPEND_SLASH` does not apply to the method); `5xx` if Django errors; non-JSON body (e.g. a proxy's HTML error page) → JSON parse failure. |

Client-side error handling for all of these is specified in §4.3.4. The existing
home page currently collapses every one of them into the string
`"unreachable"`; that user-visible behaviour is preserved (AC-9) — the point of
this issue is that the *handling* moves into one shared, tested place.

---

## 4. File-by-file changes

### 4.1 Documentation of how to run it (requirement 1)

#### 4.1.1 NEW `frontend/README.md`

Authoritative location for front-end instructions. Must contain these sections,
with this content:

1. **Title + one-line purpose** — "Cashmire front-end — SvelteKit (Svelte 5)
   single-page app."
2. **Prerequisites** — Node 22 or newer. State the two supported ways to get
   it: `devenv shell` (which provides `nodejs_26`, per `devenv.nix`), or a local
   Node install. State that `npm` ships with Node.
3. **Run it locally** — exactly this block, and nothing that contradicts
   `package.json`:

   ```
   cd frontend
   npm install
   npm run dev
   ```

   Followed by: "Open <http://localhost:5173/>. You should see the heading
   **Cashmire** and a line reading `API status: ok` when the backend is running,
   or `API status: unreachable` when it is not — either way, the page rendering
   means the front-end is up. The footer link **Privacy & legal** and the header
   nav link **Privacy** both go to <http://localhost:5173/privacy>."
4. **Note on the port** — `vite.config.js` sets `strictPort: true` on port
   5173, so if the port is busy the dev server exits with an error instead of
   silently choosing 5174. Tell the reader to free the port rather than look for
   another one.
5. **Note on the backend** — the front-end runs standalone; only the API status
   line needs the backend. Point at `docker compose up db api` and note that
   `backend/cashmire/settings.py` allows the CORS origin
   `http://localhost:5173` by default.
6. **Configuration** — link to §4.4's contract: copy `.env.example` to `.env`,
   `VITE_API_URL`, the default, and the fact that a `VITE_` prefix is what makes
   a variable visible to client code.
7. **Other commands** — `npm run build`, `npm run preview`, `npm test`, each
   with one line on what it does. Do not invent scripts that are not in
   `package.json`.
8. **Running under Docker Compose** — `docker compose up frontend` from the
   repo root, same URL, and the env-file difference from §4.4.3.

#### 4.1.2 NEW root `README.md`

The repo has no root README at all today. Create a short one — this issue is not
a licence to write full project documentation:

- One-paragraph description of Cashmire and the stack (Django + DRF,
  PostgreSQL, SvelteKit, Docker Compose). Do not restate or extend product
  scope.
- **Quick start (Docker Compose)**: copy `.env.example` → `.env`, then
  `docker compose up --build`; front-end on <http://localhost:5173>, API on
  <http://localhost:8000/api/health/>.
- **Front-end** section: the `cd frontend && npm install && npm run dev` block,
  the URL, the success check, and a link to `frontend/README.md` as the
  authoritative reference.
- **Back-end** section: one line plus a pointer; do not document the backend in
  detail here, it is outside this issue.
- **Docs** section: links to `docs/specs/`, `docs/decisions/`, `docs/reviews/`.

If the team would rather not have a root README created by this issue, the
fallback is that AC-2 is dropped and `frontend/README.md` alone satisfies
requirement 1. Flagged as Q-2.

### 4.2 Base layout and navigation shell (requirement 2)

#### 4.2.1 EDIT `frontend/src/routes/+layout.svelte`

Keep the Svelte 5 runes style already in the file (`$props()`, `{@render}`) —
do not convert to `<slot>`; `svelte` is ^5 and the existing test passes a
`children` snippet via `createRawSnippet`.

New document order:

1. `<header>` containing `<nav aria-label="Main">` with an unordered list of
   links.
2. The page content: `{#if children}{@render children()}{/if}` — the existing
   guard stays, because `privacy/page.test.js` renders the layout with a stub
   snippet and other tests may render it with none.
3. The existing `<footer>` with the `/privacy` link, **unchanged in markup and
   accessible name**, so AC-6 holds and the existing T-4 keeps passing.

Nav link set — exactly the routes that exist today, no placeholder links to
unbuilt pages:

| Label | href | Notes |
|-------|------|-------|
| Cashmire | `/` | Brand/home link. Must be a real `<a>`, not a heading, and must be the first focusable element in the header. |
| Home | `/` | See Q-3: whether the brand link alone suffices or a separate "Home" item is wanted. Default in this spec: **include both**, with the brand link given `aria-hidden="false"` plain text and the nav list carrying `Home` and `Privacy`, because a brand-only home link is a convention users discover rather than read. |
| Privacy | `/privacy` | Same destination as the footer link; duplication between header and footer is intentional and accepted. |

Required behaviour and constraints:

- **Active link marking.** Use SvelteKit's `page` state to compare the current
  pathname with each link's href and set `aria-current="page"` on the match.
  Exact-match for `/`; for other routes, match the pathname exactly as well
  (there are no nested routes yet — do not build prefix-matching logic for
  hypothetical children). `aria-current` must drive the visual active style via
  a CSS attribute selector, so the accessible and visual states cannot diverge.
  The implementer picks the current, non-deprecated API for reading the page
  store/state in the installed `@sveltejs/kit` version — do not guess between
  `$app/stores` and `$app/state`; check what the installed version documents.
- **No `<main>` in the layout.** Decision 0001 point 4 is explicit that pages
  own their own `<main>`. Both existing pages already render one. Do not add a
  `<main>` to the layout; do not remove the pages'.
- **Styling stays component-scoped** in the layout's `<style>` block. Decision
  0001 point 6 defers a global stylesheet; this issue does not introduce
  `src/app.css`, a CSS reset or design tokens. Keep the footer's existing
  colours/border and match the header to them (`#0b3d91` link colour, `#c8c8c8`
  border) so the shell looks deliberate without a token system.
- **Focus visibility.** The footer already styles `a:focus-visible` with a 3px
  outline; apply the same treatment to header/nav links (AC-15).
- **Layout must not fetch anything.** No API call, no store subscription to data
  — it is chrome only. (Privacy test T-5 asserts zero network requests on the
  privacy page; a fetching layout would break the spirit of that and of issue
  #63's AC-7.)
- **No new dependency**, no icon library, no CSS framework (AC-14).

#### 4.2.2 UPDATE `docs/decisions/0001-shared-app-shell-layout.md`

Decision 0001 point 2 says, in writing: "no header bar, no logo, no nav menu".
This issue deliberately overrides that. The implementer must **not** silently
contradict an accepted decision record. Add a short, dated amendment section to
`0001` (status becomes `Proposed — amended by #15`) recording:

- what changed (header + nav added),
- why (two routes exist and both are now reachable from anywhere; #15 asks for a
  shell beyond the footer),
- what is unchanged (points 3, 4, 5, 6 — `+layout.js` coexistence, pages own
  `<main>`, per-route page options, component-scoped styling).

Writing that amendment is a docs change and is inside this agent's scope; if the
team prefers a new ADR `0003` that supersedes `0001` point 2 instead of an
in-place amendment, that is an acceptable amendment to this spec (Q-5).

### 4.3 Shared API client helper (requirement 3)

#### 4.3.1 NEW `frontend/src/lib/api.js`

Located under `frontend/src/lib/`, so it is importable as `$lib/api` — the
`$lib` alias is already provided by SvelteKit and needs no config change.
`frontend/src/lib/` does not exist yet and is created by this file.

File extension is `.js`, not `.ts`, per the §0 finding. Types are expressed in
JSDoc, which `jsconfig.json` (`checkJs: true`, `strict: true`) already checks.

#### 4.3.2 Exports (the contract)

```js
/** Resolved base URL for the Cashmire API, without a trailing slash. */
export const API_BASE_URL: string;

/**
 * Build an absolute API URL from a path.
 * @param {string} path  Path relative to the API root; leading slash optional.
 * @returns {string}
 */
export function apiUrl(path);

/**
 * Thrown when the API responds with a non-2xx status.
 * Carries the HTTP status and the parsed (or raw) error body.
 */
export class ApiError extends Error {
  status;   // number
  url;      // string
  body;     // unknown — parsed JSON when the body was JSON, else the raw text
}

/**
 * fetch wrapper: resolves the URL against API_BASE_URL, sets JSON headers,
 * JSON-encodes a plain-object body, and rejects on non-2xx.
 * @param {string} path
 * @param {RequestInit & { body?: unknown }} [options]
 * @returns {Promise<unknown>} parsed JSON, or null for 204/empty bodies
 */
export async function apiFetch(path, options);
```

The three names `API_BASE_URL`, `apiUrl` and `apiFetch` are the public surface.
Anything else in the file is module-private. Callers must never read
`import.meta.env.VITE_API_URL` themselves — that is the whole point (AC-9).

#### 4.3.3 Base URL resolution rules

1. Read `import.meta.env.VITE_API_URL`.
2. Treat `undefined`, `null` and a whitespace-only string as "not set".
3. When not set, fall back to the literal `http://localhost:8000` — the same
   default already used by `+page.svelte` and already written in the root
   `.env.example`. Keep the three in sync.
4. Strip any trailing `/` from the resolved value, so `http://localhost:8000/`
   and `http://localhost:8000` behave identically.
5. Resolution happens once at module scope. It is a build-time-inlined constant
   under Vite, so there is nothing to re-evaluate at runtime.
6. Do **not** throw when the var is missing — local dev must work with no `.env`
   file at all, which is the behaviour today.

`apiUrl(path)` joins with exactly one `/` between base and path, and **preserves
the caller's trailing slash**. Django's routes are declared with trailing
slashes (`health/`), so `apiFetch("/api/health/")` must request
`http://localhost:8000/api/health/` verbatim — the helper must not add,
normalise away, or "tidy" a trailing slash. A test pins this (§6 T-7).

#### 4.3.4 `apiFetch` behaviour, including every error case

| Situation | Required behaviour |
|-----------|--------------------|
| 2xx with JSON body | resolve with the parsed JSON |
| `204 No Content`, or 2xx with an empty body | resolve with `null` |
| 2xx with a body that is not valid JSON | reject with `ApiError` (`status` = the real status, `body` = the raw text). Do not return a half-parsed value. |
| 400 / 422 validation failure | reject with `ApiError`, `status` 400/422, `body` = parsed DRF error object so a caller can map field errors |
| 401 unauthenticated | reject with `ApiError`, `status` 401. The helper does **not** redirect, clear state, or know about auth — there is no auth in the codebase yet. Out of scope (§7). |
| 403 forbidden | reject with `ApiError`, `status` 403 |
| 404 not found | reject with `ApiError`, `status` 404 |
| 5xx | reject with `ApiError`, `status` as given |
| network failure / API down / CORS rejection | let `fetch`'s own `TypeError` propagate unchanged, or wrap it in `ApiError` with `status: 0` — **pick one and document it in a file-top comment**; the spec's preference is to wrap with `status: 0` so callers have exactly one error type to catch. |
| caller passes a plain-object `body` | JSON-stringify it and set `Content-Type: application/json` |
| caller passes `FormData`/`Blob`/string | pass through untouched and do **not** set `Content-Type` |
| caller passes their own `headers` | merge, with caller's values winning |
| caller passes `signal`, `method`, `credentials`, etc. | forwarded to `fetch` unchanged |

Also required:

- Default `method` is `GET`.
- `Accept: application/json` on every request.
- Do **not** set `credentials: "include"` by default — there is no cookie auth
  yet and silently sending credentials cross-origin is a security decision, not
  a skeleton detail (Q-6).
- No retry, no caching, no timeout, no interceptor chain. If a timeout is wanted
  later it goes in via `AbortSignal` from the caller.

#### 4.3.5 EDIT `frontend/src/routes/+page.svelte`

Replace the inline env read and raw `fetch` with the helper:

- remove `const apiUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";`
- remove the direct `fetch(...)` / `res.json()` pair
- `import { apiFetch } from "$lib/api";` and call it with `"/api/health/"` inside
  the existing `onMount`
- keep the exact user-visible strings: initial `"checking..."`, success shows
  the response's `status` field, any failure shows `"unreachable"`
- the `catch` must now catch `ApiError` as well as anything else; keep it broad

Everything else on the page stays, including its `<main>` and `<h1>`.

#### 4.3.6 Money rule (forward-looking, binding on the helper)

`apiFetch` returns parsed JSON and must apply **no numeric coercion of any
kind** — no `Number()`, no `parseFloat`, no "normalise amounts" step, ever. The
backend will serialise `NUMERIC` money fields as JSON strings; a helper that
helpfully turned them into JS floats would silently reintroduce float money
across the whole app. Add this as a comment in the file so a future contributor
does not "improve" it. Decimal-aware formatting is a future, separate concern
(§7).

### 4.4 Env var contract (requirement 3, config half)

#### 4.4.1 The contract

| Name | `VITE_API_URL` |
|------|----------------|
| Consumed by | `frontend/src/lib/api.js` only |
| Exposed to client code because | the `VITE_` prefix is what Vite inlines into the client bundle; a differently-named variable would be invisible to browser code |
| Read as | `import.meta.env.VITE_API_URL` |
| Value | origin of the Cashmire API, scheme included, **no** trailing slash and **no** `/api` suffix (the `/api` prefix belongs to the paths callers pass) |
| Required | No |
| Default when unset/blank | `http://localhost:8000` |
| Local dev value | `http://localhost:8000` |
| Compose value | `http://localhost:8000` — the browser, not the `frontend` container, makes the request, so this must be the host-published port and **not** `http://api:8000` |
| Consequence of a wrong value | every API call fails as a network/CORS error; the home page shows `API status: unreachable` |

A changed value requires a dev-server restart: Vite inlines `import.meta.env` at
build/serve time.

#### 4.4.2 NEW `frontend/.env.example`

Committed, documents the variable, and is the file a developer copies:

- a header comment: copy this file to `frontend/.env` (or `.env.local`) for a
  bare `npm run dev`; only `VITE_`-prefixed variables reach client code; never
  put a secret in a `VITE_` variable because it ships in the browser bundle
- `VITE_API_URL=http://localhost:8000`
- a comment stating the no-trailing-slash, no-`/api`-suffix rule and that the
  app works with this file absent, thanks to the fallback

#### 4.4.3 EDIT root `.env.example`

`VITE_API_URL` already exists on line 12. Do not remove it — Compose's
`env_file: .env` is how the `frontend` service gets it. Add a comment above it:
that this entry serves the Docker Compose path, that a bare `npm run dev` inside
`frontend/` reads `frontend/.env` instead (Vite's `envDir` is the Vite project
root), that the two should be kept to the same value, and that it must be a
host-reachable URL because the browser issues the request.

Both READMEs must say which path reads which file (AC-3).

**Rejected alternative:** setting `envDir: ".."` in `frontend/vite.config.js` so
one root `.env` serves both. It removes the duplication but points the
front-end's env loader at a file holding `DJANGO_SECRET_KEY` and
`ANTHROPIC_API_KEY`. Only `VITE_`-prefixed values are exposed to the client, so
it is not a leak today, but it makes the blast radius of one future typo
(`VITE_ANTHROPIC_API_KEY`) a published secret. Not worth it for a skeleton.
Recorded as Q-7 if the team disagrees.

#### 4.4.4 EDIT `frontend/.gitignore`

Currently `node_modules`, `.svelte-kit`, `build`. Add:

```
.env
.env.*
!.env.example
```

Root `.gitignore`'s unanchored `.env` already covers `frontend/.env`, but not
`frontend/.env.local` — which is the file Vite users most often create and the
one most likely to hold a real URL or token. Belt and braces, locally visible.

### 4.5 Files that must NOT change

- `frontend/src/routes/+layout.js` — `ssr = false` stays (decision 0001 point 3).
- `frontend/src/routes/privacy/+page.svelte` and `privacy/page.test.js` — issue
  #63's deliverables. The layout change must leave both passing untouched.
- `frontend/src/app.html`, `svelte.config.js`, `frontend/Dockerfile`,
  `docker-compose.yml` — no change needed for any AC here.
- `frontend/vite.config.js` — no change expected. If the implementer believes one
  is needed (e.g. a `test.setupFiles`), that is a deviation to raise, not to make
  silently.
- Anything under `backend/`.
- `frontend/package.json` — scripts and dependencies unchanged (AC-14).

---

## 5. Non-functional requirements

### 5.1 Accessibility

- One `<nav>` with `aria-label="Main"`; links in a `<ul>`/`<li>`.
- Current page marked with `aria-current="page"` (AC-5), and the active visual
  style driven off that attribute.
- Landmarks after this change: `banner` (header), the page's own `main`,
  `contentinfo` (footer). No duplicate or nested `main`.
- Link text is self-describing out of context ("Privacy", not "here").
- Visible `:focus-visible` outline on every link (AC-15).
- Nav must be usable at a 320px viewport width — wrap the list; **do not** build
  a hamburger menu, drawer or JS toggle for two links (§7).

### 5.2 Performance / footprint

No new dependency, no web font, no icon set, no third-party asset, no analytics.
The layout issues zero network requests.

### 5.3 Manual verification script

1. `cd frontend && npm install && npm run dev`, open `http://localhost:5173/`.
2. Header nav shows **Cashmire**, **Home**, **Privacy**; footer shows
   **Privacy & legal**.
3. "Home" carries `aria-current="page"` and the active style; "Privacy" does not.
4. Click **Privacy** → `/privacy` renders with the same header and footer, and
   the current marker has moved.
5. Tab from page load: focus reaches brand, Home, Privacy, then page links, then
   the footer link, each with a visible ring.
6. With the backend down the home page shows `API status: unreachable`; with
   `docker compose up db api` it shows `API status: ok`.
7. Stop the dev server, set `VITE_API_URL=http://localhost:9999` in
   `frontend/.env`, restart → `unreachable`. Devtools Network shows the request
   went to `http://localhost:9999/api/health/`. Remove the file, restart → `ok`.
8. Narrow the window to 320px: nav wraps, nothing is clipped or horizontally
   scrolling.
9. `npm run build` succeeds; `npm test` is green.

---

## 6. Tests to add alongside the code

### 6.0 Honest note on test execution

`frontend/src/routes/privacy/page.test.js` carries a header comment saying it was
written but never executed, because `npm` was unavailable in the environment that
authored it. **That must not repeat.** The implementer of #15 is expected to
actually run `npm install && npm test` (Node is available via `devenv shell`, see
`devenv.nix`). If the suite genuinely cannot be run, say so explicitly in the PR
with the exact command and failure — do not let unexecuted tests accumulate, and
expect QA to treat an unrun suite as a blocker rather than a detail.

A bonus of running the suite: it is the first real execution of the #63 tests,
and the first chance to find out whether they pass.

### 6.1 NEW `frontend/src/lib/api.test.js`

Colocated with the module, matching the existing colocation convention. Pure
unit tests with a stubbed `globalThis.fetch` (`vi.spyOn` / `vi.stubGlobal`) — no
live server, no backend dependency.

| ID | Asserts |
|----|---------|
| T-5 | `API_BASE_URL` is `http://localhost:8000` when `VITE_API_URL` is unset |
| T-6 | a configured value is used, and a trailing slash on it is stripped |
| T-7 | `apiUrl("/api/health/")` and `apiUrl("api/health/")` both yield `<base>/api/health/` — **trailing slash preserved**, no double slash |
| T-8 | `apiFetch` on a 200 + JSON body resolves with the parsed object, and called `fetch` exactly once with the expected absolute URL |
| T-9 | non-2xx rejects with `ApiError` carrying the right `status` and parsed `body` — one case each for 400, 401, 403, 404, 500 |
| T-10 | a `fetch` rejection (network down) surfaces as the documented single error shape; and a 204 resolves with `null` |
| T-10b | a plain-object `body` is JSON-stringified with `Content-Type: application/json`; `FormData` is passed through with no `Content-Type` set |

Stubbing `import.meta.env` for T-5/T-6 needs care: the module reads it at module
scope, so tests must use `vi.stubEnv` plus `vi.resetModules()` + dynamic
`import()` per case, or the implementer may expose a module-private
`resolveBaseUrl(env)` and test that directly while `API_BASE_URL` stays the
public export. Either is acceptable; the second is simpler and is the spec's
suggestion.

### 6.2 NEW `frontend/src/routes/layout.test.js`

Follows `privacy/page.test.js`: `@testing-library/svelte` + `createRawSnippet`
for the `children` prop. No `@testing-library/jest-dom` matchers — it is not
installed, and the #63 review already preferred doing without it.

| ID | Asserts |
|----|---------|
| T-1 | a `navigation` role is present, and it contains links with `href` `/` and `/privacy` |
| T-2 | the `children` snippet's content is rendered **between** the header and the footer (assert document order, e.g. via `compareDocumentPosition` or `container` structure — not merely "it appears somewhere") |
| T-3 | a `contentinfo`/footer link with an accessible name matching `/privacy/i` and `href="/privacy"` still exists (the footer survived the refactor) |
| T-4 | with the current path mocked as `/`, exactly one nav link has `aria-current="page"` and it is the home link; with it mocked as `/privacy`, the marker is on the privacy link |
| T-4b | rendering the layout issues zero `fetch` calls |

T-4 requires mocking whichever page store/state module the implementation uses
(`vi.mock` on `$app/stores` or `$app/state`). If that mock turns out to be
disproportionately painful for the installed Kit version, dropping T-4 to a
manual check in §5.3 step 3 is an acceptable amendment — **say so in the PR**
rather than quietly deleting the assertion.

### 6.3 Regression

`npm test` must run the pre-existing privacy tests unmodified. If the layout
change forces an edit to `privacy/page.test.js`, that is a signal the footer
contract was broken (AC-6) — fix the layout, not the test.

---

## 7. Out of scope

Good ideas that do **not** belong in this issue. Recorded here rather than built:

- Any new page or route (dashboard, expenses, budgets, categories, login).
- Auth of any kind: no token storage, no `Authorization` header, no 401
  redirect, no session handling in `apiFetch`.
- Typed API bindings, generated clients, OpenAPI tooling, TanStack Query,
  SWR-style caching, request dedup, retries, interceptors.
- Migrating the project to TypeScript (Q-1).
- A global stylesheet, CSS reset, design tokens, or a component library —
  decision 0001 point 6 defers this until a page needs it.
- Responsive hamburger/drawer navigation, breadcrumbs, dropdowns, active-trail
  logic for nested routes.
- Decimal-aware money formatting helpers (`Intl.NumberFormat`,
  `decimal.js`) — needed once a page renders money, not now.
- Linting/formatting tooling (ESLint, Prettier, `svelte-check`) and CI wiring.
- Changing `ssr = false`, the adapter, or the Dockerfile.
- Error-boundary pages (`+error.svelte`), loading states, toasts.
- Any data-model or backend change (§2, §3).

---

## 8. Risks

| ID | Risk | Mitigation |
|----|------|-----------|
| R-1 | Implementer reads "initialize the project skeleton" literally and re-scaffolds, destroying the #63 privacy page and the existing layout. | §0 states the project exists; AC-6 and §6.3 fail loudly if it is lost. |
| R-2 | The layout change breaks `privacy/page.test.js` T-4 and it gets "fixed" by editing the test. | AC-6 and §6.3 forbid it; reviewers should reject a diff that touches that file. |
| R-3 | Decision 0001 explicitly forbids a nav; a header lands contradicting an accepted ADR with no record. | §4.2.2 requires the amendment in the same PR. |
| R-4 | `api.ts` is created, pulling in TypeScript and a toolchain migration this issue cannot carry. | §0 finding 1, §4.3.1, AC-14, Q-1. |
| R-5 | `apiFetch` is given a trailing-slash "normaliser" and every Django route 404s or 301-redirects. | §4.3.3 rule, pinned by T-7. |
| R-6 | A future contributor adds `Number()` coercion to the response path and floats appear in money fields. | §4.3.6 comment-in-code requirement; project rule restated in §2. |
| R-7 | Compose's `VITE_API_URL` is set to `http://api:8000`, which is unreachable from the browser. | §4.4.1 and §4.4.3 call it out explicitly. |
| R-8 | Two `.env.example` files drift apart. | §4.4.3 cross-reference comments; both READMEs state the split. |
| R-9 | The new tests are written but never run, repeating the #63 situation. | §6.0; AC-13. |
| R-10 | Scope creep: the shell grows a sidebar, theme switcher, auth menu "while we're in there". | §7; decision 0001 point 2's accretion warning. |

---

## 9. Open questions for the team

Flagged rather than guessed. None of these blocks a first read of this spec, but
Q-1 and Q-3 should be answered before implementation.

- **Q-1 — `.js` + JSDoc, or migrate to TypeScript?** The issue text says
  `api.ts`. The repo is checked JS with no `typescript` dependency. This spec
  chooses `frontend/src/lib/api.js` with JSDoc and keeps TS out (AC-14). If the
  team wants TS, it should be its own issue, done before or after but not inside
  this one.
- **Q-2 — Is creating a root `README.md` wanted here?** None exists. This spec
  creates a minimal one (AC-2). The alternative is `frontend/README.md` only.
- **Q-3 — Nav items: brand-only, or brand + explicit "Home"?** This spec
  defaults to brand + `Home` + `Privacy`. Three links for two pages is arguably
  one too many; a reviewer may prefer brand + `Privacy`.
- **Q-4 — Is `@testing-library/jest-dom` worth adding** so tests can use
  `toHaveAttribute`/`toHaveAccessibleName` instead of raw DOM assertions? The
  #63 review deliberately did without. AC-14 says no for now.
- **Q-5 — Amend ADR 0001 in place, or write ADR `0003` superseding its point 2?**
  §4.2.2 defaults to an in-place dated amendment.
- **Q-6 — Should `apiFetch` default to `credentials: "include"`?** This spec says
  no (no auth exists; sending credentials cross-origin by default is a security
  decision). Revisit when auth lands.
- **Q-7 — One root `.env` via Vite `envDir: ".."`, or a separate
  `frontend/.env.example`?** This spec chooses the separate file and explains why
  in §4.4.3.
- **Q-8 — Does the team want a `/api` suffix baked into `VITE_API_URL`?** This
  spec says no: the var is the origin, and `/api/...` belongs to the caller's
  path. Mixing the two conventions is a classic source of `//api/api/` bugs.

---

## 10. Definition of done

1. Every AC in §1.2 passes.
2. `npm install && npm run build && npm test` all succeed, and the PR says so.
3. `frontend/README.md` was followed verbatim by someone other than the author
   on a clean clone, and worked.
4. The ADR 0001 amendment (§4.2.2) is in the same PR as the layout change.
5. No file listed in §4.5 was modified.
6. No application code, migration or test under `backend/` was touched.
7. A human has read this spec and the diff. An agent-produced spec is a
   proposal — nothing here is approved by virtue of having been written.
