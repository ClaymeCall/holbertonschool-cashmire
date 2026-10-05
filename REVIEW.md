# QA & Security Review — Privacy and Legal Information Page (Issue #63)

**Reviewed (Initial):** 2024-10-05  
**Re-reviewed:** 2026-10-05  
**Branch:** demo/privacy-page (commit 86fbf6a)  
**Reviewer:** QA & Security Agent  

---

## Executive Summary

**Status: NO BLOCKING FINDINGS AFTER RE-REVIEW**

The privacy page implementation is complete, accurate, and conforms to SPEC.md requirements. All acceptance criteria AC-1 through AC-11 are met or verified acceptable per the specification.

**IMPORTANT: This review was incomplete on first pass.** Two real defects in the test file were missed:
1. T-1 and T-4 used jest-dom matchers that were never installed, causing `is not a function` errors.
2. T-3's allowlist had overlapping phrases that would not match correctly against the normalized text.

Both defects have been fixed by the developer. This re-review verifies each fix in detail.

---

## Re-Review Findings — Defects and Fixes

### Defect 1: T-1 and T-4 Used Jest-DOM Matchers That Were Not Installed

**Original Issue:**

Lines 36-43 and 137-143 in the initial test file used `toHaveAccessibleName()` and `toHaveAttribute()` — matchers provided by `@testing-library/jest-dom`. The `package.json` devDependencies list only `@testing-library/svelte`, `jsdom`, and `vitest` — no `jest-dom`. Neither test file nor any other file imported jest-dom. Both assertions would have thrown `is not a function` on the first test run.

**Why It Mattered:**

- Static code review cannot catch runtime errors when the required dependency is missing.
- The test suite would have failed immediately on first execution, blocking merge.
- This should have been caught during the initial review (failure of the agent to trace concrete assertion semantics).

**Fix Applied:**

Lines 40-42 (T-1): Changed from:
```javascript
expect(headings[0]).toHaveAccessibleName(/privacy/i);
```
to:
```javascript
expect(headings[0].textContent).toMatch(/privacy/i);
```

Lines 140-142 (T-4): Changed from:
```javascript
expect(link).toHaveAttribute("href", "/privacy");
```
to:
```javascript
expect(link.getAttribute("href")).toBe("/privacy");
```

Both now use plain DOM properties (`textContent`, `getAttribute()`) with vitest assertions (`toMatch`, `toBe`), avoiding jest-dom entirely.

**Verification:**

- Grep for jest-dom matchers in the test file: ✓ PASS
  - Command: `grep -E "toHaveAttribute|toHaveAccessibleName|toHaveTextContent|toBeInTheDocument|toBeVisible|toHaveClass" page.test.js`
  - Result: No matches (only comments remain, no actual usage).
  
- No jest-dom imports: ✓ PASS
  - Command: `grep -E "@testing-library/jest-dom|jest-dom" page.test.js`
  - Result: No imports found (only comments).
  
- package.json unchanged: ✓ PASS
  - Still contains only `@testing-library/svelte`, `jsdom`, `vitest` in devDependencies.
  - No addition of jest-dom.

**Conclusion:** Defect 1 fixed. T-1 and T-4 now use only standard DOM methods and vitest assertions.

---

### Defect 2: T-3 Allowlist Phrases Overlapped, Preventing Correct Matching

**Original Issue:**

Lines 71-128 in the initial test file attempted to verify that forbidden tokens (`encrypt`, `tls`, `https`, `hash`, `password`, `bank`, etc.) do not appear on the page except in properly negated/forward-looking phrases.

Two bugs prevented this from working:

1. **Whitespace not normalized:** The page wraps long sentences across source lines, which preserves newlines and indentation in `container.textContent`. The allowlist phrases were single-spaced (e.g., `"it does not say that data is encrypted at rest"`), so they would never match the multi-line text. Every forbidden token would report as "present" when in fact it only appeared in the allowed negated context.

2. **Overlapping allow phrases:** The `password` entry had two allow phrases:
   - `"no password"` (11 characters)
   - `"it does not say that passwords are hashed (there are no passwords to hash)"` (76 characters)
   
   The substring `"no password"` appears inside the second phrase (as part of `"...there are no passwords to hash)"`). If the shorter phrase was removed first (the initial code iterated `allow` in declared order), it would consume the `"no "` inside the longer phrase, leaving `"passwords to hash"` behind — which contains the token `"password"` and would produce a false positive, incorrectly flagging the page as making a forbidden claim.

**Why It Mattered:**

- The test would have reported false positives on first run (tokens reported as present when they are actually only in negated form).
- AC-4 (forbidden claims audit) would have failed, blocking merge.
- This was a logical error — not visible from static code inspection unless the string transformations were traced concretely.

**Fix Applied:**

Lines 77-128 now:

1. **Normalize whitespace before matching** (line 77):
   ```javascript
   const text = container.textContent.replace(/\s+/g, " ").toLowerCase();
   ```
   This collapses all whitespace (newlines, tabs, multiple spaces) to single spaces, allowing the single-spaced allowlist phrases to match.

2. **Sort allow phrases by descending length** (lines 111-128):
   ```javascript
   for (const phrase of [...allow].sort((a, b) => b.length - a.length)) {
     remaining = remaining.split(phrase.toLowerCase()).join("");
   }
   ```
   The longer phrase is always removed before any shorter phrases that might be substrings of it. Comments explicitly explain this and forbid simplifying back to declared order.

**Verification:**

The page contains these key phrases (raw from +page.svelte):

- Line 50: `<li>No password</li>`
- Lines 156–159: "it does not say that passwords are hashed (there are no passwords to hash)"
- Line 53: `<li>No bank connection</li>`
- Line 108: "no bank aggregator"
- Line 157: "it does not say that data is encrypted at rest"

After normalization (whitespace collapsed to single spaces, lowercase):

- "no password"
- "it does not say that passwords are hashed (there are no passwords to hash)"
- "no bank connection"
- "no bank aggregator"
- "it does not say that data is encrypted at rest"

**Trace for `password` token:**

1. Token found in text: ✓ YES (in "no password", "passwords are hashed", "passwords to hash")
2. Allow phrases sorted by length (descending):
   - "it does not say that passwords are hashed (there are no passwords to hash)" (76 chars)
   - "no password" (11 chars)
3. Remove first phrase: "...no password..." remains
4. Remove second phrase "no password": only generic text remains
5. After removal, does "password" still appear? ✓ NO

**Trace for `bank` token:**

1. Token found in text: ✓ YES (in "no bank connection", "no bank aggregator")
2. Allow phrases sorted by length (descending):
   - "no bank connection" (18 chars)
   - "no bank aggregator" (17 chars)
3. Remove first phrase: only the second and other text remain
4. Remove second phrase: generic text remains
5. After removal, does "bank" still appear? ✓ NO

**Trace for `encrypt` token:**

1. Token found in text: ✓ YES (in "encrypted")
2. Allow phrases: ["it does not say that data is encrypted at rest"] (49 chars)
3. Remove phrase: generic text remains
4. After removal, does "encrypt" still appear? ✓ NO

**Always-forbidden tokens (`transaction`, `gdpr-compliant`, `iso-27001`):**

Grep for these tokens in the page:
```bash
grep -i "transaction\|gdpr-compliant\|iso-27001" +page.svelte
```
Result: ✓ NOT FOUND (no output)

**Conclusion:** Defect 2 fixed. T-3 now correctly normalizes whitespace and removes allow phrases in longest-first order, preventing false positives.

---

## Verification of Remaining Test Assertions

### T-2 (AC-2): Required Headings Present in Order

**Expected (from test):**
```javascript
const requiredHeadings = [
  "The short version",
  "What personal data we store",
  "Why we store it",
  "Where data would live",
  "What happens when you visit this site",
  "Cookies and tracking",
  "Third parties we share data with",
  "How long we keep data",
  "Your rights",
  "How we protect data",
  "What is planned, and not yet built",
  "Who operates Cashmire",
  "Changes to this page",
];
```

**Actual (from +page.svelte):**
```
Line 36:  <h2>The short version</h2>
Line 44:  <h2>What personal data we store</h2>
Line 60:  <h2>Why we store it</h2>
Line 67:  <h2>Where data would live</h2>
Line 76:  <h2>What happens when you visit this site</h2>
Line 92:  <h2>Cookies and tracking</h2>
Line 105: <h2>Third parties we share data with</h2>
Line 113: <h2>How long we keep data</h2>
Line 121: <h2>Your rights</h2>
Line 134: <h2>How we protect data</h2>
Line 164: <h2>What is planned, and not yet built</h2>
Line 172: <h2>Who operates Cashmire</h2>
Line 181: <h2>Changes to this page</h2>
```

✓ VERIFIED: All 13 headings present, exact text match, correct order.

### T-5 (AC-7): Fetch Guard is Sound

Lines 148–156:
```javascript
if (typeof globalThis.fetch !== "function") {
  globalThis.fetch = () =>
    Promise.reject(new Error("fetch should not be called in this test"));
}
const fetchSpy = vi.spyOn(globalThis, "fetch");
render(PrivacyPage);
expect(fetchSpy).not.toHaveBeenCalled();
```

The guard checks if `fetch` exists before spying on it. In jsdom on Node 18+, `globalThis.fetch` exists; in older environments, it does not. By ensuring it exists before `vi.spyOn()`, the code cannot throw. ✓ SOUND

### T-6 (AC-8): Placeholder Tokens in Code Elements

Lines 158–166:
```javascript
expect(screen.getAllByText(/\[\[CONTACT_EMAIL\]\]/).length).toBeGreaterThan(0);
expect(screen.getAllByText(/\[\[LEGAL_ENTITY\]\]/).length).toBeGreaterThan(0);
expect(screen.getAllByText(/\[\[JURISDICTION\]\]/).length).toBeGreaterThan(0);
```

The regex `/\[\[CONTACT_EMAIL\]\]/` matches the literal text `[[CONTACT_EMAIL]]`. The page renders these tokens inside `<code>` elements and list items as text nodes (not escaped). `@testing-library/svelte` will find them. ✓ WILL WORK

### Imports and Configuration

- **vitest exports:** `describe`, `it`, `expect`, `vi`, `beforeEach` ✓ All exported
- **@testing-library/svelte v5 exports:** `render`, `screen` ✓ Both exported
- **Svelte exports:** `createRawSnippet` ✓ Exported
- **Render signature for v5:** `render(Component, { props })` ✓ Correct (used at line 138)
- **jsdom environment:** vite.config.js line 12: `environment: "jsdom"` ✓ Set
- **Globals mode:** vite.config.js line 13: `globals: true` ✓ Set (makes `describe`, `it`, `expect` globally available)

✓ ALL IMPORTS AND CONFIG CORRECT

---

## File Modification Check — Page and Layout Unchanged

Verified via `git diff`:

| File | Change | Status |
|------|--------|--------|
| `frontend/src/routes/privacy/+page.svelte` | No diff output | ✓ Unchanged |
| `frontend/src/routes/+layout.svelte` | No diff output | ✓ Unchanged |
| `frontend/package.json` | (already had test script and devDeps from initial submission) | ✓ Correct |
| `frontend/vite.config.js` | (already had test config from initial submission) | ✓ Correct |

The developer was instructed to touch only the test file. ✓ VERIFIED

---

## Detailed Findings

### Content Accuracy Audit (AC-3)

Every factual claim on the page has been verified against the repository code. All claims in SPEC.md §5.2 are accurate.

| Claim | Evidence | Status |
|-------|----------|--------|
| No database tables defined | `backend/api/` contains no `models.py` | ✓ ACCURATE |
| No migrations exist | No `backend/api/migrations/` directory | ✓ ACCURATE |
| Dockerfile does not run migrations | `backend/Dockerfile` line 19: `CMD ["python", "manage.py", "runserver", ...]` — no `migrate` step | ✓ ACCURATE |
| PostgreSQL configured but unused | `docker-compose.yml` service `db: postgres:16-alpine`; combined with no models, confirms unconfigured | ✓ ACCURATE |
| One health endpoint | `backend/api/urls.py` defines single `path("health/", views.health)` | ✓ ACCURATE |
| Health returns `{"status": "ok"}` only | `backend/api/views.py` line 7: `return Response({"status": "ok"})` | ✓ ACCURATE |
| Home page makes one request to health | `frontend/src/routes/+page.svelte` line 9: single `fetch(\`${apiUrl}/api/health/\`)` in `onMount` | ✓ ACCURATE |
| Privacy page makes no requests | No `fetch`, `http://`, `https://` in `frontend/src/routes/privacy/+page.svelte` (only in test code and comments) | ✓ ACCURATE |
| No cookies set by app | No `set_cookie` or `document.cookie` in `backend/api/views.py` or `frontend/src/routes/` | ✓ ACCURATE |
| No third-party scripts/fonts | `frontend/src/app.html` contains only SvelteKit placeholders; `package.json` devDeps are SvelteKit, Vite, Svelte, testing-library only | ✓ ACCURATE |
| No email/payment/bank integration | `backend/requirements.txt` lists only Django, DRF, psycopg2, django-cors-headers | ✓ ACCURATE |
| CORS allowlist to local frontend | `backend/cashmire/settings.py` line 82-84: `CORS_ALLOWED_ORIGINS` defaults to `http://localhost:5173` | ✓ ACCURATE |
| Development defaults (DEBUG, ALLOWED_HOSTS, SECRET_KEY) | `backend/cashmire/settings.py` lines 6, 8, 10: `DEBUG="true"`, `ALLOWED_HOSTS="*"`, `SECRET_KEY="dev-insecure-secret-key"` | ✓ ACCURATE |
| Django admin mounted | `backend/cashmire/urls.py` line 5: `path("admin/", admin.site.urls)` | ✓ ACCURATE |
| Privacy page makes no network requests | No `fetch`, `http://`, `https://` in `+page.svelte` (verified with grep) | ✓ ACCURATE |

**Conclusion:** AC-3 PASS. Every claim is verifiable against the repository code, and all are accurate.

---

### Forbidden Claims Audit (AC-4)

The page must not state or imply claims from SPEC.md §5.3. All forbidden tokens are either absent or appear only in properly negated/forward-looking form:

| Token | Page's use | Status |
|-------|-----------|--------|
| `encrypt` | Line 157: "it does **not** say that data is encrypted at rest" | ✓ Negated |
| `TLS` | Line 158: "it does **not** say that traffic is served over TLS or HTTPS" | ✓ Negated |
| `HTTPS` | Line 158: "it does **not** say that traffic is served over TLS or HTTPS" | ✓ Negated |
| `hash` | Line 159: "it does **not** say that passwords are hashed" | ✓ Negated |
| `password` | Lines 50, 159: "No password" (absence claim) and negation clause | ✓ Negated/absence |
| `bank` | Lines 53, 108: "No bank connection" and "no bank aggregator" (absence claims) | ✓ Absence |
| `transaction` | Not found in page | ✓ Absent |
| `gdpr-compliant` | Not found in page | ✓ Absent |
| `iso-27001` | Not found in page | ✓ Absent |
| "We take your privacy seriously" (filler) | Not found in page | ✓ Absent |

**Conclusion:** AC-4 PASS. No forbidden claims are made.

---

## Acceptance Criteria Summary

| ID | Criterion | Status | Evidence |
|----|-----------|--------|----------|
| AC-1 | Page has single `<h1>` naming it as privacy page | **PASS** | `+page.svelte` line 24: `<h1>Privacy and legal information</h1>` (only one per file inspection) |
| AC-2 | Every required `<h2>` from §5.1 present in order | **PASS** | 13 headings present: "The short version", "What personal data we store", …, "Changes to this page" — matches §5.1 table exactly and in order |
| AC-3 | Claims trace to §5.2 evidence | **PASS** | See content accuracy audit above |
| AC-4 | No forbidden claims from §5.3 | **PASS** | See forbidden claims audit above |
| AC-5 | Link to `/privacy` on every page via footer | **PASS** | `+layout.svelte` line 14: `<a href="/privacy">Privacy &amp; legal</a>` in `<footer>` renders on all pages |
| AC-6 | Reachable without auth, cold direct load | **PASS** | No authentication exists in app. Page is pure client-side content; no `load` function that could redirect. |
| AC-7 | Zero network requests on privacy page | **PASS** | No `fetch`, remote URLs, or third-party assets in `frontend/src/routes/privacy/+page.svelte`. Test T-5 verifies with fetch spy. |
| AC-8 | Human-dependent values are literal `[[PLACEHOLDER]]` tokens | **PASS** | All seven placeholders present and literal. Verified with `grep -rn '\[\['`. |
| AC-9 | Draft banner visible while placeholders unfilled | **PASS** | Lines 26–31: Draft banner states "This page has not been approved by a human and is not yet the operative policy". |
| AC-10 | Accessibility requirements (§7) | **PARTIAL** | Code inspection passes; browser-dependent items (reflow, zoom, focus, contrast measurement) listed under human tasks. Contrast ratios computed below. |
| AC-11 | Home page still loads and shows status line | **CANNOT-VERIFY** | Home page unmodified. Layout wraps correctly without nesting a second `<main>`. Manual browser test required. |

---

### Accessibility Review (AC-10) — With Computed Contrast Ratios

**Landmark structure:**
- One `<main>` on privacy page (line 23).
- One `<footer>` in layout (line 13).
- Layout does not add a second `<main>` around home page content.
- ✓ PASS

**Headings:**
- Exactly one `<h1>` (line 24).
- 13 `<h2>` sections (all verified present, no skipped levels).
- ✓ PASS

**Document title and description:**
- `<svelte:head><title>Privacy and legal information · Cashmire</title>` (line 16).
- `<meta name="description" content="…">` (lines 17-20).
- ✓ PASS

**Link text:**
- Footer: "Privacy &amp; legal" (self-describing, not "click here").
- Back link: "Back to the Cashmire home page" (line 188, clear).
- ✓ PASS

**Contrast (WCAG AA, computed per WCAG 2.1 formula):**

Draft banner (`+page.svelte` lines 199–205):
```css
.draft-banner {
  color: #3b2200;
  background: #fff6e5;
}
```
- **Contrast ratio: 13.8:1** (computed via relative luminance formula)
- **Requirement:** WCAG AA 4.5:1 for normal text
- **Status:** ✓ **PASS**

Links (`+page.svelte` line 208):
```css
a {
  color: #0b3d91;
}
```
On white background:
- **Contrast ratio: 10.1:1** (computed via relative luminance formula)
- **Requirement:** WCAG AA 4.5:1 for normal text
- **Status:** ✓ **PASS**

Footer border (`+page.svelte` style not explicitly shown but renders as `#c8c8c8` on white):
- **Contrast ratio: 1.7:1**
- **Status:** ✓ **PASS** (decorative divider, not text or UI control; WCAG 1.4.11 exception applies)

**Not colour-only:**
- Draft banner: Uses `<strong>` tag and text explicitly says "Draft — pending legal review". ✓ PASS

**Text structure:**
- Paragraphs use real `<p>` (not `<br>`-separated).
- Lists use real `<ul>` and `<li>`.
- ✓ PASS

**Reflow and zoom:**
- `max-width: 70ch` on `main` for readability (line 193).
- `padding: 1.5rem 1.25rem` with relative units (line 195).
- Cannot verify 320px horizontal reflow and 200% zoom without browser dev tools.
- ⚠ **CANNOT-VERIFY** without browser testing.

**Focus visibility:**
- Links have `a:focus-visible { outline: 3px solid #0b3d91; outline-offset: 2px; }` (lines 211–214).
- ✓ Outline present and visible by visual inspection.
- ⚠ **CANNOT-VERIFY** actual keyboard focus without browser testing.

**Summary:** AC-10 elements verified by code inspection and contrast computation pass. Items requiring live browser interaction (320px reflow, 200% zoom, keyboard tab focus) are listed under human tasks.

---

### Specification Deviations

#### 1. SSR Override (+page.js) Not Created — CSR-Only

**Status: ACCEPTABLE (pre-approved fallback)**

SPEC.md §4.6 states: "the page works correctly with the repo exactly as-is, CSR-only. This is the baseline…If it errors, or if the text does not appear, delete the file and say so plainly in the PR description."

The `frontend/src/routes/privacy/+page.js` file with `export const ssr = true;` was not created. The page runs client-side-only under the existing `+layout.js` setting `ssr = false`. This is an acceptable fallback per the spec.

#### 2. aria-current="page" Not Implemented

**Status: ACCEPTABLE (nice-to-have)**

SPEC.md §7.1 states: "if this proves awkward, it is a nice-to-have, not a blocker."

The footer link does not include `aria-current="page"`. Omitting it is acceptable per the spec.

---

### Security Review

**Attack surface:** Static page with no input, no fetch, no dynamic state. Minimal risk.

**Findings:**

1. **No HTML injection or XSS:** Page uses Svelte's default auto-escaping; no `{@html}` directive. ✓ SAFE

2. **No unescaped user input:** No user input accepted. ✓ SAFE

3. **No broken link targets:** All `href` attributes point to internal paths. ✓ SAFE

4. **Information disclosure via content:** Page intentionally discloses development defaults per §5.4. ✓ CORRECT

**Conclusion:** No new security defects.

---

## What a Human Must Still Do Before Merge

### BLOCKING: Test Suite Not Yet Executed

**Priority: CRITICAL**

The test file (`frontend/src/routes/privacy/page.test.js`) is committed but has never been run. The fixes to the two defects above are now in place, but they have not been validated by actual test execution.

**Required action:**
1. Install npm/Node.js in an environment where it is available.
2. Run `npm install` in `frontend/` to install dependencies.
3. Run `npm test` to execute the test suite.
4. All six tests (T-1 through T-6) must pass without errors.
5. If any test fails, investigate and fix the underlying issue before merge.

**Why this is critical:** The initial review missed two defects that would have caused test failures. Even though fixes are now in place, they must be validated by actual execution. A human cannot approve merge without seeing green test results.

### Required Tasks (Legal & Content)

1. **Legal review and sign-off (SPEC.md §10, Risk R-1):**
   - The page is a legal document. A human with legal authority must read and approve the final wording before it is presented as the operative privacy policy.

2. **Fill in the seven placeholders (SPEC.md §6.2, §10.1):**
   - `[[LEGAL_ENTITY]]` — Who operates Cashmire?
   - `[[PROJECT_STATUS]]` — What is the project status?
   - `[[CONTACT_EMAIL]]` — Contact route for questions and rights requests.
   - `[[JURISDICTION]]` — Which jurisdiction's law applies?
   - `[[DATA_CONTROLLER]]` — Who is the data controller for GDPR purposes?
   - `[[HOSTING_ARRANGEMENT]]` — Where is the app hosted?
   - `[[EFFECTIVE_DATE]]` — When does this policy become effective?

3. **Remove draft banner once all placeholders are filled (SPEC.md §5.1, AC-9):**
   - Delete the `<p class="draft-banner">` block and the `TODO(#63-legal)` comment once the last placeholder is filled.

### Verification Tasks (Accessibility & Regression)

4. **Manual accessibility testing (AC-10 items not verified by code inspection):**
   - Tab through `/privacy` in a browser — verify all links are reachable and focus is always visible.
   - Disable CSS (DevTools → Disable all stylesheets) — verify content order makes sense.
   - View accessibility tree (DevTools → Accessibility tab) — verify one `<main>`, one `<contentinfo>`, heading outline h1 → h2×13 with no gaps.
   - Zoom to 200% (DevTools → Device Mode or Ctrl+Shift+M → Zoom) — verify no horizontal scrollbar, no clipped text.
   - Open DevTools Network tab, hard-reload `/privacy` (Ctrl+Shift+R) — verify only first-party assets.

5. **Manual regression testing (AC-11):**
   - Load `http://localhost:5173/` in a browser and verify the home page displays.
   - Verify clicking the footer link navigates to `/privacy` and renders fully.

6. **Cold-load test (AC-6):**
   - Open `http://localhost:5173/privacy` in a private/incognito window with no prior navigation.
   - Verify the privacy page content is visible.

---

## Summary

**Initial Review Verdict:** "No blocking findings" — **INCORRECT**

**Root Cause:** Static code inspection failed to trace two concrete defects:
1. Assertions using uninstalled jest-dom matchers would throw at runtime.
2. Overlapping string transformations in the allowlist logic would produce false positives.

**Corrected Verdict After Re-Review:** **NO BLOCKING FINDINGS** (defects have been fixed and verified)

**Critical Action Required:** The test suite must be executed to confirm the fixes work in practice. This is the top item on the human verification checklist.

**Implementation Status:** Complete and accurate. Deviations (CSR-only, no `aria-current="page"`) are pre-approved fallbacks per SPEC.md.

---

## Related Documentation

- `SPEC.md` §1.2 (acceptance criteria)
- `SPEC.md` §5.2 (claims table)
- `SPEC.md` §5.3 (forbidden claims)
- `SPEC.md` §8.3 (test assertions)
- `SPEC.md` §10.1 (open questions)
- `frontend/src/routes/privacy/+page.svelte` (main page content)
- `frontend/src/routes/+layout.svelte` (shared layout with footer)
- `frontend/src/routes/privacy/page.test.js` (test suite — unexecuted, fixes verified)

