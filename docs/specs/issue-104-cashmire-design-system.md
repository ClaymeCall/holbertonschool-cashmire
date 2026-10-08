# SPEC — Cashmire design system: visual overhaul (foundation slice)

- **Issue:** #104 "Unify the front-end into one navigable site: shared design
  system, full nav shell, home dashboard"
- **Scope of this slice:** the design-system bullet of #104's acceptance
  criteria only — color tokens, spacing scale, typography, button/input/card
  styles, applied to every screen that exists on `main` today. **Not** in
  this slice: expanding the nav to expenses/budgets, auth-state-aware nav,
  or a dashboard home page — those acceptance criteria depend on screens
  from #40/#41/#52/#53, which are not on this branch. See "Explicitly out of
  scope" below.
- **Codebase surveyed at:** branch `main`, commit `833e599`

---

## 1. Why this is a slice, not all of #104

Issue #104 bundles four things: (a) a shared design system, (b) expanding
the nav to cover expenses/budgets, (c) an auth-aware nav, and (d) a
dashboard home page replacing the health-check placeholder. (b), (c) and
(d) all require screens — expense list/create/edit, budget dashboard/
create/edit — that do not exist on `main`; #104 itself lists them as
dependencies (#40, #41, #52, #53). Building a nav entry or a dashboard
against a screen that isn't there would mean dead links or invented
content.

(a) has no such dependency: it is a token/typography/component change
applicable to the five screens that already exist (`/`, `/login`,
`/register`, `/privacy`, `/health`) and the shared shell. This PR does
that slice and leaves #104 open for the remaining three once their
dependent screens land — consistent with how decision `0001`'s two
previous amendments each covered one slice of shell/styling work rather
than waiting for the full issue.

## 2. The brief

The design direction, palette, type system, and component rules
implemented here were supplied as a product brief ("Cashmire design
system (draft)"), reproduced in full below for traceability between this
spec and the rendered result.

### 2.1 Aesthetic direction

> "Quiet luxury, softly handled." Think a folded cashmere sweater in a
> boutique: warm neutrals, generous space, soft edges, and precise numbers.

- Warm, low-contrast backgrounds. Never pure white or pure black.
- Soft shapes (16–24px radii) paired with exact, ledger-like data.
- Tactile details: a faint weave or grain texture, stitched dividers, and
  macro wool photography.
- Slow, gentle motion (300–500ms ease-out), nothing bouncy.

### 2.2 Typography

| Role | Font | Why |
|---|---|---|
| Cosy/premium headers | Fraunces (soft, light weight) | Rounded serif forms feel like wool. Hero text, page titles, emotional moments. |
| Finance headers | IBM Plex Mono | Ledger/terminal feel — "numbers you can trust." Balances, section labels, table headers, category tags. |
| Body/UI | DM Sans | Friendly geometric sans between the serif and the mono. |

Rules: Fraunces for sentences, mono for data labels — never mixed in the
same line. Tabular numerals on all amounts. Body text 16px/1.6. Mono
labels uppercase with +0.04em tracking.

### 2.3 Color palette

Core (cashmere wool): Ivory `#F7F2E9` (page bg), Oatmeal `#E9DFCC`
(surfaces), Camel `#C49A6C` (primary accent/CTA), Heather taupe `#A39384`
(secondary text/borders), Mocha `#6A4E3F` (headings/hover), Espresso
`#2A231F` (body text / dark bg).

Accents: Dusty rose `#D8B4A8`, Heather sage `#9AA68C`.

Semantic (muted, never neon): income/under-budget = moss `#6E8F68`,
overspend = terracotta `#B4543C`, warning = ochre `#D1A24A`.

Dark mode: Espresso `#1F1A17` background, surfaces `#2A231F`, text Oatmeal
`#E9DFCC`, Camel stays the accent.

### 2.4 Visual/asset rules

Macro cashmere photography for hero backgrounds/empty states; a 3–4%
opacity knit/weave texture on surfaces; fine single-weight line illustration
in Mocha/Camel; Oatmeal cards with 1px taupe borders and soft warm shadows;
dashed "stitched" dividers; pill-shaped Camel-fill/Ivory-text buttons;
charts in Camel/Sage/Rose/Taupe with rounded bars, no gridline clutter;
calm, reassuring, plainspoken voice.

## 3. What was implemented

### 3.1 Token layer (`frontend/src/lib/styles/tokens.css`)

Every color, radius, and focus-ring value a component already consumed
(`--color-primary`, `--color-border`, `--radius-sm`, etc. — introduced by
the earlier #104 slice, see decision `0001`'s second amendment) was
**repointed** to the Cashmire palette rather than renamed, so this PR
restyles every existing screen without having to touch every call site.
New tokens were added for concepts the old system had no name for:
`--font-heading`/`--font-mono`/`--font-body`, `--radius-md`/`--radius-lg`/
`--radius-full`, `--motion-duration`/`--motion-ease`, `--shadow-soft`,
`--texture-weave`, and a `--color-success-*` triad (the brief's "moss"
semantic had no home in the old error/warning-only token set).

**Two values intentionally do not match the brief's literal hex codes**,
because a 1:1 swap fails WCAG contrast:

| Token | Brief's hex | Used instead | Why |
|---|---|---|---|
| Button fill (`--color-cta-bg`) | Camel `#C49A6C` | `#8F5F26` (deep camel) | Ivory text on plain Camel is ≈2.3:1; AA requires 4.5:1 for normal text. `#8F5F26` keeps the same hue and clears ≈4.9:1. |
| Muted/hint text (`--color-text-muted`) | Heather taupe `#A39384` | `#7D6854` | Heather taupe on Ivory is ≈2.7:1. `#7D6854` clears ≈4.7:1. |

Plain Camel and Heather taupe are kept as tokens for decorative,
non-text uses (active-nav fill behind white text, dividers, future chart
fills) where the lighter value is the correct one. Contrast ratios for
every text/background pairing introduced here were computed against the
WCAG relative-luminance formula before being picked; see the header
comment in `tokens.css` for the reasoning kept next to the values.

Dark mode is wired via `@media (prefers-color-scheme: dark)` — automatic,
with no theme-switcher UI, which decision `0001` point 2 still rules out.

### 3.2 Typography (`frontend/src/lib/styles/fonts.css`)

Fraunces (300, 300 italic, 600), IBM Plex Mono (400, 500), and DM Sans
(400, 500, 700) are **self-hosted**: the woff2 files live in
`frontend/static/fonts/` and are served from this app's own origin, not a
Google Fonts `<link>`/`@import`. This is not a style preference — decision
`0002` point 5 requires a privacy-page update for "a third-party service
... hosted fonts," and the privacy page's own spec (AC-7) requires `/privacy`
to issue zero third-party network requests. Self-hosting the same
open-license (OFL) files keeps both true with no privacy-page change
needed. Only the Latin subset of each weight was kept (covers ASCII plus
the accented characters used in this repo's French docs/UI copy);
Cyrillic/Vietnamese/Greek subsets were dropped to keep the payload small
(~184KB total across 8 files).

### 3.3 Global base layer (`frontend/src/lib/styles/base.css`, new)

Decision `0001` point 6 ("styling stays component-scoped") is amended
again here, the same way its second amendment already did for tokens:
adopting one typeface per role and one background across every screen
would mean repeating the same `font-family`/`background`/`color`
declarations in each component's own `<style>` block — the exact
duplication a global stylesheet exists to avoid. `base.css` is kept to
true document-wide defaults only: `html`/`body` background and font,
heading font/color, link color, `code`/`pre` font (mono, so inline code
already reads as "data" per the brief), and a `focus-visible` fallback. It
defines no component-specific class — anything beyond these defaults
stays in the owning component's own `<style>` block.

### 3.4 Components and screens

- **`Button.svelte`**: pill shape (`--radius-full`), Camel-deep fill /
  Ivory text for primary, Mocha-outline-on-hover; secondary variant is an
  outline button. Gentle color transition on hover (`--motion-duration`/
  `--motion-ease`), per the brief's "slow, gentle motion... nothing
  bouncy."
- **`TextField.svelte`**: label switched to the mono/uppercase/tracked
  treatment the brief specifies for data labels; input border uses the
  taupe family with a soft radius and a gentle hover/focus transition.
- **`FormError.svelte`**: radius bumped to `--radius-md`; colors already
  routed through tokens, now resolving to the terracotta ("overspend")
  semantic.
- **`+layout.svelte`** (shared shell): header/footer get the surface color
  plus the faint weave texture (`--texture-weave`) and a dashed
  ("stitched") border in place of the old solid 1px line; brand mark set
  in Fraunces; nav links get a pill hover/active treatment (Camel fill on
  the current page); footer switches to the mono/uppercase/tracked
  treatment, since footer links read as navigational labels rather than
  body prose.
- **`/` (home)**: hero `<h1>` set in light-italic Fraunces; API status
  value wrapped in `<code>` so it renders in the mono "data" face.
- **`/login`, `/register`**: no structural change — these already
  consumed the shared tokens (earlier #104 slice), so the new palette and
  fonts apply automatically through `base.css` and the components above.
- **`/privacy`**: draft-banner radius bumped to `--radius-md` to match the
  new card language; content and claims table untouched (no data-handling
  behavior changed, so decision `0002` point 5 does not apply here).
- **`/health`**: this was the one screen the earlier #104 slice did not
  reach — it still had hardcoded hex (`#0b3d91`, `#8a8a8a`, `#f1f1f1`,
  ...) instead of tokens. Brought onto the shared tokens here, including a
  new `--color-success-*` triad for its "API is reachable" state (the old
  token set only had error/warning, not success).

### 3.5 What is deliberately not in this slice

- **Macro cashmere photography / line illustration.** The brief calls for
  macro wool photography and single-weight line art (yarn, needles, folded
  knits). No asset-sourcing pipeline exists in this repo (no CMS, no image
  host, no stock-photo license) and inventing placeholder imagery would be
  asset debt, not design-system debt. Hero backgrounds and empty states use
  the texture/color/type system only. Revisit once an asset source is
  decided.
- **Chart color palette (Camel/Sage/Rose/Taupe, rounded bars).** No chart
  exists in the app yet — budgets/expenses screens aren't built. Decision
  `0001`'s second amendment deferred a `Card` component for the same
  reason ("no screen needs one yet"); charts follow the same rule. The
  semantic tokens (`--color-income-*`, `--color-overspend-*`,
  `--color-warning-*`) are in place so the first chart/budget screen can
  consume them directly.
- **Nav expansion, auth-aware nav, dashboard home.** See §1.

## 4. Acceptance criteria (this slice)

| ID | Criterion | How it is checked |
|---|---|---|
| AC-1 | `frontend/src/lib/styles/tokens.css` defines the full Cashmire palette, typography, spacing, radius, motion and dark-mode tokens, and every existing component/page consumes them (no literal hex color left in `frontend/src/routes` or `frontend/src/lib/components`). | `grep -rnE '#[0-9a-fA-F]{3}([0-9a-fA-F]{3})?\b' frontend/src/routes frontend/src/lib/components` returns only `#104` issue references and `{#each}`/`{#if}` Svelte template syntax, never a color literal. |
| AC-2 | Fraunces/DM Sans/IBM Plex Mono render on every screen, served from this app's own origin. | Manual: `npm run dev`, open any route, DevTools Network tab shows `/fonts/*.woff2` requests with no `fonts.googleapis.com`/`fonts.gstatic.com` request. |
| AC-3 | Buttons are pill-shaped; primary buttons keep ≥4.5:1 text contrast. | Manual + the contrast table in §3.1. |
| AC-4 | `/health` (the one screen the previous #104 slice missed) is on tokens, not hardcoded hex. | `grep -nE '#[0-9a-fA-F]{3}([0-9a-fA-F]{3})?\b' frontend/src/routes/health/+page.svelte` returns only the `#104` references in the style block's own comment. |
| AC-5 | `/privacy` still issues zero network requests besides this app's own JS/CSS/fonts (AC-7 of `docs/specs/issue-63-privacy-page.md` must still hold). | Manual: DevTools Network tab on a cold load of `/privacy`. |
| AC-6 | Existing frontend tests keep passing; no test asserts on removed literal colors. | `npm test` in `frontend/`. |
| AC-7 | `docs/decisions/0001-shared-app-shell-layout.md` gets a new amendment documenting the global base stylesheet and the token repoint. | This PR includes that amendment. |

## 5. Explicitly out of scope

Expanding the nav to expenses/budgets; auth-state-aware nav; replacing `/`
with a budgets/expenses dashboard; a `Card` component; chart components;
macro photography and line-illustration assets; responsive-layout
verification (#64) and the dedicated accessibility pass (#65) — this slice
should not regress either (contrast was checked token-by-token, see §3.1),
but their full checklists are owned elsewhere.
