<script>
  // Daily spending trend over the last 30 days, for the landing-page
  // dashboard (DashboardCharts.svelte). Props-only — no fetching here, see
  // DashboardCharts for why.
  import { LineChart } from "layerchart";
  import { toPlotNumber } from "$lib/dashboard";

  /**
   * @typedef {Object} Props
   * @property {import("$lib/dashboard").DailyTotal[]} daily
   */
  /** @type {Props} */
  let { daily } = $props();

  /**
   * `"YYYY-MM-DD"` -> local midnight `Date`. Never `new Date(dateString)`
   * directly — that parses as UTC per the ISO-8601 spec and can land on the
   * wrong calendar day once rendered in a non-UTC timezone.
   *
   * @param {string} dateString
   * @returns {Date}
   */
  function parseLocalDate(dateString) {
    const [year, month, day] = dateString.split("-").map(Number);
    return new Date(year, month - 1, day);
  }

  const chartData = $derived(
    daily.map((day) => ({ date: parseLocalDate(day.date), total: toPlotNumber(day.total) })),
  );

  const hasSpending = $derived(daily.some((day) => day.total !== "0"));
</script>

<div class="chart-card">
  <h3>Spending over the last 30 days</h3>
  {#if !hasSpending}
    <p class="empty">No expenses recorded in the last 30 days.</p>
  {:else}
    <div class="chart">
      <LineChart
        data={chartData}
        x="date"
        y="total"
        series={[{ key: "total", label: "Spent", color: "var(--color-accent)" }]}
      />
    </div>
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
</style>
