# Error Response Sanitization (Issue #62)

## Checklist

| Acceptance criterion | Status | Evidence |
|---|---|---|
| Unhandled API exceptions return a generic, user-safe message | ✅ Resolved | `api.exceptions.sanitized_exception_handler` preserves normal DRF validation/API errors and replaces unhandled exceptions with a generic JSON 500 response. |
| Debug mode and verbose tracebacks are disabled outside development | ✅ Resolved | `DJANGO_DEBUG` now defaults to `false`; `.env.example` explicitly enables it for local development and marks that setting as development-only. |
| Trigger a server error and inspect the response body | ✅ Resolved | `SanitizedErrorResponseTests.test_unhandled_api_exception_returns_generic_response` triggers an exception containing a fake database password with `DEBUG=False` and asserts that only the generic message is returned. |

## Verification

- `docker compose run --rm api python manage.py test api.tests.test_errors api.tests.test_login api.tests.test_registration` — 20 tests passed.
- `docker compose run --rm api python manage.py test api` — 198 tests passed.
- With `DJANGO_DEBUG` unset, `docker compose run --rm -e DJANGO_DEBUG= api python manage.py shell -c "from django.conf import settings; print(settings.DEBUG)"` printed `False`.
- `git diff --check` — passed.
- The test checks HTTP 500, the exact generic JSON response, and absence of the exception class and simulated secret from the response body.

## Result

Unhandled exceptions remain available in server-side logs for diagnosis, while the API response does not expose exception details or a traceback. Existing DRF-handled client errors continue to use their existing response format.
