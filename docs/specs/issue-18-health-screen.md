# SPEC — First working Svelte screen: API health check

- **Issue:** #18 "First working Svelte screen"
- **Status:** Proposal. Not approved. A human must read this before the
  Full-Stack Development agent is asked to implement it.
- **Author:** Product & Architecture agent
- **Scope:** SvelteKit frontend only. **No Django code, no model, no migration,
  no new API route.** See §3.
- **Codebase surveyed at:** worktree `cashmire-wt-issue18`, branch
  `agentic/issue-18-health-screen`, commit `cc64e87`

---

## 0. Read this first — the issue text contains one factual error

The issue says the front-end should call `GET /health/`. **There is no
`/health/` route on this project's API.** The actual, existing endpoint is:

```
GET /api/health/
```

Evidence:

- `backend/cashmire/urls.py` mounts the app's URLconf under a prefix:
  `path("api/", include("api.urls"))`
- `backend/api/urls.py` declares `path("health/", views.health, name="health")`

So the resolved path is `/api/` + `health/` = `/api/health/`. The existing home
page already calls it correctly (`frontend/src/routes/+page.svelte` line 9:
`fetch(\`${apiUrl}/api/health/\`)`).

**Resolution for this issue: the new screen calls `/api/health/`. Do not add a
`/health/` route to Django to make the issue text literally true.** Adding a
second alias for the only endpoint in the project, to match a typo in a ticket,
would be worse than fixing the ticket. See Q-1 in §10 — a human should correct
the issue description.

---

## 1. Problem statement and acceptance criteria

### 1.1 User story

> As a developer or reviewer working on Cashmire, I want a page in the
> front-end that calls the backend health endpoint and tells me plainly whether
> the API is reachable — showing me that it is still checking, that it answered,
> or that it failed and why — so that I can confirm the front-end/back-end wiring
> works without opening devtools, curl, or a terminal.

The secondary purpose, and the reason the issue is titled "first working Svelte
screen", is to establish the pattern every later screen copies: how a route is
laid out, how the API base URL is read, and how in-flight / success / failure are
represented in the UI.

### 1.2 Acceptance criteria (testable)

| ID | Criterion | How it is checked |
|----|-----------|-------------------|
| AC-1 | Navigating to `/health` renders a page with exactly one `<h1>` naming it as the API health check. | Manual: open `http://localhost:5173/health`. Automated: T-1. |
| AC-2 | While the request is in flight the page renders a visually distinct **loading** state containing the word "Checking" (see §5.2). | Automated: T-2. |
| AC-3 | On a 2xx response with a parseable JSON body, the page renders a **success** state that displays the `status` value returned by the API (`ok`) and the HTTP status code. | Automated: T-3. Manual: with the API up. |
| AC-4 | On any failure (§6) the page renders a visually distinct **error** state with a human-readable message naming the cause and the URL that was called. | Automated: T-4, T-5, T-6, T-7. Manual: stop the `api` container and reload. |
| AC-5 | Exactly one of the three states is in the DOM at any time. The states are not simultaneously present-but-hidden, and none of them is console-only. | Automated: T-8. |
| AC-6 | The request URL is built from `import.meta.env.VITE_API_URL`, with a documented fallback (§4.4). | Automated: T-9. Manual: set `VITE_API_URL` to a bad host and observe the error state. |
| AC-7 | The error state offers a **Retry** control that re-issues the request and returns the page to the loading state. | Automated: T-10. Manual. |
| AC-8 | A request that never settles does not leave the page stuck on "Checking" forever — it times out into the error state (§6.3). | Automated: T-7. |
| AC-9 | The state region is announced to assistive technology when it changes (§7). | Manual: §7.2 checklist. |
| AC-10 | The shared footer links to `/health` from every page, and the existing `/privacy` link still works. | Automated: T-11. Manual. |
| AC-11 | `frontend/src/routes/+page.svelte` and `frontend/src/routes/privacy/+page.svelte` are unchanged and still work. | Manual regression check. Reviewer diffs the PR. |
| AC-12 | Nothing under `backend/` changes. No migration is added. | Reviewer diffs the PR. |

### 1.3 Out of scope

See §9. In particular: do **not** refactor the duplicate health fetch out of the
home page under this issue.

---

## 2. Data model delta

**None. No table, column, constraint, index or relationship is added, changed or
removed.**

Justification, verifiable in the repo:

- `backend/api/` contains `__init__.py`, `apps.py`, `urls.py`, `views.py`. There
  is no `models.py`; the app defines zero models.
- There is no `backend/api/migrations/` directory.
- This feature reads one hardcoded JSON object from an endpoint and renders it.
  It persists nothing, client-side or server-side: no `localStorage`, no
  cookie, no store that outlives the page.

The project rule that **monetary values are always `Decimal` / `NUMERIC`, never
float** is **not applicable** to this feature: it introduces no field at all, and
no monetary value appears anywhere in the health response. The rule still binds
whenever `Expense` / `Budget` are actually built. This is stated explicitly so a
reviewer can distinguish "the rule was considered and does not apply" from "the
rule was forgotten".

### 2.1 Client-side types

The frontend is **JavaScript, not TypeScript**: there is no `tsconfig.json` and
no `.ts` file anywhere under `frontend/src/`. `frontend/jsconfig.json` sets
`"allowJs": true` and `"checkJs": true`, so type information is expressed as
**JSDoc** and is checked by the editor/`svelte-check` rather than by `tsc` on a
`.ts` file.

So: **do not introduce a `.ts` file or a `src/lib/types.ts` for this issue.**
Declare the types as JSDoc typedefs in the `<script>` block of the new page:

```
/**
 * Body returned by GET /api/health/.
 * The backend returns exactly {"status": "ok"} today
 * (backend/api/views.py). `status` is typed as string, not the literal "ok",
 * because the screen must render whatever value arrives rather than assume it.
 * @typedef {{ status: string }} HealthResponse
 */

/**
 * @typedef {"loading" | "success" | "error"} HealthState
 */
```

Rules for the implementer:

- Treat `status` as an opaque string to display. Do **not** branch on
  `status === "ok"` to decide success/failure — HTTP status decides that (§6.2).
  A future backend that returns `{"status": "degraded"}` with HTTP 200 should
  render the success state showing `degraded`, not an error.
- Do not model fields the endpoint does not return (uptime, version, database
  connectivity). Those would be fabrications. See §9 and R-3.

---

## 3. API contract

**No route is added, changed or removed. No request or response shape changes.
No backend file is touched.** This section documents the *existing* endpoint the
screen consumes, so the implementer does not have to guess its shape.

### 3.1 Consumed route

| Method | Path | Auth | Request body | Success response | Content type |
|--------|------|------|--------------|------------------|--------------|
| `GET` | `/api/health/` | **None.** There is no authentication anywhere in Cashmire — no login route, no token, no session issued by application code. Send no credentials; do not set `credentials: "include"`. | None. No query parameters, no headers required. | `200 OK`, body `{"status": "ok"}` | `application/json` — `REST_FRAMEWORK.DEFAULT_RENDERER_CLASSES` in `backend/cashmire/settings.py` is `JSONRenderer` only, so the browsable HTML API is disabled and the response is always JSON. |

Source of truth: `backend/api/views.py`

```python
@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})
```

### 3.2 Error cases of the consumed route

The project rule is that every new or changed route must list its error cases.
This route is neither new nor changed, but the screen has to handle what it can
actually emit, so the cases are enumerated here rather than omitted. The
"validation failure / not found / unauthorized / forbidden" quartet maps onto
this route as follows:

| Condition | Status | Body | Can it happen? | Screen behaviour |
|-----------|--------|------|----------------|------------------|
| Happy path | `200` | `{"status": "ok"}` | Yes | Success state (§5.3). |
| **Validation failure** | — | — | **No.** The view takes no input: no body, no query params, no path params. There is nothing to validate. | N/A |
| **Unauthorized (401)** | — | — | **No.** No authentication class is configured and the view declares no permission class. | If it ever appears, it falls into the generic non-2xx branch (§6.2) and shows the error state. Do not write an auth-specific message; there is no auth to explain. |
| **Forbidden (403)** | `403` | DRF JSON error | Unlikely, but reachable: Django's CSRF middleware is enabled. A `GET` is a safe method and is not CSRF-checked, so this should not occur for this call. | Generic non-2xx branch (§6.2). |
| **Not found (404)** | `404` | DRF/Django JSON or HTML error page | **Yes, and this is the most likely misconfiguration.** Calling `/health/` instead of `/api/health/` (§0), or pointing `VITE_API_URL` at a server that is not this API. | Error state, with the called URL shown so the mistake is diagnosable. See §6.2 and the special-case message. |
| **Method not allowed (405)** | `405` | `{"detail": "Method \"POST\" not allowed."}` | Only if someone changes the screen to a non-`GET` method. | Generic non-2xx branch. |
| **Not acceptable (406)** | `406` | DRF JSON error | Only if a request sends an `Accept` header that JSONRenderer cannot satisfy. **Therefore: do not set an `Accept` header on this request.** Omitting it is the safest choice. | Generic non-2xx branch. |
| **Server error (500)** | `500` | HTML (debug traceback, since `DJANGO_DEBUG` defaults to `true`) — i.e. **not** JSON | Possible if the Django process is misconfigured. Note the body will not parse as JSON. | Generic non-2xx branch. The screen must not attempt to display a 500 HTML body as JSON. See §6.4. |
| **CORS rejection** | — | — | **Yes, and this is the second most likely misconfiguration.** `CORS_ALLOWED_ORIGINS` defaults to `http://localhost:5173` exactly. A browser on `http://127.0.0.1:5173` is a *different origin* and its request will be blocked by the browser. | The `fetch` promise **rejects** with a `TypeError`; the response is not readable and the status code is not observable from JS. Falls into the network-failure branch (§6.1). The message must therefore mention CORS as a possible cause — see §6.1. |
| **Backend not running** | — | — | Yes. Common in local development. | `fetch` rejects. Network-failure branch (§6.1). |

---

## 4. File layout and route design

### 4.1 Files to create

| Path | Purpose |
|------|---------|
| `frontend/src/routes/health/+page.svelte` | The screen. All of the logic and markup for this issue. |
| `frontend/src/routes/health/page.test.js` | Component tests. Colocated, and named to match the one existing precedent, `frontend/src/routes/privacy/page.test.js`. See §8. |

### 4.2 Files to modify

| Path | Change | Why |
|------|--------|-----|
| `frontend/src/routes/+layout.svelte` | Add one `<a href="/health">API health</a>` to the existing `<footer>`, next to the existing privacy link. Nothing else. | AC-10. A diagnostic page nobody can navigate to is nearly useless. `docs/decisions/0001-shared-app-shell-layout.md` §2 already names the footer as the single home for site-wide links, and adding a link to it is exactly the "small edit to one file" that record anticipates. Keep the footer minimal otherwise: no nav element, no header, no active-link styling beyond §7. |

### 4.3 Files that must NOT be touched

- `frontend/src/routes/+page.svelte` — the home page. It has its own inline
  health fetch; leave it exactly as it is (AC-11). The duplication is known and
  deliberate under this issue; see §9 and R-2.
- `frontend/src/routes/privacy/+page.svelte`, `frontend/src/routes/privacy/page.test.js`
- `frontend/src/routes/+layout.js` — do **not** change `export const ssr = false;`.
  Changing the app-wide rendering mode is not a side effect that belongs in this
  PR (ADR 0001 §3).
- `frontend/src/app.html`, `frontend/svelte.config.js`
- Anything under `backend/`. Any migration. `docker-compose.yml`. `.env`, `.env.example`
  (`VITE_API_URL=http://localhost:8000` is already present in `.env.example` — no
  change needed).
- `frontend/package.json`, `frontend/vite.config.js` — the test stack (`vitest`,
  `@testing-library/svelte`, `jsdom`) and the `"test": "vitest run"` script are
  **already configured**. This issue adds no dependency. If the implementer
  believes one is needed, that is a signal to simplify instead.

### 4.4 Route path decision: `/health`

Chosen: `/health`, file `frontend/src/routes/health/+page.svelte`.

- Matches the existing convention: the one non-root route in the project is a
  directory with a `+page.svelte` inside it (`routes/privacy/+page.svelte`).
- There is no collision with the backend's `/api/health/`: the frontend serves
  port 5173 and the API port 8000; they are separate origins with separate URL
  spaces.
- Preferred over `/status` (ambiguous — could mean a public status page with
  uptime history, which this is not) and over `/api-health` (hyphenated paths
  are not used anywhere in this repo).
- Do **not** put this content on `/` or replace the home page's status line.
  AC-11 guards that.

### 4.5 How `VITE_API_URL` is read

The existing precedent, which this screen follows, is
`frontend/src/routes/+page.svelte` line 4:

```
const apiUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
```

Required behaviour, spelled out:

1. **Read it as `import.meta.env.VITE_API_URL`.** Not `process.env`, not
   `$env/static/public`, not `$env/dynamic/public`. Rationale: `import.meta.env`
   is Vite's own mechanism, it is what the one existing page already uses, and
   the SvelteKit `$env/*` modules expect a `PUBLIC_`-prefixed name — switching to
   them would require renaming the variable in `.env`, `.env.example` and
   `docker-compose.yml`, which is out of scope. Consistency wins here.
2. **Only `VITE_`-prefixed variables are exposed to client code.** This is a Vite
   rule, not a project choice. `VITE_API_URL` already satisfies it.
3. **Fallback.** Use `?? "http://localhost:8000"`, identical to the home page, so
   the screen works in a checkout where the variable is unset.
4. **Also handle the empty string.** `??` does not catch `""`, and an empty
   `VITE_API_URL` in `.env` would produce a request to `/api/health/` on the
   frontend's own origin, which 404s confusingly. Prefer a check that treats a
   missing *or* blank value as absent. Pseudocode, not prescriptive:
   `const raw = import.meta.env.VITE_API_URL; const base = raw && raw.trim() ? raw.trim() : "http://localhost:8000";`
5. **Normalise the trailing slash.** `VITE_API_URL=http://localhost:8000/` must
   not produce `http://localhost:8000//api/health/`. Strip trailing slashes from
   the base before concatenating.
6. **Construct the URL as** `` `${base}/api/health/` ``. Keep the **trailing
   slash** on `/api/health/`: Django's `APPEND_SLASH` would otherwise issue a
   redirect, and a cross-origin redirect is an avoidable complication.
7. **Compute the URL inside the component's `<script>` block**, not at module
   scope of a separate module. This keeps it re-evaluated per component instance,
   which is what lets the tests stub the env var before rendering (§8.3, R-4).
8. **Expose the computed URL in the UI** — the error state must show it (§5.4),
   and showing it in the success state too is allowed and useful. This is the
   single highest-value debugging affordance on the page: a wrong base URL is the
   most likely reason the screen is red.

**Known environment gotcha, worth a line in the PR description.** The repo's
`.env` lives at the *repository root*, but Vite's `envDir` defaults to the Vite
project root, which is `frontend/`. There is no `frontend/.env`. So:

- Under `docker compose up`, the `frontend` service has `env_file: .env`, so
  `VITE_API_URL` is present in the container's `process.env` and Vite picks up
  `VITE_`-prefixed variables from `process.env`. It works.
- Running `npm run dev` directly from `frontend/` on the host, `VITE_API_URL` is
  typically **unset**, and the `http://localhost:8000` fallback is what makes the
  page work. That is the fallback's whole job.

Do not "fix" this by adding `envDir` to `vite.config.js` or creating
`frontend/.env` under this issue — see §9.

### 4.6 Fetch timing: `onMount`, not a `load` function

**Decision: run the fetch from `onMount` in `+page.svelte`. Do not create
`frontend/src/routes/health/+page.js`.**

Reasons, in order of weight:

1. **A `load` function cannot express the three required states inside the
   page.** SvelteKit resolves `load` *before* the page component renders. There
   is no moment at which the page component exists and the request is still in
   flight, so there is no place to render AC-2's loading state from the page
   itself. The navigation-level `navigating` store is a different thing and would
   not satisfy "the screen explicitly handles loading".
2. **A `load` function turns failure into the wrong UI.** A thrown error or a
   rejected promise in `load` renders SvelteKit's error boundary, not the page.
   Satisfying AC-4 would then require a `+error.svelte`, pushing the error state
   into a different component from the success state — directly against AC-5 and
   harder to test.
3. **It matches the existing code.** `frontend/src/routes/+page.svelte` fetches
   in `onMount`. One pattern in the codebase is better than two.
4. **`ssr = false` is set app-wide** (`frontend/src/routes/+layout.js`), so the
   app is client-rendered regardless; a `load` would run in the browser anyway and
   buy nothing in return.
5. **`onMount` is browser-only by definition**, so there is no risk of the fetch
   running during SSR if someone later flips `ssr` back on.

Streaming a promise from `load` and resolving it with `{#await}` in the page is a
third option that *could* satisfy all three states. It is rejected as
unnecessarily indirect for one request to one endpoint, and because it spreads
this screen's logic across two files. Noted so a reviewer knows it was
considered.

### 4.7 Svelte version and reactivity style

`svelte@^5.2.3` is installed. The project is in mixed mode: `+layout.svelte` and
`privacy/+page.svelte` use Svelte 5 (`$props()`, `{@render}`), while
`routes/+page.svelte` is written in legacy style.

**Use Svelte 5 runes for the new page:** `let state = $state("loading")` and
friends. New code should use the current idiom; the two newest components already
do. Do not refactor `routes/+page.svelte` to match (AC-11).

Suggested shape of the component state — the implementer may name things
differently but must keep one single source of truth for which state is active:

| Variable | Type | Notes |
|----------|------|-------|
| `uiState` | `HealthState` | `"loading"` initially. The *only* thing the template branches on. |
| `health` | `HealthResponse \| null` | Set on success. |
| `httpStatus` | `number \| null` | Set whenever a response was received, success or not. |
| `errorMessage` | `string \| null` | Set on error. Human-readable, per §6. |
| `requestUrl` | `string` | Computed per §4.5; displayed per §5.4. |

Do not derive the active state from "is `health` non-null" or from
"`errorMessage` is set" — a single explicit `uiState` discriminant is what makes
AC-5 checkable and prevents the two-states-at-once bug.

---

## 5. UI states

### 5.1 Shared chrome (rendered in all three states)

- `<svelte:head><title>API health · Cashmire</title></svelte:head>`, matching the
  `"<Page> · Cashmire"` pattern established by the privacy page. Add a
  `<meta name="description">`.
- `<main>` wrapping everything. **Pages own their `<main>`; the layout does not
  provide one** (ADR 0001 §4). Exactly one `<main>` on the page.
- Exactly one `<h1>`, text: `API health check` (AC-1).
- One short sentence of context below the `<h1>`, always visible, e.g. "This page
  calls the Cashmire API's health endpoint and reports what came back." It must
  not claim anything the page has not yet determined.
- A single state region (one element) that contains exactly one of §5.2 / §5.3 /
  §5.4. See §7 for its ARIA attributes.
- A link back to `/` at the end.

The footer link to `/privacy` comes from the layout for free.

### 5.2 Loading state

Shown from the first render until the request settles.

Must render:

- A visible status line whose text begins with **`Checking…`** — e.g.
  `Checking the API…`. The literal substring `Checking` is asserted by T-2, so do
  not change the word without updating the test.
- The URL being called may be shown here too (optional).
- A visual indicator that something is in progress. A CSS-animated spinner or a
  pulsing dot is fine; so is plain text. **If any animation is used it must
  respect `@media (prefers-reduced-motion: reduce)`** by stopping or removing the
  animation (§7).

Must NOT render:

- Any success or error affordance. No Retry button (there is nothing to retry
  yet).
- A fake percentage or progress bar. There is no progress to report.

Visual distinctness (AC-5 / the issue's "visibly distinct" requirement): neutral
styling — grey text, grey left border or grey background.

### 5.3 Success state

Shown when a response arrived with an `ok` status and a parseable JSON body.

Must render:

- A clear heading-or-strong line such as **`API is reachable`**.
- **The `status` value from the response body**, labelled, e.g.
  `Reported status: ok`. This is the "show the health check response" requirement
  from the issue. Render the received value, not a hardcoded `ok`.
- **The HTTP status code**, e.g. `HTTP 200`.
- The URL that was called (recommended).

May render:

- The raw JSON body in a `<pre>` for completeness. Allowed, and useful on a
  diagnostic page. If present, render it with `JSON.stringify(body, null, 2)` as
  text content — never with `{@html}`.

Must NOT render:

- Uptime, version, database status, latency SLAs, or any other field the endpoint
  does not return (§2.1, R-3).
- The word "healthy" as a claim about the database or any subsystem. The endpoint
  proves only that Django answered. A sentence like "the API answered; this does
  not check the database" is honest and welcome.

Visual distinctness: a success colour (green family) **plus** a text label and/or
a non-colour glyph. Meaning must not be carried by colour alone (§7).

### 5.4 Error state

Shown for every failure in §6.

Must render:

- A clear line such as **`API check failed`**.
- **A specific, human-readable message** from the mapping in §6. Not "Error", not
  "Something went wrong", not a bare exception string.
- **The URL that was called**, verbatim. Non-negotiable: a wrong `VITE_API_URL`
  is the most likely cause and the user cannot diagnose it otherwise.
- **The HTTP status code, if one was received** (`HTTP 404`). If the request never
  produced a response, say so explicitly rather than printing `HTTP null`.
- **A `<button>` labelled `Retry`** (AC-7). Activating it must: reset `uiState`
  to `"loading"`, clear `errorMessage`/`httpStatus`/`health`, and re-issue the
  request. It must be a real `<button type="button">`, not a styled `<div>` or an
  `<a>`. Guard against double-submits while a request is in flight (disable it,
  or ignore activation when `uiState === "loading"` — but note the button is not
  rendered in the loading state anyway, so this is belt-and-braces).

May render:

- A short hint list for the most likely causes when the request never reached the
  server: the API container is not running; `VITE_API_URL` points somewhere
  wrong; the browser origin is not in `CORS_ALLOWED_ORIGINS` (§6.1).

Must NOT render:

- A raw stack trace, or the full text of a Django debug 500 HTML page. Keep the
  message short; the details belong in devtools.
- Any suggestion that the user's data is at risk. There is no user data (§2).

Visual distinctness: an error colour (red family) **plus** a text label. Contrast
≥ 4.5:1 — do not use pale red on white.

---

## 6. Error handling

A failure is **anything other than "a 2xx response whose body parsed as JSON"**.
There are exactly four branches. All four end in the §5.4 error state.

### 6.1 Branch 1 — the `fetch` promise rejects (no response at all)

Causes: the API is not running; DNS/connection failure; a wrong host or port in
`VITE_API_URL`; **a CORS rejection** (`CORS_ALLOWED_ORIGINS` defaults to
`http://localhost:5173` exactly, so a browser on `127.0.0.1:5173` is blocked);
the request was aborted by the timeout (§6.3 — handle that one separately if the
abort reason is distinguishable, otherwise this branch is a correct home for it).

Important: in this branch the browser gives JavaScript **no status code and no
response body**, by design — a CORS failure is deliberately opaque. So the
message must not guess at a status.

Message to show (wording may vary, substance may not):

> Could not reach the API at `<url>`. The request never completed — the API may
> not be running, the URL may be wrong, or the browser origin may not be allowed
> by the API's CORS configuration.

`httpStatus` stays `null`; render "no response received" rather than `HTTP null`.

### 6.2 Branch 2 — a response arrived but `response.ok` is false

`response.ok` is the check: true for 200–299, false otherwise. Use it; do not
hand-roll `status >= 200 && status < 300`, and do not treat a 3xx as success.

Message:

> The API responded with HTTP `<status>` `<statusText>` at `<url>`.

Plus, for `404` specifically, append a targeted hint — this is the single most
likely wiring mistake on this project (§0):

> The health endpoint is at `/api/health/`. Check that `VITE_API_URL` points at
> the Cashmire API and does not already include the `/api` prefix.

Do **not** try to parse the body of a non-ok response to extract a DRF `detail`
field. A 500 under `DEBUG=true` returns HTML, so the parse would fail and you
would be handling an error inside an error handler. Status code plus URL is
enough for this screen.

### 6.3 Branch 3 — the request never settles (timeout)

Without a timeout, a hung connection leaves the page on "Checking…" forever,
which looks identical to a slow network and violates AC-8.

Required: abort the request after **8 seconds** and show the error state.

- Preferred mechanism: pass `{ signal: AbortSignal.timeout(8000) }` to `fetch`.
  This is supported in all current browsers and in Node 18+ (so it is available
  under jsdom in the test run).
- Equivalent alternative if that proves awkward: an `AbortController` plus
  `setTimeout`, clearing the timer when the request settles. If you take this
  route, **clear the timer in all paths**, including on component destroy, so a
  navigation away does not leave a pending callback writing to a dead component.
- Message:

  > The API at `<url>` did not respond within 8 seconds.

- 8 seconds is a deliberate choice: long enough to survive a cold Django
  autoreload on first request, short enough that a developer does not assume the
  page is broken. If the implementer finds the local cold start genuinely exceeds
  it, raise it and say so in the PR rather than silently removing the timeout.
- **If the timeout cannot be made to work reliably, say so in the PR description
  and leave AC-8 explicitly unmet for the reviewer to decide.** Do not ship a
  timeout that silently does nothing.

### 6.4 Branch 4 — the body is not valid JSON

`await response.json()` throws on a malformed or non-JSON body. This is reachable
even with a 2xx (a proxy or dev-server returning an HTML page with status 200).

Message:

> The API at `<url>` returned HTTP `<status>` but the response body could not be
> read as JSON.

Here `httpStatus` **is** known, so show it.

A related sub-case: the body parses but is not the expected shape (e.g. `null`,
an array, or an object with no `status` key). Treat a missing/non-string `status`
as a malformed response and use this branch's message with an adjusted tail
("…did not contain a `status` field"). Do **not** render `undefined` into the
success state.

### 6.5 Implementation shape

A single `try`/`catch` around the whole sequence, with explicit status and shape
checks inside it, is sufficient and is preferred over four nested handlers:

1. `try` → `fetch(url, { signal: ... })`
2. if `!response.ok` → set the §6.2 message, `uiState = "error"`, return
3. `await response.json()` (inside the same `try`, so §6.4 is caught)
4. validate the shape → §6.4 message if wrong
5. set `health`, `httpStatus`, `uiState = "success"`
6. `catch (err)` → distinguish abort (§6.3) from network failure (§6.1) if the
   error allows it (an aborted fetch rejects with a `DOMException` named
   `"TimeoutError"` or `"AbortError"`); otherwise use §6.1's message.

**Console logging is allowed in addition to the UI, never instead of it.** The
issue is explicit on this point: every state must be visible on screen. If you
log, log once, in the catch, and keep the UI message independent of it.

---

## 7. Accessibility

### 7.1 Requirements

- **Landmarks:** content inside `<main>`; exactly one per page (ADR 0001 §4).
- **Headings:** one `<h1>`; any sub-heading is `<h2>`; no skipped level.
- **Live region:** the state region must carry `role="status"` (which implies
  `aria-live="polite"`) so that the transition from loading to success/error is
  announced without stealing focus. Put the attribute on a **stable wrapper
  element that is always in the DOM**, and swap its *contents* between states — a
  live region that is itself created at the same moment its content appears is
  frequently not announced.
  - For the error state, `role="status"` on the stable wrapper is still the right
    call; do not use `role="alert"` on a newly-inserted node for the same reason,
    and `alert` is assertive, which is heavier than this page needs.
- **Not colour alone:** each state's meaning must be in its text, not only in its
  colour or icon. Any icon must be `aria-hidden="true"` with the meaning carried
  by adjacent text.
- **Reduced motion:** any spinner animation must be disabled under
  `@media (prefers-reduced-motion: reduce)`.
- **Retry button:** a real `<button type="button">` with a visible, descriptive
  label (`Retry`). Keyboard-operable for free; focus must remain visible. After a
  retry that fails again, the button is re-rendered — be aware this loses focus;
  that is acceptable for this issue, but do not remove the default focus outline.
- **Focus:** visible focus on every link and the button. Do not remove outlines
  without a stronger replacement.
- **Contrast:** all text ≥ 4.5:1 against its background, in all three states.
- **Reflow:** readable at 320px width and 200% zoom with no horizontal scroll.
  If a long URL is displayed, allow it to wrap (`overflow-wrap: anywhere`) rather
  than overflowing.
- **Current page:** `aria-current="page"` on the footer link when on `/health`
  is a nice-to-have, not a blocker. If added, apply the same treatment to the
  privacy link for consistency.
- **Language:** `<html lang="en">` is already set in `frontend/src/app.html`.
  Nothing to do; don't break it.

### 7.2 Manual checklist for review

1. Load `/health` with the API up: loading state appears, then success.
2. Stop the `api` container, reload: loading state, then error with a URL and a
   Retry button. Start the API, click Retry: returns to loading, then success.
3. Tab through: both links and the button reachable, focus always visible.
4. Enable OS "reduce motion": no spinning animation.
5. Devtools accessibility tree: one `main`, one `status` region, one `h1`.
6. Zoom to 200% and narrow to 320px: no clipping, no horizontal scrollbar.
7. Confirm the `/privacy` footer link still works from `/health` (AC-10/AC-11).

---

## 8. Test plan

### 8.1 Starting position

Unlike issue #63, the test stack is **already in place**:

- `frontend/package.json` has `"test": "vitest run"` and devDependencies
  `vitest`, `@testing-library/svelte`, `jsdom`.
- `frontend/vite.config.js` has the `test` block (`environment: "jsdom"`,
  `globals: true`) and the `resolve.conditions: ["browser"]` workaround under
  `VITEST` — read the comment there before touching anything; it exists because
  Vite otherwise resolves Svelte's SSR build and `mount()` fails.
- `frontend/src/routes/privacy/page.test.js` is the one existing precedent for
  file naming and style.

**However: `frontend/node_modules` is not installed in this worktree** (there is
no `frontend/node_modules/.package-lock.json`). The implementer must run
`npm install` in `frontend/` first.

`@testing-library/jest-dom` is **not** installed and must not be assumed — a
previous PR shipped tests using `toHaveAttribute`/`toHaveAccessibleName` and they
would have thrown `is not a function` (see `docs/reviews/issue-63-privacy-page.md`).
Use plain DOM assertions: `el.textContent`, `el.getAttribute(...)`,
`expect(...).toBe/toMatch`.

### 8.2 Test file location and tooling

- **One file: `frontend/src/routes/health/page.test.js`.** Colocated with the
  component, matching `privacy/page.test.js`. Do not create a top-level `tests/`
  directory.
- Component tests with `@testing-library/svelte` (`render`, `screen`,
  `findByText`, `getByRole`). No Playwright, no new dependency, no backend test
  harness under this issue.
- Mock the network. `vi.stubGlobal("fetch", vi.fn())` or
  `vi.spyOn(globalThis, "fetch")`. **No test may make a real network request** —
  the suite must pass with the API down and with no network at all.
- Reset between tests: `vi.restoreAllMocks()` / `vi.unstubAllGlobals()` /
  `vi.unstubAllEnvs()` in `beforeEach` or `afterEach`.
- Because the fetch is in `onMount` and resolves asynchronously, assert
  post-settle states with `await screen.findByText(...)` (which retries) rather
  than a synchronous `getByText` immediately after `render`.

### 8.3 Required tests

| ID | Covers | Assertion |
|----|--------|-----------|
| T-1 | AC-1 | Rendering the page exposes exactly one level-1 heading whose text matches `/api health/i`. |
| T-2 | AC-2 | With `fetch` mocked to a promise that never resolves, the rendered text contains `Checking` immediately after `render`, and contains neither the success nor the error marker text. |
| T-3 | AC-3 | With `fetch` resolved to `{ ok: true, status: 200, json: async () => ({ status: "ok" }) }`, the page eventually shows the reachable/success marker, the literal `ok`, and `200`. |
| T-4 | AC-4, §6.2 | With `fetch` resolved to `{ ok: false, status: 404, statusText: "Not Found" }`, the page eventually shows the error marker and `404`, and does **not** show the success marker. |
| T-5 | AC-4, §6.1 | With `fetch` rejecting (`new TypeError("Failed to fetch")`), the page eventually shows the error marker and a message mentioning that the API could not be reached. Assert the called URL appears in the DOM. |
| T-6 | AC-4, §6.4 | With `fetch` resolved to `{ ok: true, status: 200, json: async () => { throw new SyntaxError("Unexpected token"); } }`, the page eventually shows the error state, not a success state with `undefined` in it. Add a second case for a 200 whose body is `{}` (no `status` key). |
| T-7 | AC-8, §6.3 | With `fetch` rejecting with a `DOMException`-like error named `"TimeoutError"`, the page shows the timeout message. (Asserting on the real 8-second timer is not worth it — do not use fake timers to drive `AbortSignal.timeout`; assert the *handling* of the abort rejection instead, and verify the real timeout manually per §7.2.) |
| T-8 | AC-5 | In each of the three scenarios above, assert that the markers for the other two states are absent (`queryByText(...)` returns `null`). This is the test that catches a template rendering two states at once. |
| T-9 | AC-6 | Assert the URL passed to the mocked `fetch`. At minimum: `expect(fetch.mock.calls[0][0]).toContain("/api/health/")` and that it does **not** contain `//api`. Additionally, with `vi.stubEnv("VITE_API_URL", "http://example.test:9999")` set before `render`, assert the called URL starts with `http://example.test:9999`. Also cover the trailing-slash case by stubbing `"http://example.test:9999/"` and asserting the result contains exactly one slash before `api`. |
| T-10 | AC-7 | From the error state, `getByRole("button", { name: /retry/i })`, change the `fetch` mock to succeed, click it, and assert the page ends in the success state. Assert `fetch` was called twice. |
| T-11 | AC-10 | Rendering `+layout.svelte` produces a link with accessible name matching `/health/i` and `href="/health"`, **and** the existing `/privacy` link is still present. Supply the `children` prop with `createRawSnippet` exactly as `privacy/page.test.js` already does — reuse that pattern rather than inventing one. |

Scope cap: one file, roughly the eleven cases above. Do not add coverage
thresholds, CI configuration, or a backend test suite under this issue.

A note on marker strings: T-2/T-3/T-4/T-8 depend on specific words appearing in
the UI (`Checking`, the success marker, the error marker). Define those strings
once at the top of the test file with a comment pointing at §5.2–§5.4 of this
spec, so a wording change is a one-line edit rather than a hunt.

### 8.4 If `npm install` fails

The environment may have no network access, and `frontend/node_modules` is empty.
If dependencies cannot be installed:

1. **Do not report tests as passing, written-and-passing, verified, or green. Do
   not paste invented test output.**
2. State the exact command attempted and the exact failure (e.g.
   `npm install → ENOTFOUND registry.npmjs.org`, or `npm: command not found`).
3. Commit the test file clearly labelled "written but not executed — dependencies
   could not be installed in this environment", following the precedent in
   `frontend/src/routes/privacy/page.test.js`.
4. List what was verified instead, concretely: re-read the component against
   §5 and §6 branch by branch; `grep` the component for `import.meta.env.VITE_API_URL`
   and for `/api/health/`; confirm the heading structure and the single `<main>`
   by reading the markup.
5. Name the acceptance criteria that could not be verified without a browser —
   AC-3, AC-4, AC-8, AC-9 and the whole of §7.2 in particular — and hand them to
   the human reviewer.

A PR that says "could not run tests, here is exactly what I checked instead" is
acceptable. A PR that implies tests ran when they did not is not.

---

## 9. Out of scope

Good ideas that belong to a different issue. Do not implement under #18.

- **Adding a `/health/` route to Django** to match the issue's typo (§0), or any
  other backend change: no new field in the response (version, uptime, database
  connectivity), no DRF schema, no `tests.py`.
- **Refactoring the home page's duplicate health fetch.** `routes/+page.svelte`
  keeps its inline fetch. Extracting a shared `src/lib/api/health.js` client is
  the obvious follow-up, and the right time to do it is when a *third* caller
  appears or when the first real resource (expenses) needs a client. ADR 0001 §2
  deliberately defers `src/lib/`. See R-2.
- **A generic API client / error type / request wrapper / retry-with-backoff.**
  One endpoint does not justify an abstraction layer.
- **Polling, auto-refresh, or a live-updating indicator.** This screen checks once
  per load, plus manual Retry.
- **A public status page** with history, incident log, or uptime percentage.
- **Migrating the frontend to TypeScript**, or adding `svelte-check` to CI. JSDoc
  per §2.1 is the convention until the team decides otherwise.
- **Switching to `$env/static/public`** and renaming `VITE_API_URL` to
  `PUBLIC_API_URL`, or adding `envDir` to `vite.config.js` so the root `.env` is
  read during host-side `npm run dev` (§4.5). Both are reasonable; both touch
  shared config and deserve their own discussion.
- **Changing `ssr = false`**, adding a deploy adapter, prerendering, or SEO work.
- **Expanding the shared layout** beyond the one footer link (§4.2) — no header,
  no nav component, no global stylesheet, no design tokens.
- **Fixing the insecure development defaults** (`DEBUG=true`,
  `ALLOWED_HOSTS=*`, fallback `SECRET_KEY`) or the `/admin/` mount. Already
  flagged as separate work by `docs/specs/issue-63-privacy-page.md` R-2/R-4.
- **Hiding the screen behind auth or a dev-only flag.** There is no auth, and
  the endpoint it calls is already public. See R-5.

---

## 10. Open questions and risks

### 10.1 Open questions — for a human, not for an implementing agent

| ID | Question | Default this spec assumes if nobody answers |
|----|----------|---------------------------------------------|
| Q-1 | Issue #18 says the endpoint is `GET /health/`; the real route is `GET /api/health/` (§0). Should someone correct the issue text? | Implement against `/api/health/`. Do not add a backend alias. |
| Q-2 | Should the health screen be linked from the footer on every page (§4.2), or stay an unlinked URL that only developers know? A diagnostic page in a user-facing footer is slightly odd. | Link it. It is the only other page, discoverability beats tidiness at this size, and removing a link later is trivial. |
| Q-3 | Is `/health` the right path, or does the team want `/status`, `/debug/health`, or something namespaced for developer tools? | `/health` (§4.4). |
| Q-4 | Is an 8-second timeout the right threshold for local development (§6.3)? | 8 seconds. |
| Q-5 | Should the raw JSON body be displayed on screen (§5.3, optional)? Useful for developers, noise for anyone else. | Implementer's choice; either is acceptable. State which was chosen in the PR. |
| Q-6 | There is still no `docs/mvp-scope.md` in this repository, although the agent charters reference one and `docs/specs/issue-63-privacy-page.md` Q-9 already flagged it. Does it exist elsewhere, or is MVP scope undefined? | This spec stays conservative in consequence: §9 is long on purpose. Someone should close this gap — it has now blocked two specs. |
| Q-7 | Should this screen's pattern (a `uiState` discriminant plus the §6 error branches) be written up as a decision record under `docs/decisions/` once it has survived review, so later screens copy it deliberately rather than by imitation? | Recommended, but not required by this issue, and not written here: this spec does not yet know whether the team accepts the pattern. Propose it after implementation. |

### 10.2 Risks

| ID | Risk | Severity | Mitigation / owner |
|----|------|----------|--------------------|
| R-1 | **A green success state proves less than it looks like it proves.** `{"status": "ok"}` is a hardcoded literal in `backend/api/views.py`. It shows that Django is running and routing, and nothing else — not that Postgres is reachable, not that migrations ran (they do not: `backend/Dockerfile`'s `CMD` is plain `runserver` with no `migrate` step). A reader could easily conclude "the system is healthy". | Medium | §5.3 forbids subsystem claims and invites an explicit "this does not check the database" line. Reviewers should insist on it. Deepening the check itself is backend work and out of scope (§9). |
| R-2 | **Two copies of the health fetch** (`routes/+page.svelte` and the new `routes/health/+page.svelte`) can drift — e.g. the URL gets fixed in one place only. | Low | Accepted deliberately for one issue (§9). The follow-up is a shared client in `src/lib/`. Flag it in the PR so it is recorded rather than forgotten. |
| R-3 | **Scope creep toward a status dashboard.** A health screen invites "while we're here, show the version / uptime / DB status", each of which needs backend work and none of which is in this issue. | Medium | §5.3's must-not list and §9. A reviewer seeing a field the endpoint does not return should treat it as a fabricated value, not a nice extra. |
| R-4 | **Stubbing `import.meta.env` in tests may not behave as expected.** Vite statically replaces `import.meta.env.VITE_*` at transform time in some modes; `vi.stubEnv` is documented to work for `import.meta.env` under Vitest, but this has **not been executed** here — `frontend/node_modules` is empty, so nothing could be run while writing this spec. | Medium | §4.5 item 7 keeps the read inside the component's instance scope, which is the arrangement most likely to work. If T-9's env-stub case cannot be made to pass, fall back to asserting the path suffix (`toContain("/api/health/")`) and verify the base URL manually, **and say so in the PR** rather than deleting the assertion silently. |
| R-5 | **The screen exposes the configured API base URL in the page** (§5.4). On a real deployment that is a small information disclosure. | Low | Accepted: it is the single most useful debugging affordance, the value is already shipped to the browser in the client bundle regardless, and there is no deployment today. Revisit if this app is ever hosted publicly. |
| R-6 | **A cross-origin `fetch` failure is opaque to JavaScript.** A CORS rejection and "the server is down" are indistinguishable from the page's point of view, so the error message has to list several possible causes and may send someone down the wrong path. | Low | §6.1 requires the message to name all the likely causes rather than assert one. The real fix is reading the browser console, which the message can hint at. |
| R-7 | **`role="status"` announcements are inconsistent across screen readers**, particularly when the live region is inserted at the same moment as its content. | Low | §7.1 requires a stable always-present wrapper whose contents swap. Verify in §7.2 step 5. |
| R-8 | **This spec is a proposal.** It may be amended or rejected. Several choices here (the footer link, the 8s timeout, the Retry button, runes vs legacy style) are judgement calls, not derivations. | — | The team accepts, amends, or rejects before implementation. Nothing in this document should be implemented merely because an agent wrote it. |

---

## 11. Definition of done

- [ ] `frontend/src/routes/health/+page.svelte` exists and implements §4–§7.
- [ ] All three states render, are mutually exclusive, and are visibly distinct
      (AC-2, AC-3, AC-4, AC-5).
- [ ] All four error branches in §6 are handled, each with its own message.
- [ ] The URL is built from `import.meta.env.VITE_API_URL` with the fallback,
      the blank-value guard, and trailing-slash normalisation (§4.5), and targets
      `/api/health/` (§0).
- [ ] Retry works and returns the page to the loading state (AC-7).
- [ ] The 8-second timeout works, **or** its absence is stated explicitly in the
      PR (§6.3).
- [ ] `frontend/src/routes/+layout.svelte` gains exactly one footer link and
      nothing else; the `/privacy` link still works (AC-10).
- [ ] `routes/+page.svelte`, `routes/privacy/*`, `routes/+layout.js`,
      `package.json`, `vite.config.js` are unchanged (AC-11, §4.3).
- [ ] Nothing under `backend/` changed; no migration added (AC-12).
- [ ] `frontend/src/routes/health/page.test.js` exists with the §8.3 cases and
      `npm test` passes — **or** §8.4's honest-fallback reporting is followed.
- [ ] No test performs a real network request.
- [ ] Accessibility checklist §7.2 completed, or the unverifiable items named.
- [ ] PR description states: which §5.3 optional (raw JSON) choice was made, the
      §4.5 env gotcha, whether the timeout was implemented, and the §0
      `/health/` → `/api/health/` correction so the issue text gets fixed.
- [ ] A human has read this spec. The §10.1 open questions are handed to the
      team, not silently answered.

## 12. Related documents

- `docs/decisions/0001-shared-app-shell-layout.md` — the footer is the home for
  site-wide links; pages own their `<main>`; `+layout.js` stays as it is.
- `docs/decisions/0002-privacy-claims-must-be-code-verifiable.md` — not directly
  engaged (this feature adds no persistence and collects nothing), but worth a
  glance: it requires the privacy page to be revisited by any PR that introduces
  data collection. **This PR introduces none**, so no privacy-page update is owed.
- `docs/specs/issue-63-privacy-page.md` — the precedent for spec structure, and
  the source of claim C-7 ("the home page makes exactly one outbound request").
  Note that adding this screen does **not** falsify C-7, which is scoped to the
  home page; but the privacy page's §5.1 row 5 wording ("The home page makes one
  request…") should be re-read by whoever reviews this PR to confirm it is still
  accurate once a second page also makes that request. Flagged, not changed here.
- `docs/reviews/issue-63-privacy-page.md` — why `@testing-library/jest-dom`
  matchers must not be used.
