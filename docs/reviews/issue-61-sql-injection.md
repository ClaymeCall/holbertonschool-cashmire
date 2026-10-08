# SQL Injection / Unsafe Query Audit (Issue #61)

## Checklist

| Acceptance criterion | Status | Evidence |
|---|---|---|
| Database access uses the Django ORM or parameterized queries; no SQL is built from input | ✅ Resolved | Audited Python application code under `backend/`; no raw SQL execution (`cursor.execute`, `.raw()`, `RawSQL`, or `.extra()`) is used. Reads, writes, and filters use Django ORM QuerySets. |
| A regression test safely handles an injection payload | ✅ Resolved | `ExpenseListTests.test_category_filter_rejects_sql_injection_payload` sends `1 OR 1=1 --` as `category_id`; the API returns 400 with a field-level validation error and no expense data. |
| Audit checklist item marked resolved | ✅ Resolved | This issue-specific audit checklist records the review and regression-test evidence. |

## Verification

- Query inputs are validated before they reach ORM filters. Expense-list category and date filters use `ExpenseListQuerySerializer`; budget-list integer filters are parsed and rejected on invalid input.
- The persistence code reviewed is `backend/api/`, including views, serializers, models, and services.
- `docker compose run --rm api python manage.py test api.tests.test_expenses` — 33 tests passed.
- `git diff --check` — passed.

## Result

No application SQL string-concatenation vulnerability was found in the audited code. The regression test documents safe rejection of a conventional SQL injection payload at the expense-list query boundary.
