// Expenses API client — issues #40/#41. Thin wrappers over `apiFetch`
// around the routes implemented in `backend/api/views.py` and documented in
// `docs/api-design.md` §3. No single-expense GET exists on the backend (only
// list+create are combined under `/api/expenses/`, and detail only supports
// PATCH/PUT/DELETE) — the edit screen therefore looks its expense up out of
// an already-fetched list rather than fetching it individually.
//
// Money rule (see `api.js`'s file-top comment, binding): `amount` travels as
// a string end to end. Nothing here parses or formats it — that's `money.js`
// and the screens that call it.
import { apiFetch } from "$lib/api";

/**
 * @typedef {Object} Expense
 * @property {number} id
 * @property {number} user_id
 * @property {number} category_id
 * @property {string} amount
 * @property {string | null} description
 * @property {string} date
 * @property {string} created_at
 * @property {string} updated_at
 */

/**
 * @param {{ category_id?: number, date_from?: string, date_to?: string }} [filters]
 * @returns {Promise<Expense[]>} already ordered newest-first by the backend
 *   (`Expense.Meta.ordering = ["-date", "-id"]`) — not re-sorted here.
 */
export async function listExpenses(filters = {}) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  }
  const query = params.toString();
  const data = await apiFetch(`/api/expenses/${query ? `?${query}` : ""}`, {
    credentials: "include",
  });
  return data.expenses;
}

/**
 * @param {{ category_id: number, amount: string, description?: string, date: string }} input
 * @returns {Promise<Expense>}
 */
export function createExpense(input) {
  return apiFetch("/api/expenses/", {
    method: "POST",
    credentials: "include",
    body: input,
  });
}

/**
 * Partial update — only the provided fields are sent (`PATCH`).
 *
 * @param {number} id
 * @param {{ category_id?: number, amount?: string, description?: string | null, date?: string }} input
 * @returns {Promise<Expense>}
 */
export function updateExpense(id, input) {
  return apiFetch(`/api/expenses/${id}/`, {
    method: "PATCH",
    credentials: "include",
    body: input,
  });
}
