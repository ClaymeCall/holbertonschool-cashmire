# Authentication strategy: Django session cookies

**Context issue:** #25  
**Decision record:** [ADR 0003 — Session-cookie authentication](./0003-session-cookie-auth-strategy.md)  
**Status:** Proposed; team confirmation is still required

## Decision

Cashmire will authenticate browser clients with Django's server-side session
framework. The browser receives an opaque `sessionid` cookie after a successful
login and sends it automatically on later API requests. The frontend must not
copy the session identifier into JavaScript storage or add it to requests
manually. This decision does not introduce JWT or another client-managed token.

This document describes the chosen strategy and its security trade-offs; it
does not mean that the authentication endpoints are already implemented. On
`main` when this document was prepared, the API exposes health and schema
routes, but no register, login, logout, or current-user endpoint.

## Where authentication data lives

| Data | Location | Security implications |
|---|---|---|
| User credentials | The user record in PostgreSQL; passwords must be stored as Django password hashes, never as plaintext or reversible encryption. | A database disclosure should not expose usable plaintext passwords. Registration and password changes must use Django's password-hashing APIs. |
| Authenticated session | Server-side Django session store. With Django's default session backend, session data is stored in the database. | The browser holds only an opaque identifier; clearing or invalidating server-side sessions revokes them. |
| Session identifier | Browser cookie named `sessionid` by default. | It is a bearer credential, so it must be protected in transit and not exposed to JavaScript. |
| CSRF token | Browser cookie named `csrftoken` by default; the backend must generate and issue a token before the frontend can read it, and the frontend returns it in the `X-CSRFToken` header for unsafe requests. | It is intentionally readable by JavaScript. It is not an authentication token and must not replace session validation. |

The exact cookie and session settings must be rechecked when deployment
configuration changes. Django's defaults relevant to the current development
setup are `HttpOnly` for the session cookie, `SameSite=Lax`, and a
`SESSION_COOKIE_AGE` of 1,209,600 seconds (two weeks). `SESSION_COOKIE_SECURE`
defaults to `False`, which is suitable only for the current local HTTP
development setup; production must use HTTPS and secure cookies.

## How credentials travel

1. The user submits credentials to the API over HTTPS in production.
2. After successful authentication, Django creates or rotates the server-side
   session and responds with `Set-Cookie: sessionid=...`. The response body
   must not return the session identifier.
3. The browser stores the cookie and includes it automatically on subsequent
   requests made with `credentials: "include"`.
4. The backend resolves the cookie to a session and sets `request.user`.
   Protected endpoints must authorize using the authenticated user and must
   scope user-owned data to that user.

For local development, the frontend at `localhost:5173` and the API at
`localhost:8000` are different origins but the same site. Credentialed
cross-origin requests therefore require the exact frontend origin in
`CORS_ALLOWED_ORIGINS` and `CORS_ALLOW_CREDENTIALS = True`; the frontend must
also use `credentials: "include"`. The backend currently enables credentialed
CORS for the configured frontend origin.

If production puts the frontend and API on different sites, deployment must
explicitly review cookie `SameSite` and `Secure` settings, HTTPS, CORS, and
CSRF trusted origins. Do not broaden allowed origins to `*` for credentialed
requests.

## Logout and expiration

- Logout must call Django's `logout(request)`, which flushes the current
  server-side session and clears the browser's session cookie. A previously
  copied session identifier must no longer authenticate after logout.
- A session expires according to the configured Django session age. The
  current default is two weeks; this is a framework default, not a promise
  that the application will retain sessions for exactly that duration in all
  deployments.
- Session state can also be invalidated server-side, for example when
  credentials are changed or an administrator revokes sessions.
- The login endpoint should use Django's authentication and login APIs so
  session rotation and password verification are handled by the framework.

## Security trade-offs and required protections

### XSS and client storage

An `HttpOnly` session cookie cannot be read directly by injected JavaScript,
unlike a token stored in `localStorage`. This reduces credential theft by XSS;
it does not make XSS harmless. Malicious script running in the application can
still issue authenticated requests through the victim's browser. Continue to
prevent XSS through safe rendering, input handling, and a restrictive content
security policy where appropriate. Never place the session identifier in
`localStorage`, `sessionStorage`, application state, or logs.

### CSRF

Browsers attach cookies automatically, which creates CSRF risk. Django's CSRF
middleware and DRF's `SessionAuthentication` checks must remain enabled for
unsafe authenticated requests. The frontend must obtain the `csrftoken` cookie
and send its value in `X-CSRFToken` for state-changing requests, including
logout and future expense, budget, and category mutations. Do not disable CSRF
checks to make a request succeed.

Login and registration also need deliberate CSRF treatment: they can change
the browser's authenticated state even when the requester is not yet logged
in. Their endpoint implementation must follow the API contract and framework
protections rather than relying on the fact that `SessionAuthentication`
doesn't require a token for an anonymous session.

The current API does not expose a CSRF bootstrap route. Before the frontend
can send `X-CSRFToken`, an endpoint or response flow must cause Django to
generate a CSRF token and issue the `csrftoken` cookie (for example, by using
Django's CSRF token helpers). Do not assume that enabling CSRF middleware
alone guarantees the frontend already has the cookie.

### Session theft and transport

Anyone who obtains a valid session identifier may act as that user until the
session is invalidated or expires. Production must use HTTPS and secure
cookies; application code must not disclose session identifiers in response
bodies, URLs, logs, analytics, or error messages. `HttpOnly` limits script
access to the cookie but does not protect against malware, browser compromise,
or an attacker who already has the identifier.

### DRF authentication defaults

The project's DRF settings do not currently override
`DEFAULT_AUTHENTICATION_CLASSES`. DRF therefore supplies its own defaults,
which include `SessionAuthentication` and `BasicAuthentication`. The product
decision is session-cookie authentication for the browser; it is not an
endorsement of HTTP Basic credentials as a frontend storage or transport
strategy. Before exposing protected endpoints, the implementing issue must
explicitly verify which authentication classes those views accept and ensure
that the actual behavior matches the API contract and deployment requirements.

## Implementation checklist for follow-up issues

- Use Django's password hashing, `authenticate`, `login`, and `logout` APIs;
  never compare or store plaintext passwords.
- Keep the session identifier in the browser-managed `HttpOnly` cookie only.
- Keep credentialed CORS restricted to explicitly configured frontend origins.
- Preserve CSRF validation on unsafe requests and send `X-CSRFToken` from the
  frontend; ensure the backend has issued the `csrftoken` cookie first.
- Require authentication for protected endpoints and scope every query over
  user-owned data to `request.user`.
- Review cookie security, expiration, authentication classes, and CSRF trusted
  origins for production settings.
- Update the privacy page in the same change that actually adds authentication,
  sessions, tokens, or cookies, as required by ADR 0002.

## Team confirmation

Issue #25 asks every team member to confirm that they understand this strategy.
The checklist records evidence, not an assumption that someone has read this
document. A PR approval is recorded only for the member who approved PR #107;
the remaining confirmations must be made explicitly by the team.

- [x] Tom (`tomvieilledent`) — approved PR #107, which introduced the session-cookie decision.
- [ ] Jason (`ToujoursPareil8`) — explicit confirmation pending.
- [ ] Clément (`ClaymeCall`) — explicit confirmation pending.

Keep issue #25 open until each member has explicitly confirmed understanding.
