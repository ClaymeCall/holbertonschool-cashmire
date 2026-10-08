<script>
  // Landing page. For a logged-in visitor it also previews their most
  // recent expenses and budgets (issue #104 componentization follow-up) —
  // proof that ExpensesList/BudgetsList (lib/components/) are genuinely
  // reusable outside their own /expenses and /budgets routes, not just
  // split out for file-size reasons. Each preview is capped at 3 items and
  // links through to its full route rather than paginating here.
  import { onMount } from "svelte";
  import { ArrowRight } from "@lucide/svelte";
  import { apiFetch } from "$lib/api";
  import heroImage from "$lib/images/cashmere-hero.webp";
  import { authState } from "$lib/auth.svelte.js";
  import ExpensesList from "$lib/components/ExpensesList.svelte";
  import BudgetsList from "$lib/components/BudgetsList.svelte";
  import DashboardCharts from "$lib/components/DashboardCharts.svelte";

  const PREVIEW_LIMIT = 3;

  let status = "checking...";

  onMount(async () => {
    try {
      const data = await apiFetch("/api/health/");
      status = data.status;
    } catch (err) {
      status = "unreachable";
    }
  });
</script>

<section class="hero" style="--hero-image: url({heroImage})">
  <div class="hero-scrim">
    <h1>Cashmire</h1>
    <p class="tagline">Quiet luxury for your everyday budget.</p>
  </div>
</section>

<main>
  {#if authState.status === "authenticated"}
    <section class="dashboard" aria-labelledby="dashboard-heading">
      <h2 id="dashboard-heading">Your spending at a glance</h2>
      <DashboardCharts />
    </section>
  {/if}

  <div class="prose">
    <p>API status: <code>{status}</code></p>
  </div>

  {#if authState.status === "authenticated"}
    <section class="preview" aria-labelledby="expenses-preview-heading">
      <div class="preview-header">
        <h2 id="expenses-preview-heading">Recent expenses</h2>
        <a href="/expenses">View all <ArrowRight size={14} /></a>
      </div>
      <ExpensesList limit={PREVIEW_LIMIT} />
    </section>

    <section class="preview" aria-labelledby="budgets-preview-heading">
      <div class="preview-header">
        <h2 id="budgets-preview-heading">Your budgets</h2>
        <a href="/budgets">View all <ArrowRight size={14} /></a>
      </div>
      <BudgetsList limit={PREVIEW_LIMIT} />
    </section>
  {/if}
</main>

<style>
  .hero {
    background-image: linear-gradient(
        180deg,
        rgba(42, 23, 15, 0.45),
        rgba(42, 23, 15, 0.15)
      ),
      var(--hero-image);
    background-size: cover;
    background-position: center;
  }

  .hero-scrim {
    max-width: 60ch;
    margin: 0 auto;
    padding: var(--space-3xl) var(--space-xl);
  }

  h1 {
    font-size: 2.25rem;
    font-style: italic;
    font-weight: 300;
    color: var(--color-ivory);
  }

  .tagline {
    color: var(--color-ivory);
    font-size: 1.1rem;
  }

  main {
    /* Without an explicit `width`, `main` only shrink-to-fits its content
       instead of actually reaching `max-width` (`body`'s flex stretch
       doesn't take effect here — SvelteKit wraps `{@render children()}` in
       a `display: contents` node, which apparently breaks it for a subtree
       this deep). Plain flowing text happened to fill the available width
       anyway, so this went unnoticed — but it's fatal for the `auto-fit`
       grids below: an auto-fit grid can't compute how many columns fit
       without a definite container width, so it was silently collapsing
       to one column. */
    width: 100%;
    max-width: 1100px;
    margin: 0 auto;
    padding: var(--space-2xl) var(--space-xl) var(--space-3xl);
  }

  .prose {
    max-width: 60ch;
    margin-inline: auto;
  }

  .dashboard {
    margin-bottom: var(--space-2xl);
  }

  .dashboard h2 {
    font-family: var(--font-heading);
    font-size: 1.2rem;
    font-weight: 600;
    color: var(--color-heading);
    margin-bottom: var(--space-md);
  }

  .preview {
    margin-top: var(--space-2xl);
  }

  .preview-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-lg);
    margin-bottom: var(--space-md);
  }

  .preview-header h2 {
    font-family: var(--font-heading);
    font-size: 1.2rem;
    font-weight: 600;
    color: var(--color-heading);
  }

  .preview-header a {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    font-size: var(--font-size-sm);
    color: var(--color-primary);
  }

  /* ExpensesList/BudgetsList (lib/components/) default to a single stacked
     column — the right call on their own routes, where the list is the
     whole page and can run to any length. Here it's always exactly
     PREVIEW_LIMIT items in the wide `main` column, so reflow them into a
     card grid instead of leaving the extra width empty; collapses to one
     column with no media query, same `auto-fit` pattern as `.dashboard`'s
     chart grid. `ul.` (not just `.`) deliberately outranks the component's
     own same-specificity `.expense-list`/`.budget-list` rule regardless of
     which stylesheet Vite happens to inject first. */
  :global(.preview ul.expense-list),
  :global(.preview ul.budget-list) {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  }
</style>
