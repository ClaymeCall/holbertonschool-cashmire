<script>
  // Reusable expense list — extracted from routes/expenses/+page.svelte
  // (issue #104 componentization follow-up) so it can be dropped anywhere
  // (the /expenses route, a home-page preview, …) without dragging along
  // that route's own page chrome (the <h1>, the "Add expense" link). The
  // route page still owns those; this component owns only the
  // loading/error/empty/list states.
  //
  // Lists the current user's expenses against the real `/api/expenses/` and
  // `/api/categories/` routes. No mock layer: built against the documented
  // contract and degrades to the error state if the session isn't
  // authenticated yet.
  //
  // Deleting an expense is issue #42's scope (confirmation flow), not this
  // one — only "Edit" is offered here.
  import { onMount } from "svelte";
  import { Calendar, Pencil, RefreshCw } from "@lucide/svelte";
  import { listExpenses } from "$lib/api/expenses";
  import { listCategories } from "$lib/api/categories";
  import { formatAmount } from "$lib/money";
  import Button from "$lib/components/Button.svelte";
  import FormError from "$lib/components/FormError.svelte";

  /**
   * @typedef {Object} Props
   * @property {number} [limit] - Cap the number of expenses rendered (the
   *   API's own order is kept, just truncated) — for a compact preview,
   *   e.g. on the home page. Omit to show every expense.
   */
  /** @type {Props} */
  let { limit } = $props();

  /** @typedef {"loading" | "ready" | "error"} ViewState */

  /** @type {ViewState} */
  let state = $state("loading");
  /** @type {import("$lib/api/expenses").Expense[]} */
  let expenses = $state([]);
  /** @type {Map<number, string>} */
  let categoryNames = $state(new Map());
  /** @type {string | null} */
  let errorMessage = $state(null);

  const visibleExpenses = $derived(
    typeof limit === "number" ? expenses.slice(0, limit) : expenses,
  );

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
      errorMessage = "Impossible de charger vos dépenses. Réessayez dans un instant.";
      state = "error";
      console.error("Failed to load expenses:", err);
    }
  }

  onMount(load);
</script>

{#if state === "loading"}
  <p role="status">Chargement de vos dépenses…</p>
{:else if state === "error"}
  <FormError messages={errorMessage ? [errorMessage] : []} />
  <Button type="button" onclick={load}><RefreshCw size={16} /> Réessayer</Button>
{:else if visibleExpenses.length === 0}
  <p>Aucune dépense pour l'instant. <a href="/expenses/new">Ajoutez la première</a>.</p>
{:else}
  <ul class="expense-list">
    {#each visibleExpenses as expense (expense.id)}
      <li>
        <div class="expense-main">
          <span class="amount">{formatAmount(expense.amount)}</span>
          <span class="category">
            {categoryNames.get(expense.category_id) ?? "Catégorie inconnue"}
          </span>
          <span class="date"><Calendar size={14} /> {expense.date}</span>
        </div>
        {#if expense.description}
          <p class="description">{expense.description}</p>
        {/if}
        <a href={`/expenses/${expense.id}/edit`}><Pencil size={14} /> Modifier</a>
      </li>
    {/each}
  </ul>
{/if}

<style>
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
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    color: var(--color-muted-text);
    margin-left: auto;
  }

  .description {
    margin: var(--space-xs) 0 0;
  }

  a {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    color: var(--color-primary);
  }

  a:focus-visible {
    outline: var(--focus-ring-width) solid var(--focus-ring-color);
    outline-offset: 2px;
  }
</style>
