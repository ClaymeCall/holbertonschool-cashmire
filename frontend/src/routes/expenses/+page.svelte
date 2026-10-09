<script>
  // Expense list screen — issue #40. The list itself is
  // `$lib/components/ExpensesList.svelte` (issue #104 componentization
  // follow-up); this route just supplies the page chrome (title, heading,
  // "Add expense" link) around it.
  import { Plus } from "@lucide/svelte";
  import ExpensesList from "$lib/components/ExpensesList.svelte";
</script>

<svelte:head>
  <title>Dépenses · Cashmire</title>
  <meta name="description" content="Vos dépenses enregistrées." />
</svelte:head>

<main>
  <div class="header-row">
    <h1>Dépenses</h1>
    <a class="button-link" href="/expenses/new"><Plus size={16} /> Ajouter une dépense</a>
  </div>

  <ExpensesList />
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
