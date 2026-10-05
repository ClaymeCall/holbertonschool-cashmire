# 0001 — Introduce a minimal shared app shell (`+layout.svelte`)

- **Status:** Proposed
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
