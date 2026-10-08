<script>
  // One budget's card — factored out of `routes/budgets/+page.svelte` (#52)
  // for issue #104, which needs the exact same rendering on the home
  // dashboard's budget summary. `docs/decisions/0001-shared-app-shell-layout.md`'s
  // design-system amendment deferred introducing a Card until a second
  // consumer existed; this is that second consumer.
  //
  // Never recomputes `status` (see budgets/+page.svelte's file-top comment
  // and docs/decisions/budget-thresholds.md) — only maps the four
  // documented values to a color + label, and computes the progress bar's
  // percentage display with `money.js`'s `percentOf`.
  import { formatAmount, percentOf, compareDecimal } from "$lib/money";

  /**
   * @typedef {Object} Props
   * @property {import("$lib/api/budgets").Budget} budget
   * @property {string} categoryName
   */

  /** @type {Props} */
  let { budget, categoryName } = $props();

  const STATUS_META = {
    ok: { label: "On track", className: "status-ok" },
    warning: { label: "Approaching limit", className: "status-warning" },
    full: { label: "Budget reached", className: "status-full" },
    exceeded: { label: "Over budget", className: "status-exceeded" },
  };

  const meta = $derived(
    STATUS_META[budget.status] ?? { label: "Unknown", className: "status-unknown" },
  );

  /**
   * @returns {string} e.g. "47.0" — capped at 100 for the progress bar's
   *   width even when the budget is exceeded (the "Over budget" label, not
   *   the bar, is what communicates overspend).
   */
  const percentForBar = $derived.by(() => {
    const percent = percentOf(budget.spent, budget.amount);
    return compareDecimal(percent, "100") > 0 ? "100" : percent;
  });
</script>

<li class={meta.className}>
  <div class="budget-header">
    <span class="category">{categoryName}</span>
    <span class="status-label">{meta.label}</span>
  </div>
  <p class="amounts">
    {formatAmount(budget.spent)} spent of {formatAmount(budget.amount)}
    ({formatAmount(budget.remaining)} remaining)
  </p>
  <div
    class="progress-track"
    role="progressbar"
    aria-valuenow={percentForBar}
    aria-valuemin="0"
    aria-valuemax="100"
    aria-label={`${categoryName} consumption`}
  >
    <div class="progress-fill" style={`width: ${percentForBar}%`}></div>
  </div>
  <a href={`/budgets/${budget.id}/edit`}>Edit</a>
</li>

<style>
  li {
    border: 1px solid var(--color-border-subtle);
    border-left-width: 4px;
    border-radius: var(--radius-sm);
    padding: var(--space-md) var(--space-lg);
    list-style: none;
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
