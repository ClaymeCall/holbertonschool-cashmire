# SPEC — Privacy and legal information page

- **Issue:** #63 "Build privacy and legal information page"
- **Status:** Proposal. Not approved. A human must read this before implementation,
  and the content itself requires legal sign-off (see §10).
- **Author:** Product & Architecture agent
- **Scope:** SvelteKit frontend only. No backend change, no model, no migration.
- **Codebase surveyed at:** branch `demo/privacy-page`, commit `86fbf6a`

---

## 0. Why this spec is unusually strict about wording

This is a legal-ish public statement about data handling. The normal failure mode
for a privacy page is to describe the product the team *intends* to build rather
than the software that actually exists. Cashmire today stores **no personal data
from users at all** — there are no models, no migrations, no accounts, no expenses.
A page that says "we encrypt your financial data" would be a false statement
shipped to users.

So this spec does two things a normal feature spec does not:

- It fixes a **claims table** (§5.2) where every sentence the page may assert is
  tied to a file in this repo that proves it.
- It fixes a **forbidden-claims list** (§5.3) of things the page must not say,
  enforced by a test (§8.3).

The qa_security agent will check the rendered page against the implementation.
Implementers should treat §5.2 and §5.3 as the acceptance surface.

---

## 1. Problem statement and acceptance criteria

### 1.1 User story

> As someone evaluating Cashmire, I want a plainly-written page that tells me what
> personal data the app holds about me, why, where it lives, and what is done to
> protect it, so that I can decide whether to trust it — without having to create
> an account or read the source code.

### 1.2 Acceptance criteria (testable)

Each criterion is written so it can be checked as pass/fail.

| ID | Criterion | How it is checked |
|----|-----------|-------------------|
| AC-1 | Navigating to `/privacy` renders a page with a single `<h1>` naming it as the privacy and legal information page. | Manual: `npm run dev`, open `http://localhost:5173/privacy`. Automated: §8.3 T-1. |
| AC-2 | The page contains every section heading listed in §5.1, in that order, as `<h2>` elements. | Automated: §8.3 T-2. |
| AC-3 | Every factual claim rendered on the page maps to a row in the claims table §5.2, and that row's evidence is still true in the repo at merge time. | Human/qa_security review, diffing §5.2 against the named files. |
| AC-4 | The page contains none of the forbidden strings/claims in §5.3. | Automated: §8.3 T-3. |
| AC-5 | A link to `/privacy` is present on **every** page of the app, via a shared layout footer. | Automated: §8.3 T-4. Manual: link is visible on `/` and on `/privacy`. |
| AC-6 | `/privacy` is reachable with no authentication, no session, and no prior navigation — a cold direct load of the URL renders the full content. | Manual: open the URL in a private window. See §4.5. |
| AC-7 | Rendering `/privacy` issues **zero** network requests (no API call, no font CDN, no analytics, no third-party asset). | Automated: §8.3 T-5. Manual: browser devtools Network tab shows only the app's own JS/CSS. |
| AC-8 | Every human-dependent fact (entity name, contact, jurisdiction, controller, effective date) appears as a literal placeholder token, not an invented value. | Automated: §8.3 T-6. Manual: grep for `TODO(#63-legal)`. |
| AC-9 | The page carries a visible notice that it is a draft pending legal review, for as long as the placeholders in AC-8 remain unfilled. | Manual review. |
| AC-10 | The page meets the accessibility requirements in §7. | Manual checklist §7.2. |
| AC-11 | The existing home page `/` still loads and still shows its API status line. | Manual. Regression check on the layout change. |

### 1.3 Explicit non-goals for this issue

Listed fully in §9.

---

## 2. Data model delta

**None. No table, column, constraint, index or relationship is added, changed or
removed.**

Justification, verifiable in the repo:

- `backend/api/` contains `__init__.py`, `apps.py`, `urls.py`, `views.py` and no
  `models.py`. The app defines zero models.
- There is no `backend/api/migrations/` directory. Zero migrations exist.
- The page is static content rendered by the client. It reads nothing and writes
  nothing.

The charter rule that monetary values must be `Decimal` / `NUMERIC` and never
float is **not applicable** here: this feature introduces no monetary field, and
indeed no field at all. The rule still binds whenever `Expense` / `Budget` are
actually built.

---

## 3. API contract

**No route is added, changed or removed. No request or response shape changes.**

Justification:

- The entire API surface is `GET /api/health/` → `{"status": "ok"}`
  (`backend/api/urls.py`, `backend/api/views.py`), plus Django's bundled
  `/admin/` mount in `backend/cashmire/urls.py`.
- The privacy page's content is fixed text authored at build time. Serving it
  from the backend would add a deployment coupling and a route to secure for no
  benefit at this size. If the policy later needs versioning or an audit trail,
  revisit — that is listed as out of scope in §9.

### 3.1 Error cases — N/A

The charter requires every new or changed route to enumerate its error cases
(validation failure, not found, unauthorized, forbidden). **This section is N/A
because this feature introduces no route**, and therefore introduces no new
error cases on the API. This is stated explicitly rather than omitted so that a
reviewer can tell the difference between "no errors documented" and "no errors
possible".

One client-side error case does exist and is in scope:

| Situation | Expected behaviour |
|-----------|--------------------|
| User requests a path that does not exist, e.g. `/privacy/gdpr` | SvelteKit's default 404 page. No custom `+error.svelte` is required by this issue; do not add one. |

---

## 4. File layout

### 4.1 Files to create

| Path | Purpose |
|------|---------|
| `frontend/src/routes/privacy/+page.svelte` | The page content. The bulk of the work. |
| `frontend/src/routes/+layout.svelte` | Shared app shell: renders page content plus a `<footer>` containing the privacy link. Does not exist today. |
| `frontend/src/routes/privacy/+page.js` | **Conditional** — only if the SSR override in §4.4 is verified to work. Contains `export const ssr = true;` and nothing else. |
| `frontend/src/routes/privacy/page.test.js` | **Conditional** — only if test tooling can be installed. See §8. |

### 4.2 Files to modify

| Path | Change |
|------|--------|
| `frontend/package.json` | Add a `test` script and the test devDependencies — only per §8. No other change. |
| `frontend/vite.config.js` | Add the vitest `test` block — only per §8. |

### 4.3 Files that must NOT be touched

`frontend/src/routes/+layout.js`, `frontend/src/routes/+page.svelte` (beyond
nothing — it should need no edit at all), `frontend/src/app.html`,
`frontend/svelte.config.js`, anything under `backend/`, `docker-compose.yml`,
`.env*`.

Note on `+page.svelte`: moving the existing page's markup into the layout is
**not** wanted. The layout wraps; the page stays as it is. AC-11 guards this.

### 4.4 Route path decision: `/privacy`

Chosen: `/privacy`, file `frontend/src/routes/privacy/+page.svelte`.

- Short, guessable, and the near-universal convention, which matters for a page
  people go looking for.
- Preferred over `/privacy-policy` because this page is broader than a privacy
  policy — it also carries operator/legal-status information (§6).
- Preferred over splitting into `/privacy` + `/legal` because at this size two
  near-empty pages are worse than one honest one. If the legal section grows
  past roughly a screen, split then.

### 4.5 "Reachable without authentication"

There is **no authentication anywhere in Cashmire** — no login route, no session
issued by application code, no guarded frontend route. So there is no auth gate
to bypass. The criterion is satisfied negatively, and the implementer must keep
it that way:

- `privacy/+page.svelte` must not import any store, guard, or helper that could
  later gain an auth check.
- `privacy/+page.js`, if created, must contain only the `ssr` export — **no
  `load` function**, so there is nothing that can fail, redirect, or require a
  token.
- The page must not call `fetch` (AC-7), so it cannot be broken by an API that
  is down, unreachable, or requiring credentials. This is deliberate: a privacy
  page that 500s because the backend is off is a bad privacy page.

The spec should also be read as a standing constraint: **if auth is added later,
`/privacy` stays public.** Recorded in `docs/decisions/0002-...`.

### 4.6 The shared layout and its interaction with `ssr = false`

`frontend/src/routes/+layout.js` currently contains exactly:

```js
export const ssr = false;
```

It has no `+layout.svelte` sibling. SvelteKit is perfectly happy with a
`+layout.js` that has no component — it just applies the page options. Adding
`+layout.svelte` alongside it does **not** conflict with or override
`+layout.js`; the two files serve different jobs (component vs. page options)
and both apply to the whole route tree. **Do not merge, move, or delete
`+layout.js`.**

Consequences of `ssr = false` that the implementer must understand:

1. The app is client-rendered. The server sends an empty shell and the browser
   builds the DOM. The privacy text is therefore **not in the initial HTML**.
2. That means: invisible to a user with JavaScript disabled, and invisible to
   crawlers that do not execute JS. For an ordinary feature page, fine. For a
   legal notice, mildly unfortunate — people do look for these with scripts off.

**Decision — attempt a per-route SSR override, with a documented fallback.**

SvelteKit page options cascade, and a more specific route may override a parent's
value. So `frontend/src/routes/privacy/+page.js` containing `export const ssr = true;`
should re-enable server rendering for `/privacy` only, leaving the rest of the
app CSR-only as today.

This has **not been verified in this environment** (`frontend/node_modules` is
empty, so nothing can be run). Therefore:

- **Required:** the page works correctly with the repo exactly as-is, CSR-only.
  This is the baseline and AC-1..AC-11 are all satisfiable without the override.
- **Attempt:** add `privacy/+page.js` with the `ssr = true` export and verify via
  `npm run dev` + "View Source" that the policy text appears in the served HTML.
- **Fallback:** if it errors, or if the text does not appear, **delete the file**
  and say so plainly in the PR description. Do not leave a file that doesn't do
  what it claims. Shipping CSR-only is an accepted outcome, recorded as a known
  limitation in §10.
- **If the override is kept**, `+layout.svelte` must be SSR-safe: no `window`,
  `document`, `localStorage` or other browser-only API at module or component
  init scope.

Do **not** set `export const prerender = true;`. The project uses
`@sveltejs/adapter-auto` (`frontend/svelte.config.js`), which resolves an adapter
from the detected deployment platform; with no platform configured, `npm run build`
is unverified in this repo. Prerendering is a build-time concern and would couple
this issue to fixing the adapter. Out of scope (§9).

### 4.7 Shared layout content

`frontend/src/routes/+layout.svelte` is a **minimal** shell. It must contain:

- A `<footer>` element (implicit `contentinfo` landmark) rendered after the page
  content, containing at minimum a link `<a href="/privacy">Privacy &amp; legal</a>`.
- The page content slot.
- Nothing else that is not needed: no header bar, no logo, no nav menu with one
  item, no theme switcher, no global reset beyond what the footer needs. There is
  one other page in this app; a nav component would be ceremony.

Svelte version note: `svelte@^5.2.3` is installed. Use the Svelte 5 form:

```
let { children } = $props();
...
{@render children()}
```

`<slot />` also still works in Svelte 5 compatibility mode and is an acceptable
fallback if the runes form errors — the existing `+page.svelte` is written in
legacy style, so the project is in mixed mode. Either is fine; do not refactor
`+page.svelte` to match.

Styling: scoped `<style>` in the layout component. Do not introduce a global
stylesheet, a CSS framework, or `src/lib/` for this issue. The contrast
requirement in §7 applies to whatever colours are chosen.

---

## 5. Content outline

This is the substance. Headings are prescriptive; wording is the implementer's,
subject to §5.2 and §5.3.

### 5.1 Required sections, in order

| # | Heading (`<h2>`) | Substance it must convey |
|---|------------------|--------------------------|
| — | *(h1)* "Privacy and legal information" | Page title. Exactly one `<h1>`. |
| — | *(draft notice, not a heading)* | Visible banner: this page is a draft pending review; placeholders are unfilled. Required while AC-8 placeholders remain. |
| — | *(last updated, not a heading)* | "Last updated: `[[EFFECTIVE_DATE]]`" using `<time>`. See §6.2. |
| 1 | "The short version" | Two or three sentences. Cashmire does not currently ask you for any personal information and stores none. It is an early-stage project; the features that would handle financial data are not built yet. Everything below explains that in detail. |
| 2 | "What personal data we store" | **Today: none.** No account, no name, no email, no password, no expense, no budget, no bank connection. There is no form on the site to enter anything. The one page that exists shows whether the API is responding. |
| 3 | "Why we store it" | Follows from §2: there is nothing to justify, because nothing is collected. State the principle that applies going forward — data will be collected only where a named feature needs it, and this page will be updated before such a feature ships. Do not dress this up as a formal lawful-basis analysis; there is no processing to have a basis for. |
| 4 | "Where data would live" | A PostgreSQL database is configured for the project (`docker-compose.yml`). The application defines no tables in it. The backend container starts the server without running database migrations, so as shipped, not even the framework's own tables are created. The database today holds nothing about you. Be precise: *configured* ≠ *populated*. |
| 5 | "What happens when you visit this site" | The home page makes one request to the project's own `/api/health/` endpoint, which returns `{"status": "ok"}` and nothing about you. **This privacy page makes no requests at all.** Like any web server, the server sees the usual connection metadata (IP address, user agent) and the development server prints request lines to its console; no logging configuration, log storage, or log retention policy is defined in the project. Say that honestly rather than claiming either "we log nothing" or "we retain logs for N days". |
| 6 | "Cookies and tracking" | The application code sets no cookies and includes no analytics, no tag manager, no tracking pixel, no third-party script, and no third-party font or asset. Caveat to state, because it is true: the project includes Django's standard admin and session machinery, and Django's built-in admin at `/admin/` would set a session cookie for anyone who logged into it — but there are no user accounts, that interface is not part of the product, and it is unrelated to using the site. See §10 risk R-4. |
| 7 | "Third parties we share data with" | None. There is no analytics provider, no email provider, no payment processor, no bank aggregator, no error-reporting service, no CDN. Nothing is shared because nothing is collected. Name the hosting arrangement as `[[HOSTING_ARRANGEMENT]]` rather than guessing. |
| 8 | "How long we keep data" | Nothing is kept, so there is nothing to retain or expire. There is no account to delete because there are no accounts. When features that store data ship, this section gets real retention periods — and those periods are a decision for a human, not a default. |
| 9 | "Your rights" | State the standard rights (access, rectification, erasure, restriction, portability, objection, complaint to a supervisory authority) and then state plainly that in practice there is currently no data of yours to access, correct, export or erase. Give `[[CONTACT_EMAIL]]` as the route to exercise them. Do **not** assert which legal regime applies — that is `[[JURISDICTION]]` / §6 / open question Q-3. |
| 10 | "How we protect data" | The hard one. See §5.4. Only claim what the code does. |
| 11 | "What is planned, and not yet built" | Explicitly labelled as future. User accounts, expense tracking, budgets and categories are planned and **do not exist in the software today**. When they ship they will involve storing personal and financial data, and this page must be updated at that time. Use unambiguous future/negative framing throughout ("is not built", "would", "will"), never present tense. |
| 12 | "Who operates Cashmire" | See §6. All placeholders. |
| 13 | "Changes to this page" | Changes are tracked in the project's git history. The last-updated date at the top reflects the most recent change. No email notification mechanism exists or is promised. |
| — | *(closing link)* | Link back to the home page. |

### 5.2 Claims table — every claim must be evidence-backed

A reviewer should be able to take each row, open the named file, and confirm.
If a claim the implementer wants to make is not in this table, either find the
evidence and add a row in the PR, or do not make the claim.

| ID | Claim the page may make | Evidence in repo | How to verify |
|----|-------------------------|------------------|---------------|
| C-1 | The app defines no database tables. | `backend/api/` | No `models.py` exists in the app. |
| C-2 | No migrations exist. | `backend/api/` | No `migrations/` directory. |
| C-3 | As shipped, the backend does not create database tables on startup. | `backend/Dockerfile` | `CMD` is `python manage.py runserver 0.0.0.0:8000`; there is no `migrate` step in the Dockerfile or in `docker-compose.yml`. |
| C-4 | A PostgreSQL database is configured but unused by application data. | `docker-compose.yml` (`db` service, `postgres:16-alpine`), `backend/cashmire/settings.py` `DATABASES` | Config present; combined with C-1 nothing writes to it. |
| C-5 | The entire API is one health endpoint. | `backend/api/urls.py`, `backend/api/views.py` | One `path("health/", ...)`; one view returning `{"status": "ok"}`. |
| C-6 | There is no registration, login, or authenticated route. | `backend/api/urls.py`, `backend/api/views.py`, `frontend/src/routes/` | No auth view, no auth route, no login UI. |
| C-7 | The home page makes exactly one outbound request, to the project's own health endpoint. | `frontend/src/routes/+page.svelte` | Single `fetch(\`${apiUrl}/api/health/\`)` inside `onMount`. |
| C-8 | The health response contains no personal data. | `backend/api/views.py` | Response body is `{"status": "ok"}`. |
| C-9 | The application sets no cookies. | `backend/api/views.py`, `frontend/src/routes/+page.svelte` | No `set_cookie`, no `document.cookie`; the health view is a plain GET and the frontend fetch sends no credentials. |
| C-10 | There are no analytics or third-party scripts. | `frontend/src/app.html`, `frontend/package.json` | `app.html` contains only the SvelteKit placeholders; dependencies are SvelteKit, Vite and Svelte only. |
| C-11 | There is no email, payment, or bank integration. | `backend/requirements.txt` | Django, DRF, psycopg2-binary, django-cors-headers. Nothing else. |
| C-12 | Browser-to-API requests are restricted by CORS to a configured origin, defaulting to the local dev frontend. | `backend/cashmire/settings.py` | `CORS_ALLOWED_ORIGINS` defaults to `http://localhost:5173`. State this carefully — see §5.4. |
| C-13 | The project currently runs with insecure development defaults. | `backend/cashmire/settings.py`, `.env.example` | `DEBUG` defaults true; `ALLOWED_HOSTS` defaults `*`; `SECRET_KEY` falls back to `"dev-insecure-secret-key"`. |
| C-14 | Django's admin interface is mounted. | `backend/cashmire/urls.py` | `path("admin/", admin.site.urls)`. |
| C-15 | This privacy page itself makes no network requests. | `frontend/src/routes/privacy/+page.svelte` | No `fetch`, no `onMount` doing I/O, no remote asset URL. Enforced by test T-5. |

### 5.3 Forbidden claims

The page must not state or imply any of the following. Test T-3 greps for the
bracketed tokens; the rest is review.

| ID | Must not say | Why |
|----|--------------|-----|
| F-1 | That data is encrypted at rest. [`encrypt`] | No encryption is configured anywhere. |
| F-2 | That traffic is served over HTTPS/TLS. [`TLS`, `HTTPS`] | Nothing in the repo terminates TLS; dev runs plain HTTP on `localhost`. A *future* hosting setup may, but the page may not promise it. |
| F-3 | That passwords are hashed/salted. [`hash`, `password`] | There are no passwords. Django's password validators are configured but no account can be created through the product. |
| F-4 | That access to data is role-restricted / least-privilege / audited. | No access control exists; the one endpoint is unauthenticated. |
| F-5 | That the app stores, processes, or protects "your expenses", "your budgets", "your transactions", or "your bank data". [`bank`, `transaction`] | None of these features exist. This is the single most important prohibition in this spec. |
| F-6 | That the app is GDPR-compliant / certified / audited / ISO-anything. | No assessment has been done; compliance is a human's call, not an agent's. |
| F-7 | That backups exist or are tested. | No backup mechanism is configured. |
| F-8 | That data is stored in a named country or region. | Hosting is undetermined — `[[HOSTING_ARRANGEMENT]]`. |
| F-9 | An invented company name, address, email, DPO, or effective date. | §6. |
| F-10 | "We take your privacy seriously" and similar unfalsifiable filler. | The whole point of this page is that every sentence is checkable. |

Note for the implementer on the grep-based test: the forbidden *tokens* will
legitimately appear in the "what is planned" and "how we protect data" sections
in negated form ("we do not claim encryption at rest"). Test T-3 is therefore
specified in §8.3 as a *review aid with an allowlist*, not an absolute bar —
read T-3's definition before fighting it.

### 5.4 "How we protect data" — what may actually be claimed

May be said:

- The strongest protection currently in place is that there is nothing to
  protect: no personal data is collected, so none can be lost, leaked or
  misused. State it that way — it is true and it is the honest headline.
- The project is open source; the code behind every statement on this page can
  be read. (Only if the repo is in fact public — see open question Q-6.)
- Browser access to the API is limited by a CORS allowlist which by default
  permits only the local development frontend (C-12). Frame this as a
  development-time configuration, not a security guarantee; CORS is a browser
  policy and not a server-side access control.

Must be said (this is the part that makes the page credible):

- A short, direct paragraph stating that Cashmire currently runs with
  **development defaults that are not safe for production**: debug mode on by
  default, a wildcard allowed-hosts setting, and a hardcoded fallback secret key
  (C-13). Therefore the page makes no claim to a hardened production security
  posture, and the project should not be treated as production-ready. Hardening
  must happen before any real user data is accepted.

Must not be said: anything in §5.3.

This section will read as unusually self-critical for a privacy policy. That is
intended and should not be softened in review without a corresponding change to
the code.

---

## 6. Legal information

### 6.1 What the page must address

- Who operates Cashmire (natural person, company, student project, ...).
- Its status: is this a product, a prototype, a coursework project? This matters
  because it sets a reader's expectations and is probably the single most
  clarifying sentence on the page.
- Who, if anyone, is the data controller.
- Which jurisdiction's law applies and which supervisory authority a complaint
  would go to.
- How to contact a human.
- An effective / last-updated date.

**None of these can be determined from the code.** The implementer must not
invent any of them. All six are open questions (§10).

### 6.2 Placeholder convention — mandatory

Define the placeholders once, at the top of
`frontend/src/routes/privacy/+page.svelte`, and reference them in the markup:

```
// TODO(#63-legal): these values require a human decision - see SPEC.md section 10.
// Do not invent values. Do not remove this comment while any value is unresolved.
const LEGAL = {
  entity:   "[[LEGAL_ENTITY]]",
  status:   "[[PROJECT_STATUS]]",
  contact:  "[[CONTACT_EMAIL]]",
  jurisdiction: "[[JURISDICTION]]",
  controller:   "[[DATA_CONTROLLER]]",
  hosting:  "[[HOSTING_ARRANGEMENT]]",
  updated:  "[[EFFECTIVE_DATE]]"
};
```

Rules:

1. Placeholders render **literally and visibly** as `[[LEGAL_ENTITY]]` etc. in
   the page. Do not substitute "TBD", "Acme Ltd", "Example Company", "N/A", or a
   blank. A visible `[[...]]` token is a defect a reviewer cannot miss; "TBD"
   reads like finished copy.
2. The double-bracket form is chosen so a single `grep -rn '\[\[' frontend/src/`
   finds every unresolved item, and so it can never be mistaken for prose.
3. `[[EFFECTIVE_DATE]]` goes inside a `<time>` element; leave `datetime` off or
   set it only when a real date is supplied. Do not emit an invalid `datetime`
   attribute.
4. `[[CONTACT_EMAIL]]` must **not** be wrapped in a `mailto:` link while it is a
   placeholder — a `mailto:[[CONTACT_EMAIL]]` link is a broken link. Render it
   as plain text until a real address exists.
5. The draft banner (AC-9) must be present while any placeholder remains, and
   should be removed in the same commit that fills the last one.

---

## 7. Accessibility requirements

This is a plain-content page with no interactivity. There is no excuse for it to
be anything other than exemplary, and it sets the pattern for pages that follow.

### 7.1 Requirements

- **Landmarks:** content inside `<main>`; footer inside `<footer>`. Exactly one
  `<main>` on the page — confirm the layout does not nest a second one around
  the existing home page's `<main>` (`frontend/src/routes/+page.svelte` already
  has one). Decide this deliberately: either the layout provides `<main>` and
  pages do not, or pages provide it and the layout does not. **Chosen: pages
  own `<main>`**, because `+page.svelte` already does and AC-11 says don't touch it.
- **Headings:** exactly one `<h1>`; sections use `<h2>`; no level is skipped;
  headings are real heading elements, not styled `<div>`s or `<p>`s.
- **Document title:** set via `<svelte:head><title>…</title></svelte:head>` —
  distinct from the home page's title, e.g. "Privacy and legal information ·
  Cashmire". Also add a `<meta name="description">`.
- **Link text:** self-describing out of context. "Privacy & legal", not "click
  here" / "more" / "read this". The footer link is the one users will scan for.
- **Current page:** the footer link gets `aria-current="page"` when the user is
  on `/privacy`. Use `$page.url.pathname` from `$app/stores` (or `$app/state` if
  that is what the installed SvelteKit version exposes); if this proves awkward,
  it is a nice-to-have, not a blocker.
- **Contrast:** body text and link text at ≥ 4.5:1 against their background;
  the draft banner must also pass — do not use pale amber-on-white.
- **Not colour alone:** the draft banner must carry its meaning in text, not only
  in a background colour.
- **Text structure:** real `<ul>`/`<li>` for lists; real `<p>` for paragraphs; no
  `<br>`-separated pseudo-paragraphs. Long sections benefit from lists — screen
  reader users get item counts.
- **Reflow and zoom:** readable at 320px width and at 200% zoom without
  horizontal scrolling. Use relative units; set a max line length (~70ch) for
  readability.
- **Focus:** keyboard focus visible on every link; do not remove default outlines
  without providing a stronger replacement.
- **Language:** `<html lang="en">` is already set in `frontend/src/app.html`;
  nothing to do, but don't break it.

### 7.2 Manual checklist for review

1. Tab through the page: every link reachable, focus always visible.
2. Disable CSS: content order still makes sense.
3. Browser devtools accessibility tree: one `main`, one `contentinfo`, heading
   outline h1 → h2 × 13 with no gaps.
4. Zoom to 200%: no horizontal scrollbar, no clipped text.
5. Devtools Network tab on a hard reload of `/privacy`: only first-party app
   assets (AC-7).

---

## 8. Testing strategy

### 8.1 Starting position — read this before planning

- `frontend/node_modules` is empty; dependencies are **not installed**.
- `frontend/package.json` has `dev`, `build`, `preview` scripts and **no `test`
  script**, no vitest, no testing-library, no jsdom.
- The backend has no `tests.py`, no pytest, no test configuration.
- There is therefore **no test runner anywhere in this repository today.**

So the implementer is not "adding a test", they are standing up test
infrastructure. For a static content page that must be kept proportionate.

### 8.2 Tooling decision

**Add vitest + @testing-library/svelte + jsdom to the frontend. Nothing else.**

- Vitest reuses the existing `frontend/vite.config.js` and the SvelteKit plugin,
  so configuration is a few lines rather than a parallel build setup.
- `@testing-library/svelte` renders a component and queries it by role and
  accessible name — which is exactly the shape of the assertions this page needs
  (headings exist, link is reachable, text is present), and it nudges future
  tests toward accessibility-flavoured queries.
- This is the conventional SvelteKit testing stack, so it is reusable rather
  than throwaway when accounts/expenses arrive.

Rejected alternatives: Playwright (a browser download and a dev-server lifecycle
is disproportionate for asserting that text is on a page; revisit when there are
real user flows); a bespoke grep script over source files (asserts on source
text, not on rendered output, so it cannot catch a page that fails to render at
all); no tests (AC-4 and AC-8 are exactly the kind of thing a human reviewer
stops checking by the third revision).

Scope cap: **one test file, roughly six assertions.** Do not build a test
pyramid for a text page. Do not add coverage thresholds, CI config, or a backend
test harness under this issue.

Expected changes:

- `frontend/package.json`: `"test": "vitest run"` in scripts; the three
  devDependencies above (plus `@testing-library/jest-dom` only if genuinely
  needed for a matcher — prefer doing without).
- `frontend/vite.config.js`: a `test` block with `environment: "jsdom"` and
  `globals: true`.

### 8.3 What the tests must assert

| ID | Covers | Assertion |
|----|--------|-----------|
| T-1 | AC-1 | Rendering the privacy page component exposes exactly one `heading` at level 1, whose accessible name matches `/privacy/i`. |
| T-2 | AC-2 | Every required `<h2>` from §5.1 is present. Assert on a list of substrings derived from the headings actually implemented; the test's job is to fail if someone deletes a section. |
| T-3 | AC-4 | Content-honesty guard. Take the page's rendered `textContent`, lowercase it, and assert that each forbidden token from §5.3 either does not appear, **or** appears only within one of an explicit, short allowlist of sentences (the negated/forward-looking uses). Keep the allowlist in the test file with a comment pointing at §5.3 and at this spec. The value of this test is that changing a claim forces someone to consciously edit the allowlist. |
| T-4 | AC-5 | Rendering the layout component produces a `link` with accessible name matching `/privacy/i` and `href="/privacy"`. |
| T-5 | AC-7 | Stub `globalThis.fetch` with a spy before rendering the privacy page; assert it was never called. |
| T-6 | AC-8 | While placeholders remain: assert the rendered text contains `[[CONTACT_EMAIL]]` (and the other tokens). This test is *expected to be updated* when real values land — add a comment saying so, so its later modification is not mistaken for someone defeating a test. |

### 8.4 Fallback if dependencies cannot be installed

`npm install` may fail — the environment may have no network access, and
`node_modules` is currently empty.

**If that happens, the required behaviour is to say so, explicitly and
prominently, in the PR description.** Specifically:

1. Do **not** report tests as passing, written-and-passing, or verified. Do not
   paste invented test output. Do not write a test file and imply it was run.
2. State the exact command attempted and the exact failure (e.g.
   `npm install → ENOTFOUND registry.npmjs.org`).
3. Choose one and state which:
   - (a) commit the test file and the `package.json` / `vite.config.js` changes
     **unrun**, clearly labelled "written but not executed — tooling could not be
     installed in this environment"; or
   - (b) omit the test tooling entirely and note that AC-1..AC-8 were verified
     manually only.
   Option (a) is preferred if the implementer is reasonably confident the test
   file is syntactically valid; option (b) is preferable to committing something
   broken.
4. Verify by other means instead, and list what was actually done:
   - Read the rendered component source against the §5.2 claims table and the
     §5.3 forbidden list, row by row, and report the result as a checklist.
   - `grep -rn '\[\[' frontend/src/routes/privacy/` to show placeholders present.
   - `grep -rn 'fetch\|http://\|https://' frontend/src/routes/privacy/` to show
     no network calls and no remote assets.
   - Confirm the heading structure by reading the markup.
   - Say clearly which acceptance criteria could **not** be verified without a
     running browser (AC-6, AC-10, AC-11 in particular) and hand them to the
     human reviewer.

A PR that says "could not run tests, here is exactly what I checked instead" is
acceptable. A PR that implies tests ran when they did not is not, and is a worse
failure than having no tests — on a page whose entire purpose is truthfulness,
especially so.

---

## 9. Out of scope

Good ideas that belong to a different issue. Do not implement under #63.

- **Cookie consent banner.** No cookies are set by application code (C-9), so a
  banner would be theatre. Required when/if analytics or sessions arrive.
- **Per-feature privacy notices** for accounts, expenses, budgets, categories.
  These features do not exist; writing their privacy notices now would produce
  exactly the false-claim problem this spec exists to prevent.
- **Terms of service / imprint / cookie policy as separate pages.** One page now.
- **Internationalisation.** English only. No i18n framework, no `USE_I18N` work.
  Note `LANGUAGE_CODE = "en-us"` is already set in Django; irrelevant here.
- **Backend-served or versioned policy** (a `PolicyVersion` model, an acceptance
  audit trail, a "you must re-accept" flow). Revisit if a real legal obligation
  appears. Git history is the version history for now.
- **A general design system / nav component / global stylesheet / `src/lib/`.**
  §4.7 deliberately keeps the layout minimal.
- **Fixing the insecure dev defaults** (`DEBUG`, `ALLOWED_HOSTS`, `SECRET_KEY`).
  This spec requires the page to *disclose* them (§5.4); fixing them is separate
  work and must not be bundled into a content PR. It should be filed as its own
  issue — see risk R-2.
- **Configuring a real deploy adapter / prerendering / SEO** (sitemap,
  robots.txt, canonical URLs). See §4.6.
- **Backend test harness.** §8 adds frontend tooling only.
- **Taking `/admin/` off the public URL conf.** Disclosed (C-14), not changed
  here. See R-4.

---

## 10. Open questions and risks

### 10.1 Open questions — require a human answer before the page can ship un-draft

These block removing the draft banner (AC-9), not the implementation. The
implementer should build the page with placeholders and leave these for the team.

| ID | Question | Why an agent must not answer it |
|----|----------|------------------------------|
| Q-1 | What is the legal entity or person operating Cashmire? (`[[LEGAL_ENTITY]]`) | Inventing a legal entity on a published legal page is a fabrication with real-world consequences. |
| Q-2 | What contact address should readers use? (`[[CONTACT_EMAIL]]`) | An invented address is a dead letterbox; a guessed real one may belong to someone else. |
| Q-3 | Which jurisdiction governs, and which supervisory authority? (`[[JURISDICTION]]`) | Determines whether GDPR, UK GDPR, CCPA or nothing applies, and what the page is obliged to say. Not inferable from code. |
| Q-4 | Who is the data controller for GDPR purposes, if GDPR applies? (`[[DATA_CONTROLLER]]`) | A named role with legal duties. Note the oddity worth raising with the team: with zero personal data processed there is arguably nothing to control *today* — but the identity must be settled before any data collection ships. |
| Q-5 | How should the project describe its own status — product, prototype, coursework, demo? (`[[PROJECT_STATUS]]`) | Shapes reader expectations and possibly whether a privacy policy is legally required at all. |
| Q-6 | Is the repository public, and may the page invite readers to verify claims in the source? | §5.4 permits this claim only if true. |
| Q-7 | Where is / will the app be hosted, and in what region? (`[[HOSTING_ARRANGEMENT]]`) | Needed for the "where does data live" and international-transfer questions. Currently local Docker only. |
| Q-8 | What is the effective date? (`[[EFFECTIVE_DATE]]`) | Should be the date of human approval, not the date an agent wrote the file. |
| Q-9 | There is no `docs/mvp-scope.md` in this repository, although the agent charters reference one. Does it exist elsewhere, or is MVP scope undefined? | The charter forbids expanding MVP scope; it cannot be checked against a missing document. This spec stays conservative in consequence. Flagging so the gap is closed. |

### 10.2 Risks

| ID | Risk | Severity | Mitigation / owner |
|----|------|----------|--------------------|
| R-1 | **A privacy policy is a legal document.** Nothing in this spec, and nothing the implementing agent writes, constitutes legal advice or legal review. The page may be inaccurate, insufficient, or inapplicable for the project's actual jurisdiction. | High | Ship with the draft banner. A human — ideally with legal input — must read and approve the final wording before it is presented as the operative policy. This spec is a proposal, not an authority. |
| R-2 | **The page discloses insecure defaults** (`DEBUG=true`, `ALLOWED_HOSTS=*`, fallback `SECRET_KEY`) per §5.4. Publishing that is honest, and also tells an attacker where to start if a real deployment ever goes live with those defaults. | Medium | The right fix is to change the defaults, not to hide them. File a separate hardening issue; it is out of scope here (§9). Until then, honesty wins — the page also says the project is not production-ready. |
| R-3 | **The page goes stale the instant real data collection ships.** A privacy page that says "we store nothing" while a `User` model exists is worse than no page: it becomes an affirmatively false statement to users. | High | `docs/decisions/0002-privacy-claims-must-be-code-verifiable.md` makes updating this page part of the definition of done for any PR introducing persistence or data collection. Enforced by human review, not tooling. |
| R-4 | **Django's `/admin/` is mounted** (C-14) with `DEBUG=true` and wildcard `ALLOWED_HOSTS`. It is disclosed on the page but not addressed. | Medium | Out of scope here. Should be part of the hardening issue in R-2: restrict or remove the admin mount before any deployment. |
| R-5 | **The per-route SSR override (§4.6) is unverified** — `node_modules` is empty so nothing could be run while writing this. It may not behave as described under a parent layout that disables SSR. | Low | §4.6 specifies a fallback and requires the implementer to report which path they took. CSR-only is an acceptable outcome. |
| R-6 | **Test tooling may be uninstallable** (no network). | Low | §8.4 specifies the required honest reporting and manual alternatives. The failure mode to guard against is a claim that tests passed. |
| R-7 | **The forbidden-token test (T-3) may produce false positives** as wording evolves, tempting someone to delete it. | Low | T-3 is specified with an explicit allowlist so that loosening it is a visible, deliberate edit rather than a silent deletion. Reviewers should treat a shrinking T-3 as a signal. |
| R-8 | **Over-disclosure.** This page is more candid about weaknesses than a typical privacy policy, which may read as alarming to a casual visitor. | Low | Accepted deliberately. The `[[PROJECT_STATUS]]` framing (Q-5) sets context. Softening the §5.4 disclosures requires a corresponding code change, not a copy edit. |

---

## 11. Definition of done

- [ ] `frontend/src/routes/privacy/+page.svelte` exists and implements §5.
- [ ] `frontend/src/routes/+layout.svelte` exists, is minimal (§4.7), and its
      footer links to `/privacy` on every page.
- [ ] `frontend/src/routes/+layout.js` is unchanged. `frontend/src/routes/+page.svelte`
      is unchanged and still works (AC-11).
- [ ] Every claim on the page traces to a row in §5.2.
- [ ] No claim in §5.3 appears, except in the allowlisted negated forms.
- [ ] All human-dependent values are `[[PLACEHOLDER]]` tokens with the
      `TODO(#63-legal)` comment; the draft banner is visible.
- [ ] Accessibility checklist §7.2 completed, or the items that could not be
      checked are named.
- [ ] Tests per §8.3 added and run — **or** §8.4's honest-fallback reporting
      followed, with the actual verification performed listed in the PR.
- [ ] Nothing under `backend/`, no migration, no `docker-compose.yml` change.
- [ ] PR description states which §4.6 path was taken (SSR override kept or
      dropped) and why.
- [ ] A human has read this spec and the resulting page. Open questions §10.1
      are handed to the team, not silently answered.

## 12. Related decision records

- `docs/decisions/0001-shared-app-shell-layout.md`
- `docs/decisions/0002-privacy-claims-must-be-code-verifiable.md`
