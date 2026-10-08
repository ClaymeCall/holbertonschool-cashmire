# QA & Security Review — Issue #46 (Create Budget Endpoint)

**Reviewed by:** qa_security agent  
**Date:** 2026-10-07  
**Branch:** feat/46-create-budget-endpoint  
**Spec:** docs/specs/issue-46-create-budget-endpoint.md  

---

## Test Suite Results

**All 28 tests pass.**

- Backend endpoint tests: 28/28 PASS (4.140s)
- Coverage: Authentication, validation (amount, dates, alert_threshold), category ownership, duplicate detection, serialization, error handling

---

## Acceptance Criteria Verification

| AC | Criterion | Result | Evidence |
|----|-----------|--------|----------|
| AC-1 | Route POST /api/budgets/ exists | PASS | `backend/api/urls.py`: `path("budgets/", views.budget_create, name="budget-create")` |
| AC-2 | Authentication required (401/403) | PASS | Test `test_budget_create_requires_session_authentication` returns 403 (DRF IsAuthenticated behavior) |
| AC-3 | Accepts category_id, amount, period_start, period_end, alert_threshold | PASS | BudgetSerializer defines all fields; tests verify parsing |
| AC-4 | amount is DecimalField string, not float | PASS | `DecimalField(max_digits=10, decimal_places=2)` serializes to string; test `test_budget_create_amount_serialized_as_string` confirms `"123.45"` |
| AC-5 | amount > 0, <= 0 returns 400 | PASS | `validate_amount()` raises ValidationError; tests verify rejection of 0, negative values; MinValueValidator(Decimal("0.01")) in model |
| AC-6 | period_start/end dates YYYY-MM-DD, period_end >= period_start | PASS | DateField validation; `validate()` method checks period_end >= period_start; tests `test_budget_create_period_end_before_start_rejected` and `test_budget_create_period_invalid_format` pass |
| AC-7 | category_id must exist and belong to request.user, 404 otherwise | PASS | Line 124: `Category.objects.get(id=category_id, user=request.user)` with DoesNotExist → 404; tests `test_budget_create_nonexistent_category_404` and `test_budget_create_foreign_category_404` confirm 404 |
| AC-8 | alert_threshold optional, 0–100 if provided, 400 otherwise | PASS | `DecimalField(..., allow_null=True, required=False)`; `validate_alert_threshold()` checks range; tests verify 0, 100, null, and out-of-bounds all behave correctly |
| AC-9 | Duplicate check (user, category, period_start, period_end) returns 409 before DB touch | PASS | Lines 132–144: `Budget.objects.filter(...).exists()` check before create; test `test_budget_create_duplicate_409` confirms 409 Conflict with message |
| AC-10 | Owner (user_id) always request.user, never from client | PASS | Line 148: `"user": request.user` in budget_data; serializer marks user_id as read_only; test `test_budget_create_owner_is_request_user` confirms user_id matches authenticated user |
| AC-11 | 201 Created returns full budget: id, user_id, category_id, amount, period_start, period_end, alert_threshold, created_at, updated_at | PASS | BudgetSerializer includes all fields; test `test_budget_create_valid_request` verifies all fields present in response |
| AC-12 | amount, alert_threshold serialized as strings (JSON) | PASS | `DecimalField` serializes to string; test confirms `"500.00"` and `"75.00"` as strings, not numbers |
| AC-13 | Timestamps in ISO 8601 UTC (e.g., `"2026-10-06T14:30:45Z"`) | PASS | Django's DateTimeField with UTC timezone; test `test_budget_create_timestamps_iso8601` confirms "T" and timezone info present |
| AC-14 | Serializer validated, tests cover creation/validation/ownership/uniqueness | PASS | 28 comprehensive tests covering all scenarios |
| AC-15 | DB UNIQUE constraint remains as race-condition safety net | PASS | Migration `api.0003_budget` includes `models.UniqueConstraint(fields=["user", "category", "period_start", "period_end"], name="unique_budget_per_user_category_period")` |

---

## Security & Correctness Findings

### BLOCKING FINDINGS

#### 1. **IntegrityError Not Caught During Race Condition**

**Severity:** BLOCKING  
**Category:** Robustness, error handling  
**Location:** `backend/api/views.py`, line 158

**Issue:**

The `Budget.objects.create()` call is not wrapped in a try/except to handle `IntegrityError`. If two concurrent requests both pass the applicative duplicate check (line 132–137) but arrive at the database simultaneously, the second will violate the UNIQUE constraint and raise an `IntegrityError`. This is unhandled and returns **500 Internal Server Error** instead of **409 Conflict**.

**Reproduction:**

```python
# Concurrent requests with same (user, category, period_start, period_end)
POST /api/budgets/ (Thread 1) - passes duplicate check, acquires lock on DB
POST /api/budgets/ (Thread 2) - passes duplicate check (DB not yet updated), creates
Thread 1 releases lock, attempts create → IntegrityError (unhandled)
Response to Thread 2: 500 Internal Server Error
Expected: 409 Conflict
```

**Why It Matters:**

- Exposes internal database errors (IntegrityError details) to clients instead of a clean API error
- Violates the spec's promise of 409 Conflict for duplicates as a "filet de sécurité"
- Poor user experience (500 suggests server fault, not data conflict)
- May leak database schema information in error traces

**Spec Reference:**

> Contrainte DB (UNIQUE composée) reste en place comme filet de sécurité en cas de race condition ou contournement applicatif.

and

> 409 Conflict — Budget en doublon ... DB constraint UNIQUE reste en filet de sécurité (gère aussi les race conditions).

**Fix Required:**

Wrap the create call in a try/except to catch `IntegrityError` and return a clean 409 response:

```python
try:
    budget = Budget.objects.create(**budget_data)
except IntegrityError:
    return Response(
        {
            "error": "CONFLICT",
            "message": "Budget déjà existant pour cette période et catégorie",
        },
        status=status.HTTP_409_CONFLICT,
    )
```

---

### NON-BLOCKING FINDINGS

#### 1. **HTTP 403 Returned for Missing Authentication (Spec Says 401)**

**Severity:** NON-BLOCKING (spec/convention mismatch, operationally consistent with codebase)  
**Category:** API Design, spec conformance  
**Location:** `backend/api/views.py`, lines 100–101 (decorator `@permission_classes([IsAuthenticated])`)

**Issue:**

The spec states:

> 401 Unauthorized — Authentification absente ou invalide

However, Django REST Framework's `IsAuthenticated` permission class returns **403 Forbidden** when a user is not authenticated, not 401 Unauthorized.

**Test Evidence:**

`test_budget_create_requires_session_authentication` asserts `response.status_code == 403` and passes. The category_list endpoint also returns 403 for unauthenticated requests (test `test_category_list_requires_session_authentication` at line 46 of tests.py).

**Why It Matters (Low):**

- Technically, RFC 7235 treats 401/403 differently:
  - **401 Unauthorized:** Authentication is required; none provided or invalid token.
  - **403 Forbidden:** Authentication is OK; user lacks permission.
  
  DRF interprets "unauthenticated" as "lacks permission," hence 403.

**Not a Bug Because:**

1. The behavior is **consistent across the API** (category_list uses the same pattern).
2. The spec may need clarification on DRF's conventions.
3. Clients can handle 403 as "unauthorized" in most frameworks.

**Recommendation:**

Clarify in `docs/api-design.md` whether the project uses 401 or 403 for unauthenticated requests, or update the spec to reflect DRF's behavior. No code change required.

---

#### 2. **Duplicate Validation Logic in Serializer and Model**

**Severity:** NON-BLOCKING (defense in depth, no harm)  
**Category:** Code efficiency  
**Location:** `backend/api/views.py`, lines 74–91 (serializer validators) and `backend/api/models.py`, lines 96–129 (model validators/constraints)

**Issue:**

Field-level validators are repeated:
- `validate_amount()` replicates the model's `MinValueValidator(Decimal("0.01"))`
- `validate_alert_threshold()` replicates the model's `MaxValueValidator(Decimal("100"))`
- `validate()` (period_end >= period_start) replicates the model's `CheckConstraint`

**Why It Matters (Low):**

- **Defense in depth:** Catching errors before the database is good practice and was explicitly requested in the spec ("défense en profondeur").
- **No correctness issue:** Both layers agree on the rules.
- **Maintenance burden:** Changes to one must be mirrored in the other.

**Not Required to Fix, but:**

For cleaner code, consider extracting validators to a shared module or letting the serializer delegate to the model's validators via `ModelSerializer` introspection (though DRF doesn't do this automatically for custom logic).

---

#### 3. **alert_threshold Serialization When Null**

**Severity:** NON-BLOCKING (spec compliant, works as intended)  
**Category:** Serialization clarity  
**Location:** `backend/api/views.py`, lines 155–156

**Issue:**

When `alert_threshold` is omitted from the request, the serializer does not include it in `validated_data`, so the model's default (80.00) is applied. The response correctly shows the default. However, the response serialization may differ depending on whether the field was explicitly null vs. omitted.

**Test Evidence:**

`test_budget_create_without_optional_alert_threshold` and `test_budget_create_alert_threshold_null` both pass, correctly returning 80.00 (default) and null, respectively.

**Not a Bug Because:**

- The spec allows alert_threshold to be optional with a 80.00 default (AC-8).
- The behavior matches the spec.

---

## Data Integrity Checks

### Decimal Handling (AC-4, AC-12)

✓ `DecimalField(max_digits=10, decimal_places=2)` is used throughout  
✓ Serializer correctly outputs strings (not floats) in JSON  
✓ No float arithmetic observed  

### Ownership Enforcement (AC-10)

✓ `user` field hardcoded to `request.user` (line 148)  
✓ Not read from `request.data`  
✓ Serializer marks `user_id` as read-only  
✓ Test confirms created budget belongs to authenticated user  

### Error Message Leakage

✓ Generic error messages used ("Catégorie non trouvée", "Budget déjà existant")  
✓ No stack traces or database details exposed  
✓ API response format consistent (error, message fields)  

### 404 vs 403 for Forbidden Categories

✓ AC-7 confirms 404 is returned for non-existent or foreign categories  
✓ Spec rationale: Preventing enumeration attacks (docs/api-design.md §1.6)  
✓ Consistent with category_list endpoint  

---

## Vulnerability Analysis (OWASP Top 10)

| Vulnerability | Status | Notes |
|---|---|---|
| **A01: Broken Access Control** | PASS | Ownership enforced at endpoint (request.user), not from client input. Category ownership verified. 404 for foreign categories. |
| **A02: Cryptographic Failures** | N/A | No crypto in scope; relies on SessionAuthentication (HTTPS assumed in production). |
| **A03: Injection** | PASS | No SQL/code injection vectors; ORM parameterization used (Django ORM). |
| **A04: Insecure Design** | PASS | Applicative duplicate check + DB constraint provides defense in depth. |
| **A05: Security Misconfiguration** | N/A | Django defaults are secure for this endpoint. |
| **A06: Vulnerable & Outdated Components** | N/A | Out of scope for this review. |
| **A07: Identification & Authentication** | PASS | SessionAuthentication enforced. Credentials not handled in this endpoint. |
| **A08: Software & Data Integrity Failures** | PASS | Budget model and serializer use DecimalField; no deserialization of untrusted data into dangerous types. |
| **A09: Logging & Monitoring** | N/A | No explicit logging in this endpoint (Django default logging applies). Recommend adding audit logs for budget creation in future. |
| **A10: SSRF** | N/A | No external requests made. |

---

## Summary

| Category | Result |
|----------|--------|
| Test Coverage | 28/28 PASS ✓ |
| Spec Conformance | 14/15 AC PASS; 1 needs fix (IntegrityError) |
| Security (OWASP) | PASS with 1 blocking finding |
| Accessibility (N/A) | Backend API, no frontend |
| Data Integrity | PASS ✓ |
| Error Handling | 1 blocking issue (IntegrityError not caught) |

---

## Blocking Issues Summary

**1 blocking finding must be fixed before merge:**

- **IntegrityError not caught during race condition** (line 158, views.py)  
  Add try/except block to handle IntegrityError and return 409 Conflict instead of 500.

---

## Non-Blocking Issues Summary

**2 non-blocking observations (no action required for merge):**

1. HTTP 403 vs 401 for unauthenticated requests (clarify in API design docs)
2. Duplicate validators in serializer and model (code quality, not a bug)

---

## Recommendations for Future PRs

1. Add test for concurrent budget creation to detect race conditions (threading test).
2. Clarify in `docs/api-design.md` whether to use 401 or 403 for unauthenticated requests (project convention).
3. Add audit logging for budget creation (security & compliance).

---

*Review completed by qa_security agent at 2026-10-07*
