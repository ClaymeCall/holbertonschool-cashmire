<script>
  // Expense list screen — issue #40.
  //
  // Lists the current user's expenses against the real `/api/expenses/` and
  // `/api/categories/` routes (both already merged — see
  // `backend/api/views.py`). No mock layer: like login/register before their
  // backend existed, this is built against the documented contract and
  // degrades to the error state if the session isn't authenticated yet.
  //
  // Deleting an expense is issue #42's scope (confirmation flow), not this
  // one — only "Edit" is offered here.
  import { onMount } from "svelte";
  import { listExpenses } from "$lib/api/expenses";
  import { listCategories } from "$lib/api/categories";
  import { formatAmount } from "$lib/money";
  import Button from "$lib/components/Button.svelte";
  import FormError from "$lib/components/FormError.svelte";

  // `<Button>` renders a <button>; a link that navigates should not be one
  // (a <button> nested in an <a>, or vice-versa, is invalid HTML and
  // double-announces to screen readers). `.button-link` below reuses
  // Button's own primary-variant styling for a plain <a>.

  /** @typedef {"loading" | "ready" | "error"} ViewState */

  /** @type {ViewState} */
  let state = $state("loading");
  /** @type {import("$lib/api/expenses").Expense[]} */
  let expenses = $state([]);
  /** @type {Map<number, string>} */
  let categoryNames = $state(new Map());
  /** @type {string | null} */
  let errorMessage = $state(null);

  async function load() {
    state = "loading";
    errorMessage = null;
    try {
      const [categories, expenseList] = await Promise.all([
        listCategories(),
        listExpenses(),
      ]);
      categoryNames = new Map(categories.map((c) => [c.id, c.name]));
      expenses = expenseList;
      state = "ready";
    } catch (err) {
      errorMessage = "Couldn't load your expenses. Try again in a moment.";
      state = "error";
      console.error("Failed to load expenses:", err);
    }
  }

  onMount(load);
</script>

<svelte:head>
  <title>Expenses · Cashmire</title>
  <meta name="description" content="Your recorded expenses." />
</svelte:head>

<main>
  <div class="header-row">
    <h1>Expenses</h1>
    <a class="button-link" href="/expenses/new">Add expense</a>
  </div>

  {#if state === "loading"}
    <p role="status">Loading your expenses…</p>
  {:else if state === "error"}
    <FormError messages={errorMessage ? [errorMessage] : []} />
    <Button type="button" onclick={load}>Retry</Button>
  {:else if expenses.length === 0}
    <p>No expenses yet. <a href="/expenses/new">Add your first one</a>.</p>
  {:else}
    <ul class="expense-list">
      {#each expenses as expense (expense.id)}
        <li>
          <div class="expense-main">
            <span class="amount">{formatAmount(expense.amount)}</span>
            <span class="category">
              {categoryNames.get(expense.category_id) ?? "Unknown category"}
            </span>
            <span class="date">{expense.date}</span>
          </div>
          {#if expense.description}
            <p class="description">{expense.description}</p>
          {/if}
          <a href={`/expenses/${expense.id}/edit`}>Edit</a>
        </li>
      {/each}
    </ul>
  {/if}
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
    display: inline-block;
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

  .expense-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-md);
  }

  .expense-list li {
    border: 1px solid var(--color-border-subtle);
    border-radius: var(--radius-sm);
    padding: var(--space-md) var(--space-lg);
  }

  .expense-main {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-lg);
    align-items: baseline;
  }

  .amount {
    font-weight: 700;
  }

  .category {
    color: var(--color-muted-text);
  }

  .date {
    color: var(--color-muted-text);
    margin-left: auto;
  }

  .description {
    margin: var(--space-xs) 0 0;
  }

  a {
    color: var(--color-primary);
  }

  a:focus-visible {
    outline: var(--focus-ring-width) solid var(--focus-ring-color);
    outline-offset: 2px;
  }
</style>
