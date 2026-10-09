# 0006 — Registration abuse controls and email-enumeration resistance

- **Status:** Accepted
- **Issue:** #146
- **Date:** 2026-10-08
- **Related decisions:** 0003 (session-cookie authentication), 0004 (login rate limiting)

## Context

`POST /api/auth/register/` is public and creates accounts. Before this
change, it had no rate limit and returned a field-specific uniqueness error
for an email already in use. Those behaviors let a caller automate account
creation and directly test whether an email belongs to an existing account.

The registration flow also immediately logged a newly created user in and
returned the user resource. Returning that response only for new accounts,
while suppressing it for duplicate emails, would still reveal account
existence through the status, body, or `sessionid` cookie. This project has
no email-delivery or address-verification service, so adding verification
would require a separate product and infrastructure change.

## Decision

1. **Throttle registration separately at 5 requests per minute per IP.**
   `RegisterView` uses DRF's `ScopedRateThrottle` with the `"register"`
   scope; `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]` configures it at
   `5/min`. This reuses the existing dependency and policy scale from login
   without letting registration traffic consume the login scope.

2. **After validating the submitted fields, return HTTP `202 Accepted` and
   the exact same neutral JSON body for a valid new registration and a
   duplicate email or username:**

   ```json
   {"detail": "If registration can be completed, sign in to continue."}
   ```

   The endpoint does not return a user object, conflict detail, or other
   account-specific information. A uniqueness race discovered during the
   database write is mapped to the same response; unrelated database
   integrity failures still surface as errors rather than being hidden.

3. **Do not establish a session on registration.** Creating an account
   still happens synchronously for a new valid email, but the client must
   not be able to tell that from the response. The user must submit the
   login form separately. The frontend presents the same next step and
   offers a link to sign in for either outcome.

4. **Keep field validation independent of account existence.** Invalid
   email syntax, missing fields, or password-policy failures continue to
   receive `400` field errors. The serializer does not run uniqueness
   validators that would reveal which submitted email or username is
   already taken; after other validation succeeds, collisions receive the
   neutral response above.

## Rationale and trade-offs

- A generic `400` only for duplicate email would still be distinguishable
  from a successful registration (`201`), and returning the created
  `UserSerializer` only for a new address would expose existence directly.
- Keeping automatic login would create another response-side channel: a
  new account would receive an authenticated session cookie while a
  duplicate request would not. Removing that convenience is necessary for
  the chosen response policy; email verification was rejected as out of
  scope because no delivery mechanism exists.
- The `202` response is intentionally generic even though creation is
  synchronous. It communicates that the request was accepted without
  describing whether a new resource was created.
- Validation errors still teach a caller whether a *submitted password or
  field format* is invalid, but those errors do not vary based on whether
  the email or username exists.
- Equal status/body and the absence of a session remove the direct response
  signal, not every conceivable side channel. This is not a guarantee
  against timing analysis, resource-exhaustion attempts, or distributed
  attackers.
- The rate limit is per IP, not per account or device. People sharing a
  NAT, school, or corporate network share five registration attempts per
  minute, while a distributed attacker can spread attempts across IPs.
  This is an MVP abuse-control baseline, not production-grade bot
  prevention. A production deployment may need edge-level limits, CAPTCHA,
  email verification, and monitoring.

## Consequences

- Clients must treat `202` as a neutral acknowledgement, not as proof that
  an account was created or that the user is authenticated. They must not
  expect an account representation or session cookie.
- Duplicate email/username attempts no longer have a field-level uniqueness
  error. The UI directs the user to sign in, which is useful for an existing
  account and remains safe for a new one.
- `429 Too Many Requests` is returned after the per-IP budget is exhausted;
  the frontend tells the user to wait before retrying.
