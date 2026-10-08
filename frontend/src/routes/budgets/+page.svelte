<script>
  // Budget dashboard screen — issue #52. The list itself is
  // `$lib/components/BudgetsList.svelte` (issue #104 componentization
  // follow-up); this route just supplies the page chrome (title, heading,
  // "Add budget" link) around it.
  import { Plus } from "@lucide/svelte";
  import BudgetsList from "$lib/components/BudgetsList.svelte";
</script>

<svelte:head>
  <title>Budgets · Cashmire</title>
  <meta name="description" content="Track how your spending compares to the budgets you've set." />
</svelte:head>

<main>
  <div class="header-row">
    <h1>Budgets</h1>
    <a class="button-link" href="/budgets/new"><Plus size={16} /> Add budget</a>
  </div>

  <BudgetsList />
</main>

<style>
  main {
    max-width: 60ch;
    margin: 0 auto;
    padding: var(--space-2xl) var(--space-xl) var(--space-3xl);
    line-height: 1.5;
  }

  .header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-lg);
    margin-bottom: var(--space-xl);
  }

  .button-link {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: var(--font-size-base);
    padding: var(--space-sm) var(--space-lg);
    border-radius: var(--radius-sm);
    border: 1px solid var(--color-primary);
    background: var(--color-primary);
    color: #fff;
    text-decoration: none;
  }

  .button-link:focus-visible {
    outline: var(--focus-ring-width) solid var(--focus-ring-color);
    outline-offset: 2px;
  }
</style>
