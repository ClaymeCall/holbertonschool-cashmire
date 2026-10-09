<script>
  // Create-budget screen — issue #53. Thin wrapper around the shared
  // `BudgetForm`: loads categories, translates the form's month/year value
  // into the `period_start`/`period_end` pair the API stores, and
  // navigates back to the dashboard on success.
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { createBudget, monthToPeriod } from "$lib/api/budgets";
  import { listCategories } from "$lib/api/categories";
  import BudgetForm from "$lib/components/BudgetForm.svelte";

  /** @typedef {"loading" | "idle" | "error"} ViewState */

  /** @type {ViewState} */
  let state = $state("loading");
  /** @type {Array<{ id: number, name: string }>} */
  let categories = $state([]);

  onMount(async () => {
    try {
      categories = await listCategories();
      state = "idle";
    } catch (err) {
      state = "error";
      console.error("Failed to load categories:", err);
    }
  });

  /**
   * @param {{ category_id: number, month: string, amount: string, alert_threshold: string }} values
   */
  async function handleCreate(values) {
    const { period_start, period_end } = monthToPeriod(values.month);
    await createBudget({
      category_id: values.category_id,
      amount: values.amount,
      period_start,
      period_end,
      alert_threshold: values.alert_threshold,
    });
    await goto("/budgets");
  }
</script>

<svelte:head>
  <title>Ajouter un budget · Cashmire</title>
  <meta name="description" content="Définissez une limite de dépenses mensuelle pour une catégorie." />
</svelte:head>

<main>
  <h1>Ajouter un budget</h1>

  {#if state === "loading"}
    <p role="status">Chargement…</p>
  {:else if state === "error"}
    <p role="alert">Impossible de charger les catégories. Réessayez dans un instant.</p>
  {:else}
    <BudgetForm
      mode="create"
      {categories}
      submitLabel="Ajouter un budget"
      onsubmit={handleCreate}
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
