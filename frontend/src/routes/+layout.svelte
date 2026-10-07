<script>
  // Minimal shared app shell — see docs/decisions/0001-shared-app-shell-layout.md
  // and its amendment for issue #15. Renders a header with site-wide
  // navigation, then page content, then a footer with the site-wide link to
  // /privacy required by issue #63 (AC-5). No global stylesheet, no theme
  // switcher — styling stays component-scoped (decision 0001 point 6).
  // `$app/state`'s `page.url` (the current, non-deprecated API for reading
  // page state) crashes at import time under this project's installed
  // @sveltejs/kit (2.70.3) + vitest/jsdom setup with
  // `TypeError: notifiable_store is not a function` — reproduced by a
  // bare `import { page } from "$app/state"` with no other code, so it is
  // not caused by anything in this component. Using it here would break
  // `privacy/page.test.js` (AC-6), which this issue must not touch. Falling
  // back to the deprecated `$app/stores`, which does not exhibit this
  // crash and is still fully supported by the installed version. Flagged
  // as a deviation in the PR description — revisit if a future Kit/Vite
  // upgrade resolves the underlying incompatibility.
  //
  // `$page` is read with optional chaining below because this store's
  // value is `{}` (no `url` yet) until SvelteKit's client router has
  // actually started a navigation — which is not the case when this
  // component is rendered standalone in a test harness, as
  // privacy/page.test.js does without mocking `$app/stores` at all.
  import { page } from "$app/stores";
  import "$lib/styles/tokens.css";

  let { children } = $props();

  // Exactly the routes that exist today — no placeholder links to unbuilt
  // pages (see docs/specs/issue-15-svelte-skeleton.md §4.2.1). Login/Register
  // added for #28/#29.
  const navLinks = [
    { href: "/", label: "Home" },
    { href: "/login", label: "Log in" },
    { href: "/register", label: "Register" },
    { href: "/privacy", label: "Privacy" },
  ];
</script>

<header>
  <a class="brand" href="/">Cashmire</a>
  <nav aria-label="Main">
    <ul>
      {#each navLinks as link (link.href)}
        <li>
          <a
            href={link.href}
            aria-current={$page?.url?.pathname === link.href ? "page" : undefined}
          >
            {link.label}
          </a>
        </li>
      {/each}
    </ul>
  </nav>
</header>

{#if children}
  {@render children()}
{/if}

<footer>
  <a href="/privacy">Privacy &amp; legal</a>
  <a href="/health">API health</a>
</footer>

<style>
  header {
    padding: var(--space-lg) var(--space-xl);
    border-bottom: 1px solid var(--color-border-subtle);
  }

  .brand {
    display: inline-block;
    margin-bottom: var(--space-sm);
    font-weight: 700;
  }

  nav ul {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-lg);
    margin: 0;
    padding: 0;
    list-style: none;
  }

  header a {
    color: var(--color-primary);
  }

  header a:focus-visible {
    outline: var(--focus-ring-width) solid var(--focus-ring-color);
    outline-offset: 2px;
  }

  nav a[aria-current="page"] {
    font-weight: 700;
    text-decoration: underline;
  }

  footer {
    padding: var(--space-lg) var(--space-xl);
    border-top: 1px solid var(--color-border-subtle);
    font-size: var(--font-size-sm);
  }

  footer a {
    color: var(--color-primary);
  }

  footer a:focus-visible {
    outline: var(--focus-ring-width) solid var(--focus-ring-color);
    outline-offset: 2px;
  }
</style>
