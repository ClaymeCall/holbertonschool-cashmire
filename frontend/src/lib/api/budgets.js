// Budgets API client — issues #52/#53. Thin wrappers over `apiFetch`
// against the routes documented in `docs/api-design.md` §4. These
// endpoints are NOT merged into `main` yet (tracked in #45–#50, open PRs
// #115/#121–125 at the time this was written) — this is built against the
// documented contract and will fail with a network/404-shaped error until
// that lands, exactly the pattern `login`/`register` used before #20-#24
// existed. Nothing here needs changing once it ships.
//
// Status rule (`docs/decisions/budget-thresholds.md`, binding): the server
// computes `status` (`ok` | `warning` | `full` | `exceeded`) from `spent`,
// `amount` and `alert_threshold`. This client never recomputes it — screens
// display the `status` string the API returns, verbatim.
import { apiFetch } from "$lib/api";

/**
 * @typedef {Object} Budget
 * @property {number} id
 * @property {number} user_id
 * @property {number} category_id
 * @property {string} amount
 * @property {string} period_start
 * @property {string} period_end
 * @property {string} alert_threshold
 * @property {string} spent
 * @property {string} remaining
 * @property {"ok" | "warning" | "full" | "exceeded"} [status]
 * @property {string} created_at
 * @property {string} updated_at
 */

/**
 * @param {{ category_id?: number }} [filters]
 * @returns {Promise<Budget[]>}
 */
export async function listBudgets(filters = {}) {
  const params = new URLSearchParams();
  if (filters.category_id !== undefined && filters.category_id !== null) {
    params.set("category_id", String(filters.category_id));
  }
  const query = params.toString();
  const data = await apiFetch(`/api/budgets/${query ? `?${query}` : ""}`, {
    credentials: "include",
  });
  return data.budgets;
}

/**
 * @param {{ category_id: number, amount: string, period_start: string, period_end: string, alert_threshold?: string }} input
 * @returns {Promise<Budget>}
 */
export function createBudget(input) {
  return apiFetch("/api/budgets/", {
    method: "POST",
    credentials: "include",
    body: input,
  });
}

/**
 * Only `amount` and `alert_threshold` are modifiable after creation per
 * `docs/api-design.md` §4.4 — `category_id`/`period_start`/`period_end`
 * are not accepted here.
 *
 * @param {number} id
 * @param {{ amount?: string, alert_threshold?: string }} input
 * @returns {Promise<Budget>}
 */
export function updateBudget(id, input) {
  return apiFetch(`/api/budgets/${id}/`, {
    method: "PATCH",
    credentials: "include",
    body: input,
  });
}

/**
 * Calendar-month helper for the "month/year" picker #53's acceptance
 * criteria call for, translating it into the `period_start`/`period_end`
 * pair the API actually stores. Pure calendar arithmetic on integers (no
 * money involved), so plain `Date` math is fine here — this is not a case
 * `money.js`'s ban on float coercion applies to.
 *
 * @param {string} month `"YYYY-MM"`, as produced by `<input type="month">`.
 * @returns {{ period_start: string, period_end: string }}
 */
export function monthToPeriod(month) {
  const [year, monthNum] = month.split("-").map(Number);
  const periodStart = `${month}-01`;
  // Day 0 of the *next* month is the last day of this one.
  const lastDay = new Date(year, monthNum, 0).getDate();
  const periodEnd = `${month}-${String(lastDay).padStart(2, "0")}`;
  return { period_start: periodStart, period_end: periodEnd };
}

/**
 * Inverse of {@link monthToPeriod}'s first half, for pre-filling the edit
 * form's (disabled) month display from an existing budget's `period_start`.
 *
 * @param {string} periodStart `"YYYY-MM-DD"`.
 * @returns {string} `"YYYY-MM"`.
 */
export function periodToMonth(periodStart) {
  return periodStart.slice(0, 7);
}
