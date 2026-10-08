<script>
  // Edit-budget screen — issue #53. Same "no single-resource GET, refetch
  // the unpaginated list" pattern as the expense edit screen (#41) — see
  // its +page.svelte for why. Only `amount` and `alert_threshold` are sent
  // back (`docs/api-design.md` §4.4): category and month are read-only in
  // `BudgetForm`'s edit mode.
  import { onMount } from "svelte";
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { listBudgets, updateBudget, periodToMonth } from "$lib/api/budgets";
  import { listCategories } from "$lib/api/categories";
  import BudgetForm from "$lib/components/BudgetForm.svelte";

  /** @typedef {"loading" | "idle" | "error" | "not-found"} ViewState */

  const budgetId = Number($page.params.id);

  /** @type {ViewState} */
  let state = $state("loading");
  /** @type {Array<{ id: number, name: string }>} */
  let categories = $state([]);
  /** @type {import("$lib/api/budgets").Budget | null} */
  let budget = $state(null);

  onMount(async () => {
    try {
      const [categoryList, budgets] = await Promise.all([
        listCategories(),
        listBudgets(),
      ]);
      categories = categoryList;

      const match = budgets.find((b) => b.id === budgetId);
      if (!match) {
        state = "not-found";
        return;
      }
      budget = match;
      state = "idle";
    } catch (err) {
      state = "error";
      console.error("Failed to load budget:", err);
    }
  });

  /**
   * @param {{ amount: string, alert_threshold: string }} values
   */
  async function handleUpdate(values) {
    await updateBudget(budgetId, {
      amount: values.amount,
      alert_threshold: values.alert_threshold,
    });
    await goto("/budgets");
  }
</script>

<svelte:head>
  <title>Edit budget · Cashmire</title>
  <meta name="description" content="Adjust an existing monthly budget." />
</svelte:head>

<main>
  <h1>Edit budget</h1>

  {#if state === "loading"}
    <p role="status">Loading…</p>
  {:else if state === "not-found"}
    <p>That budget couldn't be found.</p>
  {:else if state === "error"}
    <p role="alert">Couldn't load this budget. Try again in a moment.</p>
  {:else}
    <BudgetForm
      mode="edit"
      {categories}
      initialCategoryId={String(budget.category_id)}
      initialMonth={periodToMonth(budget.period_start)}
      initialAmount={budget.amount}
      initialAlertThreshold={budget.alert_threshold}
      submitLabel="Save changes"
      onsubmit={handleUpdate}
    />
  {/if}

  <p><a href="/budgets">Back to budgets</a></p>
</main>

<style>
  main {
    max-width: 40ch;
    margin: 0 auto;
    padding: var(--space-2xl) var(--space-xl) var(--space-3xl);
    line-height: 1.5;
  }

  a {
    color: var(--color-primary);
  }

  a:focus-visible {
    outline: var(--focus-ring-width) solid var(--focus-ring-color);
    outline-offset: 2px;
  }
</style>
