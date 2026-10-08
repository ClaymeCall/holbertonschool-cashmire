<script>
  // Donut of this period's spending by category, for the landing-page
  // dashboard (DashboardCharts.svelte). Props-only — no fetching here, see
  // DashboardCharts for why.
  import { PieChart } from "layerchart";
  import { formatAmount } from "$lib/money";
  import { toPlotNumber } from "$lib/dashboard";

  /**
   * @typedef {Object} Props
   * @property {import("$lib/dashboard").CategoryTotal[]} totals
   */
  /** @type {Props} */
  let { totals } = $props();

  // Decorative accent tokens, explicitly earmarked in tokens.css for chart
  // fills — cycles if there are more categories than colors.
  const ACCENT_PALETTE = [
    "var(--color-camel)",
    "var(--color-dusty-rose)",
    "var(--color-heather-sage)",
    "var(--color-heather-taupe)",
    "var(--color-camel-deep)",
    "var(--color-mocha)",
  ];

  const chartData = $derived(
    totals.map((total) => ({
      categoryName: total.categoryName,
      value: toPlotNumber(total.total),
    })),
  );
</script>

<div class="chart-card">
  <h3>Dépenses par catégorie cette période</h3>
  {#if totals.length === 0}
    <p class="empty">Aucune dépense enregistrée cette période.</p>
  {:else}
    <div class="chart">
      <PieChart
        data={chartData}
        key="categoryName"
        value="value"
        c="categoryName"
        cRange={ACCENT_PALETTE}
        innerRadius={-20}
      />
    </div>
    <ul class="legend">
      {#each totals as total, i (total.categoryId)}
        <li>
          <span
            class="swatch"
            style={`background: ${ACCENT_PALETTE[i % ACCENT_PALETTE.length]}`}
          ></span>
          {total.categoryName} — {formatAmount(total.total)}
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
    flex-direction: column;
    gap: var(--space-xs);
    font-size: var(--font-size-sm);
  }

  .legend li {
    display: inline-flex;
    align-items: center;
    gap: var(--space-sm);
  }

  .swatch {
    width: 0.7rem;
    height: 0.7rem;
    border-radius: var(--radius-sm);
    flex-shrink: 0;
  }
</style>
