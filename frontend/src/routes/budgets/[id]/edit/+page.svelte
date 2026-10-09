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
  <title>Modifier le budget · Cashmire</title>
  <meta name="description" content="Ajustez un budget mensuel existant." />
</svelte:head>

<main>
  <h1>Modifier le budget</h1>

  {#if state === "loading"}
    <p role="status">Chargement…</p>
  {:else if state === "not-found"}
    <p>Ce budget est introuvable.</p>
  {:else if state === "error"}
    <p role="alert">Impossible de charger ce budget. Réessayez dans un instant.</p>
  {:else}
    <BudgetForm
      mode="edit"
      {categories}
      initialCategoryId={String(budget.category_id)}
      initialMonth={periodToMonth(budget.period_start)}
      initialAmount={budget.amount}
      initialAlertThreshold={budget.alert_threshold}
      submitLabel="Enregistrer les modifications"
      onsubmit={handleUpdate}
    />
  {/if}

  <p><a href="/budgets">Retour aux budgets</a></p>
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
