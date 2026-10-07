<script>
  // Site-wide nav — extracted from the shared app shell (issue #104
  // componentization follow-up) so it's a self-contained, reusable unit:
  // no props required, since auth state is read directly from the shared
  // `$lib/auth.svelte.js` singleton rather than passed down.
  //
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
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { page } from "$app/stores";
  import {
    House,
    Receipt,
    Wallet,
    Shield,
    LogIn,
    UserPlus,
    LogOut,
    Menu,
    X,
  } from "@lucide/svelte";
  import textureTile from "$lib/images/cashmere-texture-tile.webp";
  import { authState, refreshCurrentUser, setCurrentUser } from "$lib/auth.svelte.js";
  import { apiFetch } from "$lib/api";

  // Exactly the routes that exist today — no placeholder links to unbuilt
  // pages (see docs/specs/issue-15-svelte-skeleton.md §4.2.1). Expenses and
  // Budgets are `protected: true`: always shown, regardless of auth state
  // (issue #104 navbar follow-up), but intercepted on click for an
  // anonymous visitor — see `handleNavClick` below — rather than letting
  // them land on a page that can only show its own generic 401 error.
  // Login/Register only make sense to show when nobody is logged in —
  // otherwise they're replaced by the "Log out" action further down.
  //
  // Icons are decorative, paired with the label text rather than replacing
  // it (issue #104 icon pass) — `aria-hidden` is applied automatically by
  // @lucide/svelte whenever an icon has no accessible-name prop of its own
  // (see its Icon.svelte), so each link's accessible name still comes from
  // its visible text alone.
  const navLinks = $derived([
    { href: "/", label: "Home", icon: House },
    { href: "/expenses", label: "Expenses", icon: Receipt, protected: true },
    { href: "/budgets", label: "Budgets", icon: Wallet, protected: true },
    ...(authState.status === "authenticated"
      ? []
      : [
          { href: "/login", label: "Log in", icon: LogIn },
          { href: "/register", label: "Register", icon: UserPlus },
        ]),
    { href: "/privacy", label: "Privacy", icon: Shield },
  ]);

  /**
   * @param {MouseEvent} event
   * @param {{ href: string, protected?: boolean }} link
   */
  function handleNavClick(event, link) {
    menuOpen = false;
    // `authState.status` is "loading" for the brief window before the
    // mount-time /api/auth/me/ check resolves (see `refreshCurrentUser`) —
    // treated the same as "anonymous" here, consistently with how the nav
    // itself already defaults to the anonymous link set during that window.
    if (link.protected && authState.status !== "authenticated") {
      event.preventDefault();
      goto("/login");
    }
  }

  // Resolved once per full page load — this component doesn't remount on
  // client-side navigation (it lives in the root layout), so login/register
  // set the state directly on success (see their own handleSubmit) rather
  // than relying on this running again.
  onMount(() => {
    refreshCurrentUser();
  });

  let loggingOut = $state(false);

  async function handleLogout() {
    if (loggingOut) return;
    loggingOut = true;
    try {
      await apiFetch("/api/auth/logout/", {
        method: "POST",
        credentials: "include",
      });
    } catch (err) {
      // Logout is idempotent from the user's point of view: even if the
      // request failed (e.g. the session had already expired server-side),
      // there is nothing actionable to show them — clear local state and
      // send them home regardless.
      console.error("Logout failed:", err);
    }
    setCurrentUser(null);
    loggingOut = false;
    await goto("/");
  }

  // Mobile nav collapse (issue #104 navbar follow-up). Closed by default so
  // the links don't flash open on small screens before CSS hides them.
  let menuOpen = $state(false);
</script>

<header style="--texture-photo: url({textureTile})">
  <div class="header-row">
    <a class="brand" href="/">Cashmire</a>
    <button
      type="button"
      class="menu-toggle"
      aria-expanded={menuOpen}
      aria-controls="main-nav"
      aria-label={menuOpen ? "Close menu" : "Open menu"}
      onclick={() => (menuOpen = !menuOpen)}
    >
      <!-- Icon-only: the button's own aria-label above is the accessible
           name, so the icon swap (Menu/X) is purely visual. -->
      {#if menuOpen}
        <X size={22} />
      {:else}
        <Menu size={22} />
      {/if}
    </button>
    <nav aria-label="Main" id="main-nav" class:open={menuOpen}>
      <ul>
        {#each navLinks as link (link.href)}
          <li>
            <a
              href={link.href}
              aria-current={$page?.url?.pathname === link.href ? "page" : undefined}
              onclick={(event) => handleNavClick(event, link)}
            >
              <link.icon size={16} />
              {link.label}
            </a>
          </li>
        {/each}
        {#if authState.status === "authenticated"}
          <li>
            <button
              type="button"
              class="nav-action"
              disabled={loggingOut}
              onclick={() => {
                menuOpen = false;
                handleLogout();
              }}
            >
              <LogOut size={16} />
              {loggingOut ? "Logging out…" : "Log out"}
            </button>
          </li>
        {/if}
      </ul>
    </nav>
  </div>
</header>

<style>
  header {
    padding: var(--space-lg) var(--space-xl);
    border-bottom: 1px dashed var(--color-border-subtle);
    background-color: var(--color-surface);
    /* Real macro-knit photo, tinted near-opaque so it reads as the brief's
       faint surface texture rather than a visible photograph. */
    background-image: linear-gradient(
        var(--texture-overlay-tint),
        var(--texture-overlay-tint)
      ),
      var(--texture-photo);
    background-size: auto, 150px 150px;
  }

  .header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-lg);
  }

  .brand {
    display: inline-block;
    font-family: var(--font-heading);
    font-size: 1.3rem;
    font-weight: 600;
    color: var(--color-heading);
    transition: color var(--motion-duration) var(--motion-ease);
  }

  .brand:hover {
    color: var(--color-camel-deep);
  }

  .menu-toggle {
    display: none;
    align-items: center;
    justify-content: center;
    width: 2.25rem;
    height: 2.25rem;
    padding: 5px;
    border: none;
    border-radius: var(--radius-sm);
    background: transparent;
    color: var(--color-primary);
    cursor: pointer;
    transition: background-color var(--motion-duration) var(--motion-ease);
  }

  .menu-toggle:hover {
    background-color: var(--color-oatmeal);
  }

  nav ul {
    display: flex;
    flex-wrap: wrap;
    /* Cross-axis alignment: without this, each <li> stretches to the row's
       full height (flex's default `align-items: stretch`) and the <a>/
       <button> pills inside them don't vertically center within that
       stretched box, so they sit at inconsistent heights relative to
       each other. */
    align-items: center;
    gap: var(--space-lg);
    margin: 0;
    padding: 0;
    list-style: none;
  }

  header a {
    color: var(--color-primary);
  }

  nav a,
  nav .nav-action {
    /* `<a>` defaults to `display: inline`, `<button>` to `inline-block` —
       with identical padding, the inline <a> still rendered ~4px shorter
       than the button (inline elements' vertical padding doesn't expand
       their box the same way), making the pills visibly different sizes.
       Forcing both to the same display mode (now `inline-flex`, to lay
       out each link/button's icon next to its label) fixes that. */
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: var(--space-xs) var(--space-sm);
    border-radius: var(--radius-full);
    text-decoration: none;
    transition: background-color var(--motion-duration) var(--motion-ease),
      color var(--motion-duration) var(--motion-ease);
  }

  nav :global(svg) {
    flex-shrink: 0;
  }

  nav a:hover,
  nav .nav-action:hover:not(:disabled) {
    background-color: var(--color-oatmeal);
  }

  nav a[aria-current="page"] {
    font-weight: 700;
    background-color: var(--color-camel);
    color: var(--color-ivory);
  }

  /* Matches `nav a`'s look exactly, but it's a <button> (issue #104
     follow-up) — logout is a state-changing POST, not a navigation, so it
     must not be a link. */
  nav .nav-action {
    font: inherit;
    color: var(--color-primary);
    background: transparent;
    border: none;
    cursor: pointer;
  }

  nav .nav-action:disabled {
    cursor: default;
    opacity: 0.65;
  }

  @media (max-width: 640px) {
    .header-row {
      flex-wrap: wrap;
    }

    .menu-toggle {
      display: flex;
    }

    nav {
      order: 3;
      width: 100%;
    }

    nav ul {
      display: none;
      flex-direction: column;
      align-items: flex-start;
      gap: var(--space-xs);
      margin-top: var(--space-md);
    }

    nav.open ul {
      display: flex;
    }
  }
</style>
