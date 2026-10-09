# 0004 — Minimal per-IP rate limiting for authentication endpoints

- **Status:** Accepted
- **Date:** 2026-10-06
- **Context issue:** #23 (login endpoint), AC-3 ("rate-limiting or basic
  brute-force consideration documented even if minimal for MVP")
- **Supersedes / superseded by:** extended by decision 0006 for registration

## Context

#23's AC-3 asks for brute-force consideration on the login endpoint,
"documented even if minimal for MVP." When this decision was made, no
endpoint in the codebase had rate limiting.

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

3. **`/api/auth/register/` has its own `ScopedRateThrottle` scope,
   `"register"`, also configured at `5/min` per IP** (issue #146, decision
   0006). It has a separate budget from login so registration attempts do
   not consume the login allowance. This is still a coarse MVP control:
   users behind a shared IP share the budget, and distributed attempts can
   evade it. See decision 0006 for the registration-specific rationale.

## Consequences

- A scripted brute-force run against one account is limited to 5
  guesses/minute from a single IP, and account-creation attempts from that
  IP have a separate limit of 5/minute — real improvements over no limit at
  all, not strong protection.
- A legitimate user who mistypes their password 6 times in under a minute
  gets a `429 Too Many Requests` rather than another `401`. Acceptable for
  an MVP demo; worth a friendlier message if this becomes a real support
  complaint.
- Per-account lockout, CAPTCHA, and distributed-attack detection are all
  out of scope here and would need a real decision of their own before a
  production deployment — this document does not claim to have solved
  brute-force protection, only to have done something rather than nothing.
