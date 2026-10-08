# 0004 — Minimal per-IP rate limiting on login

- **Status:** Proposed
- **Date:** 2026-10-06
- **Context issue:** #23 (login endpoint), AC-3 ("rate-limiting or basic
  brute-force consideration documented even if minimal for MVP")
- **Supersedes / superseded by:** —
- **Note for whoever merges #107:** that PR adds
  `docs/decisions/0003-session-cookie-auth-strategy.md`, proposed in
  parallel with this one and not yet present on this branch. This document
  is written as a standalone decision so it doesn't block on merge order,
  but it is really an extension of 0003's security-trade-offs section and
  should be folded in there (as an amendment) once both have landed, rather
  than living on indefinitely as a separate file.

## Context

#23's AC-3 asks for brute-force consideration on the login endpoint,
"documented even if minimal for MVP." Nothing rate-limits any endpoint in
this codebase today.

## Decision

1. **`LoginView` carries DRF's `ScopedRateThrottle`, scoped `"login"`,
   configured at `5/min` in `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`**
   (`backend/cashmire/settings.py`). No new dependency — `ScopedRateThrottle`
   ships with `djangorestframework`, already installed.

2. **The throttle key is the caller's IP address, not the account being
   targeted.** `ScopedRateThrottle` (via DRF's `SimpleRateThrottle`) keys
   anonymous requests by IP. This is deliberate for MVP scope — it needs no
   extra state beyond Django's cache — but it is coarse:
   - A shared IP (NAT, campus network, corporate proxy) shares one budget
     across every user behind it. Five people trying to log in from the
     same office in the same minute can lock each other out.
   - It does **not** protect a single targeted account from an attacker
     spreading attempts across many IPs.

3. **Only `/api/auth/login/` is throttled this way. `/api/auth/register/`
   is not**, even though it is also unauthenticated and could be spammed.
   Registration abuse is a real but different problem (fake-account
   creation, not credential-guessing against an existing account) and is
   left for whoever picks that up — flagged here so it isn't assumed
   solved.

## Consequences

- A scripted brute-force run against one account is limited to 5
  guesses/minute from a single IP — a real improvement over no limit at
  all, not a strong one.
- A legitimate user who mistypes their password 6 times in under a minute
  gets a `429 Too Many Requests` rather than another `401`. Acceptable for
  an MVP demo; worth a friendlier message if this becomes a real support
  complaint.
- Per-account lockout, CAPTCHA, and distributed-attack detection are all
  out of scope here and would need a real decision of their own before a
  production deployment — this document does not claim to have solved
  brute-force protection, only to have done something rather than nothing.
