# 0001 — Introduce a minimal shared app shell (`+layout.svelte`)

- **Status:** Proposed — amended by #15, #104 (×3)
- **Date:** 2026-10-05
- **Context issue:** #63 (privacy and legal information page)
- **Supersedes / superseded by:** —

## Context

Until now the SvelteKit frontend has had exactly one page
(`frontend/src/routes/+page.svelte`) and no shared component at all. There is a
`frontend/src/routes/+layout.js` containing only `export const ssr = false;`,
but no `+layout.svelte`, no nav, no footer, no global stylesheet, and no
`src/lib/`.

Issue #63 needs a privacy link reachable from every page. That is the first
requirement in the project for chrome that is not page-specific, so the question
of "where does app-wide UI live" has to be answered now rather than later.

## Decision

1. **Add `frontend/src/routes/+layout.svelte` as the single shared app shell.**
   It renders the page content and a `<footer>` containing site-wide links.

2. **Keep it genuinely minimal.** For now the shell is a footer and nothing
   else: no header bar, no logo, no nav menu, no theme control, no global CSS
   reset, no design system, no `src/lib/` component directory. With two pages, a
   nav component would be more structure than content. Chrome gets added when a
   page needs it, not in anticipation.

3. **`+layout.js` and `+layout.svelte` coexist; neither is merged into the
   other.** `+layout.js` carries page options (currently `ssr = false`);
   `+layout.svelte` carries markup. Both apply to the whole route tree. The
   existing `ssr = false` is left alone — changing the app-wide rendering mode
   is not a side effect that belongs in a content PR.

4. **Pages own their `<main>` element; the layout does not provide one.** The
   existing home page already renders `<main>`, and the alternative would mean
   editing a page this work has no other reason to touch. Every new page is
   therefore responsible for its own `<main>` landmark.

5. **Per-route page options are the mechanism for per-page rendering
   differences.** Where a specific page needs behaviour the app-wide default
   does not give it (e.g. server rendering for a content page under a CSR-only
   app), that is expressed in that route's own `+page.js`, not by changing the
   root default.

6. **Styling stays component-scoped** until there is a concrete reason for a
   global stylesheet. The first PR that genuinely needs shared tokens should
   introduce them and amend this record.

## Consequences

- Site-wide links have one obvious home, and the next page added gets the footer
  for free.
- The whole app remains client-rendered by default; nothing about the existing
  home page changes.
- Adding a second shared element later (a header, say) is a small edit to one
  file rather than a refactor.
- Risk: a shared shell tends to accrete. Point 2 is the guard — reviewers should
  push back on additions to the layout that no current page requires.
- Risk: the "pages own `<main>`" rule is easy to forget and produces a page with
  no main landmark. It is cheap to catch in review and should be part of the
  checklist for any new route.

## Amendment — 2026-10-05 (issue #15)

**What changed:** point 2's "no header bar, no logo, no nav menu" no longer
holds. `frontend/src/routes/+layout.svelte` now also renders a `<header>`
containing a brand link (`Cashmire`, `/`) and a `<nav aria-label="Main">`
with links to `Home` (`/`) and `Privacy` (`/privacy`). The active link is
marked with `aria-current="page"`, driven off `$app/state`'s `page.url`.

**Why:** the app now has two real routes (`/` and `/privacy`), and until
this change the only way to reach `/privacy` was the footer link, with no
way back to `/` other than the browser's back button. Issue #15 asks for a
navigable shell now that there is more than one page to navigate between;
deferring a two-link nav further would mean every new route re-litigates
the same question.

**What is unchanged:** points 3, 4, 5 and 6 still hold exactly as written —
`+layout.js` and `+layout.svelte` still coexist and neither is merged into
the other; pages still own their own `<main>` (the layout adds no `<main>`
of its own); per-route page options are still the mechanism for per-page
rendering differences; styling is still component-scoped in the layout's
own `<style>` block, with no global stylesheet, CSS reset or design tokens
introduced. Point 2's "accretion" warning stands for anything beyond these
two links — this amendment is not a licence for a sidebar, theme switcher
or auth menu later.

## Amendment — 2026-10-06 (issue #104, design-system slice)

**What changed:** point 6 ("styling stays component-scoped until there is a
concrete reason for a global stylesheet") no longer holds without
qualification. By the time #28/#29 (login/register) landed, the same color,
spacing, border, and focus-ring values were being hand-typed in three
places (`+layout.svelte`, `login/+page.svelte`, `register/+page.svelte`),
and `privacy/+page.svelte` had its own copies of the same primary/warning
colors — the "concrete reason" point 6 asked for. This amendment
introduces:

- `frontend/src/lib/styles/tokens.css` — `:root` custom properties naming
  the colors, spacing scale, border radius, and focus-ring values already
  in use. No new values were invented; existing hex codes were given names.
  It is imported from wherever it's consumed (the layout, and each shared
  component below) rather than globally in `app.html` — Svelte's
  per-component style scoping does not apply to `:root` custom properties,
  so this is sufficient for the variables to resolve document-wide once any
  importer is on the page.
- `frontend/src/lib/components/Button.svelte`, `TextField.svelte`, and
  `FormError.svelte` — the three repeated patterns (a submit button, a
  labelled input with an optional hint, and a form-level `role="alert"`
  block for one message or a list) factored out of login/register into
  reusable components built on the tokens above.
- `+layout.svelte`, `login/+page.svelte`, `register/+page.svelte`, and
  `privacy/+page.svelte` were adopted to use the tokens (and, for
  login/register, the shared components) in place of their local copies.

**What is unchanged:** points 2 through 5 still hold — the layout still adds
no header/nav/footer beyond what #15 already introduced, still adds no
`<main>`, and `+layout.js`/`+layout.svelte` still coexist. This is a styling
amendment, not a structural one.

**What is explicitly deferred:** issue #104's full scope — expanding the nav
to cover expenses/budgets, making it auth-state-aware, and replacing the
home page's health-check placeholder with the budgets/expenses dashboard —
depends on screens from #40/#41/#52/#53 and a session/auth-state mechanism
(#25), none of which exist in this codebase yet. This amendment covers only
the design-system foundation; the nav/dashboard work is a follow-up once
those land. A `Card` style is likewise not introduced yet, since no screen
needs one until the budget/expense dashboards exist.

## Amendment — 2026-10-07 (issue #104, nav/dashboard slice)

**What changed:** the deferral above is resolved now that #40/#41 (expense
screens) and #52/#53 (budget screens) exist.

- **Nav is auth-state-aware.** Logged out, it still shows exactly
  `Home`/`Log in`/`Register`/`Privacy` (unchanged from #15/#28/#29). Logged
  in, it shows `Dashboard`/`Expenses`/`Budgets`/`Privacy`, plus a `Log out`
  control — a `<button>`, not a nav link, since it performs an action
  rather than navigating. The `/` link's label switches between "Home" and
  "Dashboard" with the same `href`, matching what that route actually shows
  for each audience (see below).
- **`frontend/src/lib/stores/auth.js`** is the "session/auth-state
  mechanism" the previous amendment named as a dependency. It is an
  **in-memory-only** Svelte store: nothing is written to `localStorage` or
  `sessionStorage`, per
  [`0003`](./0003-session-cookie-auth-strategy.md) point 6 (no client-held
  token or identity for an XSS payload to read). It is populated only by
  `login`/`register`'s own existing success handlers (recording that their
  own request just succeeded — not a new request) and cleared by `logout`
  calling `POST /api/auth/logout/`. It is **not** populated by probing
  `GET /api/auth/me/` on layout mount or on navigation — `routes/layout.test.js`'s
  T-4b ("rendering the layout issues zero fetch calls") already locks in
  that the shared shell itself never makes a network request, and this
  amendment keeps that true.
  - **Known consequence, accepted for this slice:** a hard page reload
    resets the store to "logged out" even with a still-valid session
    cookie, until the next login/register. Revisit once #26/#27
    (current-user dependency) land, if the team decides a `/api/auth/me/`
    check belongs somewhere (e.g. a route-level `load`, not the shared
    layout) despite the cost of relaxing T-4b's guarantee.
- **`/` now shows the real dashboard for a logged-in user** — each budget's
  consumption/status and recent expenses, per `docs/mvp-scope.md`'s central
  journey, step 3 — and a public landing (what Cashmire is, links to
  `/login`/`/register`) for a logged-out visitor, since there is no session
  to scope personal data to. The `/health` check this page used to run
  moved to its own route back in #18 and stays reachable from the footer;
  it is not duplicated here.
- **`frontend/src/lib/components/BudgetCard.svelte`** is the `Card` style
  the previous amendment deferred until "the budget/expense dashboards
  exist" — true as of this amendment, since the home dashboard now needs
  the exact same budget-card rendering `routes/budgets/+page.svelte`
  already had. Factored out so both consumers share one implementation
  rather than drifting apart.

**What is unchanged:** points 2 through 6 and the prior amendments still
hold — no new global stylesheet, `+layout.js`/`+layout.svelte` still
coexist, pages still own their own `<main>`, and the layout still adds no
`<main>` of its own. The nav/button addition is the only structural change
to `+layout.svelte` itself.

**What is explicitly deferred:** swapping any of this for real backend
calls (#92 and its dependencies — the budget API in particular is still
unmerged at the time of this amendment); the responsive layout pass (#64)
and the accessibility pass (#65), neither of which this amendment should
regress but whose checklists are owned elsewhere; and the reload-resets-to-
logged-out limitation named above.

## Amendment — 2026-10-07 (issue #104, Cashmire visual overhaul)

**What changed:** point 6 is amended a second time. The previous
amendment's tokens (`frontend/src/lib/styles/tokens.css`) are repointed
from placeholder blue/grey values to the full Cashmire palette
(warm neutrals, Fraunces/IBM Plex Mono/DM Sans typography, soft radii,
dark mode) specified in
`docs/specs/issue-104-cashmire-design-system.md`. A new
`frontend/src/lib/styles/base.css` is introduced for true document-wide
defaults — `html`/`body` background and font, heading font/color, link
color, `code`/`pre` font, a `focus-visible` fallback — imported once from
`+layout.svelte` alongside `tokens.css`. The same reasoning that justified
`tokens.css` applies here, one layer up: once every screen shares one
typeface per role and one background, repeating `font-family`/
`background`/`color` in each component's own `<style>` block is exactly
the duplication a global stylesheet exists to prevent. `base.css` defines
no component-specific class and no layout/structure — points 2–5 are
untouched, and anything beyond these seven document-wide rules still
belongs in the owning component.

Fraunces/IBM Plex Mono/DM Sans are self-hosted
(`frontend/static/fonts/*.woff2`, referenced by `frontend/src/lib/styles/fonts.css`),
not loaded from Google Fonts — decision `0002` point 5 requires a
privacy-page update for any "third-party service ... hosted fonts," and
`/privacy`'s own spec requires zero third-party network requests
(`docs/specs/issue-63-privacy-page.md` AC-7). Self-hosting the same
open-license files keeps both true without touching `/privacy`.

**What is unchanged:** points 2–5 still hold exactly as in the previous
two amendments. This is again a styling amendment, not a structural one —
no new route, no new nav entry, no `<main>` added to the layout.

**What is explicitly deferred:** the nav/dashboard slice this amendment
once deferred landed separately (see the amendment immediately above) and
is not part of this change — this amendment only repoints colors/typography
on top of it. Macro cashmere photography, line illustration, and a chart
color palette from the design brief are also deferred: no asset-sourcing
pipeline exists for the former, and no chart or budget/expense screen
exists yet to consume the latter. See
`docs/specs/issue-104-cashmire-design-system.md` §3.5 for the full list and
reasoning.
