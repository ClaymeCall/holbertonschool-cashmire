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
  import { goto } from "$app/navigation";
  import { currentUser, logout } from "$lib/stores/auth";
  import "$lib/styles/tokens.css";

  let { children } = $props();

  // Issue #104's amendment to decision 0001: the nav now reflects auth
  // state rather than listing every route unconditionally. `$currentUser`
  // is only ever set by login/register's own success handlers (see
  // lib/stores/auth.js) — reading it here is a plain reactive read, not a
  // fetch, so this still satisfies layout.test.js's T-4b ("rendering the
  // layout issues zero fetch calls").
  const navLinks = $derived(
    $currentUser
      ? [
          { href: "/", label: "Dashboard" },
          { href: "/expenses", label: "Expenses" },
          { href: "/budgets", label: "Budgets" },
          { href: "/privacy", label: "Privacy" },
        ]
      : [
          { href: "/", label: "Home" },
          { href: "/login", label: "Log in" },
          { href: "/register", label: "Register" },
          { href: "/privacy", label: "Privacy" },
        ],
  );

  let loggingOut = $state(false);

  async function handleLogout() {
    if (loggingOut) return;
    loggingOut = true;
    try {
      await logout();
      await goto("/");
    } catch (err) {
      // Leaves the nav in its logged-in state (lib/stores/auth.js's
      // `logout` only clears the store on success) — the user can retry.
      console.error("Logout failed:", err);
    } finally {
      loggingOut = false;
    }
  }
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
      {#if $currentUser}
        <li>
          <button type="button" onclick={handleLogout} disabled={loggingOut}>
            {loggingOut ? "Logging out…" : "Log out"}
          </button>
        </li>
      {/if}
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

  nav button {
    font: inherit;
    color: var(--color-primary);
    background: none;
    border: none;
    padding: 0;
    cursor: pointer;
  }

  nav button:disabled {
    cursor: default;
    opacity: 0.65;
  }

  nav button:focus-visible {
    outline: var(--focus-ring-width) solid var(--focus-ring-color);
    outline-offset: 2px;
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
