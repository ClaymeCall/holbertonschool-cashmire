<script>
  // Budget dashboard screen — issue #52.
  //
  // `spent`/`remaining`/`status` are all computed server-side (per
  // `docs/decisions/budget-thresholds.md`) once #45-#50 ship; this screen
  // never recomputes `status` — it only maps the four documented values to
  // a color + label. The percentage-consumed figure shown in the progress
  // bar IS computed client-side with `money.js`'s `percentOf`, which exists
  // for exactly this (see its file-top comment) — that's display
  // arithmetic, not the ok/warning/full/exceeded decision itself.
  //
  // Not merged yet at the time this was written (#45, #115/#121-125): this
  // calls the real, documented `/api/budgets/` route and will show the
  // error state until it ships — same pattern as #40/#41 before #34-#39
  // landed.
  import { onMount } from "svelte";
  import { listBudgets } from "$lib/api/budgets";
  import { listCategories } from "$lib/api/categories";
  import { formatAmount, percentOf, compareDecimal } from "$lib/money";
  import Button from "$lib/components/Button.svelte";
  import FormError from "$lib/components/FormError.svelte";

  /** @typedef {"loading" | "ready" | "error"} ViewState */

  /** @type {ViewState} */
  let state = $state("loading");
  /** @type {import("$lib/api/budgets").Budget[]} */
  let budgets = $state([]);
  /** @type {Map<number, string>} */
  let categoryNames = $state(new Map());
  /** @type {string | null} */
  let errorMessage = $state(null);

  const STATUS_META = {
    ok: { label: "On track", className: "status-ok" },
    warning: { label: "Approaching limit", className: "status-warning" },
    full: { label: "Budget reached", className: "status-full" },
    exceeded: { label: "Over budget", className: "status-exceeded" },
  };

  /**
   * @param {import("$lib/api/budgets").Budget} budget
   */
  function statusMeta(budget) {
    return STATUS_META[budget.status] ?? { label: "Unknown", className: "status-unknown" };
  }

  /**
   * @param {import("$lib/api/budgets").Budget} budget
   * @returns {string} e.g. "47.0" — capped at 100 for the progress bar's
   *   width even when the budget is exceeded (the "Over budget" label,
   *   not the bar, is what communicates overspend).
   */
  function percentForBar(budget) {
    const percent = percentOf(budget.spent, budget.amount);
    return compareDecimal(percent, "100") > 0 ? "100" : percent;
  }

  async function load() {
    state = "loading";
    errorMessage = null;
    try {
      const [categories, budgetList] = await Promise.all([
        listCategories(),
        listBudgets(),
      ]);
      categoryNames = new Map(categories.map((c) => [c.id, c.name]));
      budgets = budgetList;
      state = "ready";
    } catch (err) {
      errorMessage = "Couldn't load your budgets. Try again in a moment.";
      state = "error";
      console.error("Failed to load budgets:", err);
    }
  }

  onMount(load);
</script>

<svelte:head>
  <title>Budgets · Cashmire</title>
  <meta name="description" content="Track how your spending compares to the budgets you've set." />
</svelte:head>

<main>
  <div class="header-row">
    <h1>Budgets</h1>
    <a class="button-link" href="/budgets/new">Add budget</a>
  </div>

  {#if state === "loading"}
    <p role="status">Loading your budgets…</p>
  {:else if state === "error"}
    <FormError messages={errorMessage ? [errorMessage] : []} />
    <Button type="button" onclick={load}>Retry</Button>
  {:else if budgets.length === 0}
    <p>
      No budgets yet. <a href="/budgets/new">Set a monthly limit for a category</a>
      to start tracking it here.
    </p>
  {:else}
    <ul class="budget-list">
      {#each budgets as budget (budget.id)}
        {@const meta = statusMeta(budget)}
        <li class={meta.className}>
          <div class="budget-header">
            <span class="category">
              {categoryNames.get(budget.category_id) ?? "Unknown category"}
            </span>
            <span class="status-label">{meta.label}</span>
          </div>
          <p class="amounts">
            {formatAmount(budget.spent)} spent of {formatAmount(budget.amount)}
            ({formatAmount(budget.remaining)} remaining)
          </p>
          <div
            class="progress-track"
            role="progressbar"
            aria-valuenow={percentForBar(budget)}
            aria-valuemin="0"
            aria-valuemax="100"
            aria-label={`${categoryNames.get(budget.category_id) ?? "Budget"} consumption`}
          >
            <div class="progress-fill" style={`width: ${percentForBar(budget)}%`}></div>
          </div>
          <a href={`/budgets/${budget.id}/edit`}>Edit</a>
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

  .budget-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-md);
  }

  .budget-list li {
    border: 1px solid var(--color-border-subtle);
    border-left-width: 4px;
    border-radius: var(--radius-sm);
    padding: var(--space-md) var(--space-lg);
  }

  .budget-header {
    display: flex;
    justify-content: space-between;
    gap: var(--space-lg);
    font-weight: 600;
  }

  .amounts {
    margin: var(--space-xs) 0 var(--space-sm);
  }

  .progress-track {
    height: 0.6rem;
    border-radius: var(--radius-sm);
    background: var(--color-border-subtle);
    overflow: hidden;
    margin-bottom: var(--space-sm);
  }

  .progress-fill {
    height: 100%;
    background: currentColor;
  }

  /* Color never carries the status alone — the text label next to it does
     the real work (docs/mvp-scope.md §3.7). These classes only tint the
     card's border/accent and the progress fill. */
  .status-ok {
    border-left-color: var(--color-success-border);
    color: var(--color-success-border);
  }

  .status-warning {
    border-left-color: var(--color-warning-border);
    color: var(--color-warning-border);
  }

  .status-full {
    border-left-color: var(--color-full-border);
    color: var(--color-full-border);
  }

  .status-exceeded {
    border-left-color: var(--color-error-border);
    color: var(--color-error-border);
  }

  .status-unknown {
    border-left-color: var(--color-border);
    color: var(--color-muted-text);
  }

  .status-label {
    font-size: var(--font-size-sm);
  }

  a {
    color: var(--color-primary);
  }

  a:focus-visible {
    outline: var(--focus-ring-width) solid var(--focus-ring-color);
    outline-offset: 2px;
  }
</style>
