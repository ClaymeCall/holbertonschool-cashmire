# 0003 — Session-cookie authentication, not a client-stored token

- **Status:** Proposed
- **Date:** 2026-10-06
- **Context issue:** #25 (document session/token strategy and security trade-offs)
- **Supersedes / superseded by:** —

The user-facing strategy, operational details, security trade-offs, and team
confirmation checklist are maintained in
[auth-strategy.md](./auth-strategy.md). This numbered ADR remains the decision
record and rationale; keep implementation-state claims in that guide accurate
as endpoints and deployment settings evolve.

## Context

Issue #25 asks the team to write up the chosen identity mechanism before the
auth endpoints (#22 register, #23 login, #24 logout, #26 current-user
middleware) get built — so that work has one agreed foundation instead of
each issue re-deciding it.

Two things already point at an answer, even though nobody wrote it down:

1. **The backend is already wired for it.** `backend/cashmire/settings.py`
   has `django.contrib.sessions` installed, `SessionMiddleware` and
   `AuthenticationMiddleware` active, and `CsrfViewMiddleware` active. DRF's
   `REST_FRAMEWORK` setting does not override `DEFAULT_AUTHENTICATION_CLASSES`,
   so it falls back to DRF's own default:
   `SessionAuthentication` + `BasicAuthentication`. No JWT library
   (`djangorestframework-simplejwt` or similar) is installed anywhere.

2. **The frontend is already written against it.** `frontend/src/routes/login/+page.svelte`
   and `register/+page.svelte` call `apiFetch(..., { credentials: "include" })`
   and store nothing from the response — their own comments say *"the API
   establishes a session... there is nothing for this component to store
   itself."* There is no `localStorage`/`sessionStorage` write anywhere in the
   frontend.

So the real decision in front of this issue is narrower than "pick an auth
mechanism" — it is "confirm the session-cookie approach both sides already
assume, write down its trade-offs, and fix the one place the backend doesn't
yet actually support it."

## Decision

1. **Identity is carried by Django's session cookie (`sessionid`), not a
   token the client stores or attaches itself.** `POST /api/auth/login/` and
   `POST /api/auth/register/` call Django's `login(request, user)`, which
   creates a server-side session row and returns a `Set-Cookie: sessionid=...`
   response header. The response body carries no token. The frontend never
   reads, stores or forwards that cookie explicitly — the browser does it,
   because every request already uses `credentials: "include"`.

2. **Transmission:** the `sessionid` cookie is `HttpOnly` (Django's default —
   JavaScript cannot read it) and is sent automatically by the browser on
   every same-site request. `frontend` (`localhost:5173`) and `backend`
   (`localhost:8000`) are different *origins* but the same *site* (same
   registrable domain, `localhost` — the Same-Site cookie algorithm ignores
   port), so the default `SameSite=Lax` cookie already flows on these
   cross-origin `fetch` calls without needing `SameSite=None`. This stops
   being true the moment frontend and backend are deployed on genuinely
   different domains — see Consequences.

3. **`CORS_ALLOW_CREDENTIALS = True` is required and is added in this PR.**
   `credentials: "include"` on the frontend is necessary but not sufficient:
   without this setting, `django-cors-headers` tells the browser the response
   cannot be used for a credentialed request, and the browser discards the
   `Set-Cookie` header entirely. This was the one place code did not yet match
   the strategy both sides assumed; `backend/cashmire/settings.py` is fixed in
   this PR so the statement in this document is true today, not aspirational
   (decision 0002, point 2: security-relevant claims may only be made if
   implemented).

4. **Logout calls Django's `logout(request)`, which flushes the session
   server-side and deletes the session cookie in the response.** A stolen
   pre-logout cookie value no longer resolves to an active session.

5. **Every state-changing request from an authenticated session must carry a
   CSRF token.** DRF's default `SessionAuthentication` enforces Django's CSRF
   check for any request where a session user is already authenticated —
   login/register themselves are unauthenticated-session requests, so they
   are not blocked by this, but logout and every future expense/budget
   mutation (#35-#39, #46-#49) will be. The frontend must read the
   `csrftoken` cookie (it is **not** `HttpOnly`, by design, precisely so JS
   can read it) and send it back as an `X-CSRFToken` header. Django must
   generate and issue a CSRF token before the frontend can read that cookie;
   the current API has no CSRF bootstrap route. This is new work for the
   issues that add login and the first authenticated mutation — flagged here,
   not solved here.

6. **Nothing is stored in `localStorage` or `sessionStorage`.** This is a
   consequence of (1), not a separate choice, and it is the main reason this
   strategy beats a client-stored JWT for this project: there is no token
   sitting in `localStorage` for an XSS payload to read and exfiltrate.

## Security trade-offs (required by #25's acceptance criteria)

- **XSS:** an `HttpOnly` session cookie cannot be read by injected JavaScript,
  so an XSS bug cannot steal the session the way it could steal a
  `localStorage` JWT. It can still *ride* the session (perform actions as the
  logged-in user via the browser's own cookie jar), which CSRF protection
  (point 5) is what limits, not the `HttpOnly` flag.
- **CSRF:** the trade-off this strategy accepts in exchange for XSS
  resistance. Mitigated by Django's `CsrfViewMiddleware` plus DRF's
  per-request CSRF enforcement on authenticated sessions (point 5). This is
  the main thing a reviewer should watch for as the mutation endpoints land —
  a route that skips CSRF "to make the frontend work" reopens exactly what
  this strategy was chosen to close.
- **Expiration:** Django's default `SESSION_COOKIE_AGE` (2 weeks) is left
  unchanged in this PR. For an MVP demo this is acceptable; it is called out
  here as a known, intentional default rather than a considered choice, so a
  future PR can shorten it without re-deriving this context.
- **Storage:** session state lives server-side (in the database, via
  `django.contrib.sessions`'s default `db` backend); the client holds only an
  opaque cookie value. Losing the database's session table invalidates every
  logged-in user at once — an availability trade-off, not a confidentiality
  one.
- **Cross-site deployment:** point 2's "same site, different origin" framing
  only holds because both frontend and backend currently live under
  `localhost`. Deploying them to two different real domains will require
  `SESSION_COOKIE_SAMESITE = "None"` plus `SESSION_COOKIE_SECURE = True` (and
  therefore HTTPS everywhere, including local testing against that
  configuration) — out of scope for this issue, flagged for whoever owns
  deployment.

## Consequences

- #22/#23/#24/#26 have one agreed mechanism to implement against: call
  Django's `login`/`logout`, authenticate via DRF's default
  `SessionAuthentication`, require `request.user.is_authenticated` for
  protected views. None of them need to choose or install a JWT library.
- The first issue that adds an authenticated *mutation* (not just
  login/logout) must add CSRF-token handling on the frontend — this is new
  surface area point 5 names but does not implement.
- `docs/decisions/0002-privacy-claims-must-be-code-verifiable.md` point 5
  applies to the issues that follow this one: #22/#23 ("adds authentication,
  sessions, tokens or cookies") must update `/privacy` in the same PR. This
  PR does not — it changes a CORS setting and documents a strategy, but no
  endpoint in this repository creates a session or sets a cookie yet
  (`/api/health/` is unauthenticated and untouched). The obligation starts
  with whichever PR implements #22 or #23 for real.
- #25's third acceptance criterion — "every team member confirms they
  understand it" — is a human sign-off step. The explicit, named checklist is
  maintained in `docs/decisions/auth-strategy.md`; keep #25 open until all
  confirmations are recorded.
