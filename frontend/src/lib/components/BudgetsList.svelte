<script>
  // Reusable budget dashboard list — extracted from
  // routes/budgets/+page.svelte (issue #104 componentization follow-up) so
  // it can be dropped anywhere (the /budgets route, a home-page preview, …)
  // without dragging along that route's own page chrome (the <h1>, the
  // "Add budget" link). The route page still owns those; this component
  // owns only the loading/error/empty/list states.
  //
  // `spent`/`remaining`/`status` are all computed server-side (per
  // `docs/decisions/budget-thresholds.md`); this component never
  // recomputes `status` — it only maps the four documented values to a
  // color + label. The percentage-consumed figure shown in the progress
  // bar IS computed client-side with `money.js`'s `percentOf`, which exists
  // for exactly this (see its file-top comment) — that's display
  // arithmetic, not the ok/warning/full/exceeded decision itself.
  import { onMount } from "svelte";
  import {
    CircleCheck,
    TriangleAlert,
    CircleAlert,
    CircleX,
    CircleHelp,
    Pencil,
    RefreshCw,
  } from "@lucide/svelte";
  import { listBudgets } from "$lib/api/budgets";
  import { listCategories } from "$lib/api/categories";
  import { formatAmount, percentOf, compareDecimal } from "$lib/money";
  import Button from "$lib/components/Button.svelte";
  import FormError from "$lib/components/FormError.svelte";

  /**
   * @typedef {Object} Props
   * @property {number} [limit] - Cap the number of budgets rendered (the
   *   API's own order is kept, just truncated) — for a compact preview,
   *   e.g. on the home page. Omit to show every budget.
   */
  /** @type {Props} */
  let { limit } = $props();

  /** @typedef {"loading" | "ready" | "error"} ViewState */

  /** @type {ViewState} */
  let state = $state("loading");
  /** @type {import("$lib/api/budgets").Budget[]} */
  let budgets = $state([]);
  /** @type {Map<number, string>} */
  let categoryNames = $state(new Map());
  /** @type {string | null} */
  let errorMessage = $state(null);

  const visibleBudgets = $derived(
    typeof limit === "number" ? budgets.slice(0, limit) : budgets,
  );

  // Icon always paired with the text label, never alone — color is never
  // the sole carrier of status either (docs/mvp-scope.md §3.7); the icon
  // is a second, non-color channel reinforcing the same label.
  const STATUS_META = {
    ok: { label: "Sous contrôle", className: "status-ok", icon: CircleCheck },
    warning: { label: "Proche de la limite", className: "status-warning", icon: TriangleAlert },
    full: { label: "Budget atteint", className: "status-full", icon: CircleAlert },
    exceeded: { label: "Budget dépassé", className: "status-exceeded", icon: CircleX },
  };

  /**
   * @param {import("$lib/api/budgets").Budget} budget
   */
  function statusMeta(budget) {
    return (
      STATUS_META[budget.status] ?? {
        label: "Inconnu",
        className: "status-unknown",
        icon: CircleHelp,
      }
    );
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
      errorMessage = "Impossible de charger vos budgets. Réessayez dans un instant.";
      state = "error";
      console.error("Failed to load budgets:", err);
    }
  }

  onMount(load);
</script>

{#if state === "loading"}
  <p role="status">Chargement de vos budgets…</p>
{:else if state === "error"}
  <FormError messages={errorMessage ? [errorMessage] : []} />
  <Button type="button" onclick={load}><RefreshCw size={16} /> Réessayer</Button>
{:else if visibleBudgets.length === 0}
  <p>
    Aucun budget pour l'instant. <a href="/budgets/new">Définissez une limite mensuelle pour une catégorie</a>
    pour commencer à la suivre ici.
  </p>
{:else}
  <ul class="budget-list">
    {#each visibleBudgets as budget (budget.id)}
      {@const meta = statusMeta(budget)}
      <li class={meta.className}>
        <div class="budget-header">
          <span class="category">
            {categoryNames.get(budget.category_id) ?? "Catégorie inconnue"}
          </span>
          <span class="status-label"><meta.icon size={16} /> {meta.label}</span>
        </div>
        <p class="amounts">
          {formatAmount(budget.spent)} dépensé(s) sur {formatAmount(budget.amount)}
          ({formatAmount(budget.remaining)} restant(s))
        </p>
        <p class="percentage">{percentOf(budget.spent, budget.amount)}% used</p>
        <div
          class="progress-track"
          role="progressbar"
          aria-valuenow={percentForBar(budget)}
          aria-valuemin="0"
          aria-valuemax="100"
          aria-label={`Consommation du budget ${categoryNames.get(budget.category_id) ?? ""}`}
        >
          <div class="progress-fill" style={`width: ${percentForBar(budget)}%`}></div>
        </div>
        <a href={`/budgets/${budget.id}/edit`}><Pencil size={14} /> Modifier</a>
      </li>
    {/each}
  </ul>
{/if}

<style>
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
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    font-size: var(--font-size-sm);
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
