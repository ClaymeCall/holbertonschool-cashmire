<script>
  // Home / dashboard screen — issue #104's central deliverable: replaces
  // the original health-check placeholder with the real summary from
  // docs/mvp-scope.md's central user journey, step 3 ("Visualisation de
  // l'impact sur les budgets") — each budget's consumption/status, plus
  // recent expenses.
  //
  // Logged-out visitors can't see personal budget/expense data (there is
  // no session to scope it to), so this renders a public landing view
  // instead and only fetches anything once `$currentUser` is set. The
  // health check this page used to do moved to `/health` back in #18 and
  // is still reachable from the footer — it isn't duplicated here.
  import { onMount } from "svelte";
  import { currentUser } from "$lib/stores/auth";
  import { listBudgets } from "$lib/api/budgets";
  import { listExpenses } from "$lib/api/expenses";
  import { listCategories } from "$lib/api/categories";
  import { formatAmount } from "$lib/money";
  import Button from "$lib/components/Button.svelte";
  import FormError from "$lib/components/FormError.svelte";
  import BudgetCard from "$lib/components/BudgetCard.svelte";

  const RECENT_EXPENSE_COUNT = 5;

  /** @typedef {"loading" | "ready" | "error"} ViewState */

  /** @type {ViewState} */
  let state = $state("loading");
  /** @type {import("$lib/api/budgets").Budget[]} */
  let budgets = $state([]);
  /** @type {import("$lib/api/expenses").Expense[]} */
  let recentExpenses = $state([]);
  /** @type {Map<number, string>} */
  let categoryNames = $state(new Map());
  /** @type {string | null} */
  let errorMessage = $state(null);

  async function load() {
    state = "loading";
    errorMessage = null;
    try {
      const [categories, budgetList, expenseList] = await Promise.all([
        listCategories(),
        listBudgets(),
        listExpenses(),
      ]);
      categoryNames = new Map(categories.map((c) => [c.id, c.name]));
      budgets = budgetList;
      recentExpenses = expenseList.slice(0, RECENT_EXPENSE_COUNT);
      state = "ready";
    } catch (err) {
      errorMessage = "Couldn't load your dashboard. Try again in a moment.";
      state = "error";
      console.error("Failed to load dashboard:", err);
    }
  }

  // Only fetches once there's a session to scope the data to — rendering
  // this page while logged out (the default) issues no request, same as
  // the shared layout (layout.test.js's T-4b).
  onMount(() => {
    if ($currentUser) load();
  });
</script>

<svelte:head>
  <title>Cashmire</title>
  <meta
    name="description"
    content="Track your expenses and budgets with Cashmire."
  />
</svelte:head>

<main>
  {#if !$currentUser}
    <h1>Cashmire</h1>
    <p>
      Track your expenses, set monthly budgets by category, and see at a
      glance how close you are to each limit.
    </p>
    <p>
      <a class="button-link" href="/register">Create an account</a>
      <a href="/login">Log in</a>
    </p>
  {:else}
    <h1>Dashboard</h1>

    {#if state === "loading"}
      <p role="status">Loading your dashboard…</p>
    {:else if state === "error"}
      <FormError messages={errorMessage ? [errorMessage] : []} />
      <Button type="button" onclick={load}>Retry</Button>
    {:else}
      <section aria-labelledby="budgets-heading">
        <div class="section-header">
          <h2 id="budgets-heading">Your budgets</h2>
          <a href="/budgets">View all</a>
        </div>
        {#if budgets.length === 0}
          <p>
            No budgets yet. <a href="/budgets/new">Set a monthly limit for a category</a>
            to start tracking it here.
          </p>
        {:else}
          <ul class="budget-list">
            {#each budgets as budget (budget.id)}
              <BudgetCard
                {budget}
                categoryName={categoryNames.get(budget.category_id) ?? "Unknown category"}
              />
            {/each}
          </ul>
        {/if}
      </section>

      <section aria-labelledby="expenses-heading">
        <div class="section-header">
          <h2 id="expenses-heading">Recent expenses</h2>
          <a href="/expenses">View all</a>
        </div>
        {#if recentExpenses.length === 0}
          <p>No expenses yet. <a href="/expenses/new">Add your first one</a>.</p>
        {:else}
          <ul class="expense-list">
            {#each recentExpenses as expense (expense.id)}
              <li>
                <span class="amount">{formatAmount(expense.amount)}</span>
                <span class="category">
                  {categoryNames.get(expense.category_id) ?? "Unknown category"}
                </span>
                <span class="date">{expense.date}</span>
              </li>
            {/each}
          </ul>
        {/if}
      </section>
    {/if}
  {/if}
</main>

<style>
  main {
    max-width: 60ch;
    margin: 0 auto;
    padding: var(--space-2xl) var(--space-xl) var(--space-3xl);
    line-height: 1.5;
  }

  section {
    margin-top: var(--space-2xl);
  }

  .section-header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: var(--space-lg);
    margin-bottom: var(--space-md);
  }

  .section-header h2 {
    margin: 0;
  }

  .budget-list,
  .expense-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-md);
  }

  .expense-list li {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-lg);
    align-items: baseline;
    border: 1px solid var(--color-border-subtle);
    border-radius: var(--radius-sm);
    padding: var(--space-md) var(--space-lg);
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

  .button-link {
    display: inline-block;
    font-size: var(--font-size-base);
    padding: var(--space-sm) var(--space-lg);
    border-radius: var(--radius-sm);
    border: 1px solid var(--color-primary);
    background: var(--color-primary);
    color: #fff;
    text-decoration: none;
    margin-right: var(--space-lg);
  }

  .button-link:focus-visible {
    outline: var(--focus-ring-width) solid var(--focus-ring-color);
    outline-offset: 2px;
  }

  a {
    color: var(--color-primary);
  }

  a:focus-visible {
    outline: var(--focus-ring-width) solid var(--focus-ring-color);
    outline-offset: 2px;
  }
</style>
