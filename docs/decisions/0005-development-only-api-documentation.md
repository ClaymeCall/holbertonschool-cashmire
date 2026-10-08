# 0005 — Expose OpenAPI documentation only in development

- **Status:** Accepted
- **Date:** 2026-10-08
- **Context issue:** #144 (access policy for the OpenAPI schema and Swagger UI)
- **Supersedes / superseded by:** —

## Context

The generated schema at `/api/schema/` and Swagger UI at `/api/docs/` describe
the API's routes, methods, request shapes, and authentication schemes. They
contain no user records, but making the complete interface discoverable to
unauthenticated clients outside development is unnecessary for this MVP.

## Decision

Both endpoints remain public when Django `DEBUG` is enabled and return 404
when it is disabled. The check is performed for every request, so toggling
`DEBUG` in tests or configuration changes their behavior without rebuilding
the URL configuration.

## Consequences

- Developers can continue to inspect the generated schema and Swagger UI in
  local development.
- Production-like deployments do not expose those documentation endpoints.
- This is a reduction in information exposure, not an authorization boundary:
  application API endpoints must continue to enforce authentication,
  authorization, validation, and ownership independently.
- The published API contract remains documented in `docs/api-design.md`.

## Verification

`api.tests.test_api_docs_access` verifies that both endpoints are available
in development, return 404 when debug mode is disabled, and do not affect an
authenticated application API route.
