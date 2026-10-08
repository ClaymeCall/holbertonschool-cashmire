<script>
  // Grouped "budgeted vs spent" bar per category, for the landing-page
  // dashboard (DashboardCharts.svelte). Props-only — no fetching here, see
  // DashboardCharts for why (single centralized fetch, not per-chart).
  import { BarChart } from "layerchart";
  import { CircleCheck, TriangleAlert, CircleAlert, CircleX, CircleHelp } from "@lucide/svelte";
  import { toPlotNumber } from "$lib/dashboard";

  /**
   * @typedef {Object} Props
   * @property {import("$lib/dashboard").BudgetVsSpentRow[]} rows
   */
  /** @type {Props} */
  let { rows } = $props();

  // Same icon+text pairing as BudgetsList's STATUS_META — color is never the
  // only signal (docs/mvp-scope.md §3.7).
  const STATUS_META = {
    ok: { label: "On track", icon: CircleCheck, color: "var(--color-success-border)" },
    warning: {
      label: "Approaching limit",
      icon: TriangleAlert,
      color: "var(--color-warning-border)",
    },
    full: { label: "Budget reached", icon: CircleAlert, color: "var(--color-full-border)" },
    exceeded: { label: "Over budget", icon: CircleX, color: "var(--color-error-border)" },
  };

  /** @param {import("$lib/dashboard").BudgetVsSpentRow} row */
  function statusMeta(row) {
    return STATUS_META[row.status] ?? { label: "Unknown", icon: CircleHelp, color: "var(--color-muted-text)" };
  }

  const chartData = $derived(
    rows.map((row) => ({
      categoryName: row.categoryName,
      amount: toPlotNumber(row.amount),
      spent: toPlotNumber(row.spent),
      status: row.status,
    })),
  );

  const visibleStatuses = $derived(
    Array.from(new Set(rows.map((row) => row.status ?? "unknown"))),
  );

  const series = [
    { key: "amount", label: "Budgeted", color: "var(--color-border-subtle)" },
    {
      key: "spent",
      label: "Spent",
      props: { fill: (/** @type {{ status?: string }} */ d) => statusMeta(d).color },
    },
  ];
</script>

<div class="chart-card">
  <h3>Budget vs spent by category</h3>
  {#if rows.length === 0}
    <p class="empty">No budgets yet.</p>
  {:else}
    <div class="chart">
      <BarChart data={chartData} x="categoryName" {series} seriesLayout="group" />
    </div>
    <ul class="legend">
      {#each visibleStatuses as status (status)}
        {@const meta = STATUS_META[status] ?? { label: "Unknown", icon: CircleHelp, color: "var(--color-muted-text)" }}
        <li style={`color: ${meta.color}`}>
          <meta.icon size={14} /> {meta.label}
        </li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .chart-card {
    border: 1px solid var(--color-border-subtle);
    border-radius: var(--radius-md);
    padding: var(--space-lg);
  }

  h3 {
    font-family: var(--font-heading);
    font-size: 1.05rem;
    color: var(--color-heading);
    margin: 0 0 var(--space-md);
  }

  .chart {
    height: 240px;
  }

  .empty {
    color: var(--color-muted-text);
  }

  .legend {
    list-style: none;
    margin: var(--space-md) 0 0;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-lg);
    font-size: var(--font-size-sm);
  }

  .legend li {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
  }

</style>
