<script>
  // Landing-page dashboard — centralized fetch for the 3 chart components
  // below, mirroring BudgetsList/ExpensesList's loading/error state machine.
  //
  // Deliberately NOT self-fetching per chart like BudgetsList/ExpensesList
  // do: those are also mounted standalone on their own routes, so
  // self-containment is right there. These 3 charts are only ever used
  // together, on this one page, and overlap heavily in data needs (all
  // three need categories, two need the full expense list) — self-fetching
  // each would triple the already-unpaginated listExpenses()/listBudgets()
  // calls on every home-page load.
  import { onMount } from "svelte";
  import { RefreshCw } from "@lucide/svelte";
  import "$lib/styles/charts.css";
  import { listBudgets } from "$lib/api/budgets";
  import { listExpenses } from "$lib/api/expenses";
  import { listCategories } from "$lib/api/categories";
  import {
    budgetVsSpentRows,
    spendingByCategory,
    dailyTotals,
    currentMonthWindow,
    last30DaysWindow,
  } from "$lib/dashboard";
  import Button from "$lib/components/Button.svelte";
  import FormError from "$lib/components/FormError.svelte";
  import BudgetVsSpentChart from "$lib/components/BudgetVsSpentChart.svelte";
  import SpendingByCategoryChart from "$lib/components/SpendingByCategoryChart.svelte";
  import SpendingTrendChart from "$lib/components/SpendingTrendChart.svelte";

  /** @typedef {"loading" | "ready" | "error"} ViewState */

  /** @type {ViewState} */
  let state = $state("loading");
  /** @type {import("$lib/api/budgets").Budget[]} */
  let budgets = $state([]);
  /** @type {import("$lib/api/expenses").Expense[]} */
  let expenses = $state([]);
  /** @type {Map<number, string>} */
  let categoryNames = $state(new Map());
  /** @type {string | null} */
  let errorMessage = $state(null);

  const budgetRows = $derived(budgetVsSpentRows(budgets, categoryNames));
  const categoryTotals = $derived(
    spendingByCategory(expenses, categoryNames, currentMonthWindow()),
  );
  const daily = $derived(dailyTotals(expenses, last30DaysWindow()));

  async function load() {
    state = "loading";
    errorMessage = null;
    try {
      const [categories, expenseList, budgetList] = await Promise.all([
        listCategories(),
        listExpenses(),
        listBudgets(),
      ]);
      categoryNames = new Map(categories.map((c) => [c.id, c.name]));
      expenses = expenseList;
      budgets = budgetList;
      state = "ready";
    } catch (err) {
      errorMessage = "Impossible de charger votre tableau de bord. Réessayez dans un instant.";
      state = "error";
      console.error("Failed to load dashboard data:", err);
    }
  }

  onMount(load);
</script>

{#if state === "loading"}
  <p role="status">Chargement de votre tableau de bord…</p>
{:else if state === "error"}
  <FormError messages={errorMessage ? [errorMessage] : []} />
  <Button type="button" onclick={load}><RefreshCw size={16} /> Réessayer</Button>
{:else}
  <div class="dashboard-charts">
    <BudgetVsSpentChart rows={budgetRows} />
    <SpendingByCategoryChart totals={categoryTotals} />
    <SpendingTrendChart {daily} />
  </div>
{/if}

<style>
  .dashboard-charts {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: var(--space-2xl);
  }
</style>
