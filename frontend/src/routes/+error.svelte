<script>
  // Error boundary (404s and other uncaught route errors). Previously the
  // bare default SvelteKit error view; this gives it the Cashmire voice and
  // the macro-photo "empty state" treatment the design brief calls for
  // (docs/specs/issue-104-cashmire-design-system.md §2.4) — this is the one
  // screen in the app that is genuinely an empty state today.
  //
  // Uses `$app/stores` rather than `$app/state`, same reasoning as
  // +layout.svelte: the latter crashes at import time under this project's
  // installed SvelteKit + vitest/jsdom setup.
  import { page } from "$app/stores";
  import emptyStateImage from "$lib/images/cashmere-empty-state.webp";
</script>

<svelte:head>
  <title>{$page?.status ?? 404} · Cashmire</title>
</svelte:head>

<main>
  <div class="text">
    <p class="status">{$page?.status ?? 404}</p>
    <h1>Page introuvable</h1>
    <p>
      {$page?.error?.message ?? "Cette page n'existe pas."}
    </p>
    <p><a href="/">Retour à la page d'accueil de Cashmire</a></p>
  </div>
  <img
    src={emptyStateImage}
    alt=""
    aria-hidden="true"
    class="illustration"
  />
</main>

<style>
  main {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--space-3xl);
    max-width: 70ch;
    margin: 0 auto;
    padding: var(--space-3xl) var(--space-xl);
  }

  .text {
    flex: 1 1 24ch;
    line-height: var(--line-height-body);
  }

  .status {
    font-family: var(--font-mono);
    letter-spacing: var(--tracking-mono-label);
    text-transform: uppercase;
    color: var(--color-text-muted);
    margin: 0 0 var(--space-sm);
  }

  h1 {
    font-style: italic;
    font-weight: 300;
    margin: 0 0 var(--space-md);
  }

  .illustration {
    flex: 1 1 20ch;
    max-width: 22rem;
    width: 100%;
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-soft);
  }

  a:focus-visible {
    outline: var(--focus-ring-width) solid var(--focus-ring-color);
    outline-offset: 2px;
  }

  a {
    color: var(--color-primary);
  }
</style>
