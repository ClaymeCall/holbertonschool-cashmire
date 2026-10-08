// In-memory auth-state store — issue #104's nav-awareness slice.
//
// Nothing here is written to `localStorage`/`sessionStorage`:
// `docs/decisions/0003-session-cookie-auth-strategy.md` point 6 is explicit
// that nothing is client-stored beyond the browser's own `HttpOnly` session
// cookie, specifically so there is no token sitting in storage for an XSS
// payload to read. This store is purely an in-memory signal for the nav to
// render against.
//
// There is deliberately no "check `/api/auth/me/` on mount" here, either:
// `routes/layout.test.js`'s T-4b asserts that rendering the shared layout
// issues zero fetch calls, and this module respects that by only ever being
// written to by an action that already made its own request for its own
// reasons (login, register, logout) — it never polls the server on its own.
//
// Known consequence, accepted for this slice of #104: a hard page reload
// resets this store to "logged out" even with a still-valid session
// cookie, until the next login/register. Revisit once #26/#27 (current-user
// dependency) land, if the team decides that trade-off should change.
import { writable } from "svelte/store";
import { apiFetch } from "$lib/api";

/** @type {import("svelte/store").Writable<Record<string, unknown> | null>} */
export const currentUser = writable(null);

/**
 * Called by login/register right after their own successful POST — not a
 * new request, just recording that one just succeeded. Always results in a
 * truthy store value (a successful login/register always means a session
 * now exists), and tries to capture the actual user record for any screen
 * that wants to display it later, handling both documented response
 * shapes: login's `{ token, user: {...} }` (docs/api-design.md §2.2) and
 * register's flat `{ id, email, ... }` (§2.1) — without needing to know
 * which endpoint called it.
 *
 * @param {unknown} responseBody
 */
export function setCurrentUser(responseBody) {
  if (
    !responseBody ||
    typeof responseBody !== "object" ||
    Array.isArray(responseBody)
  ) {
    currentUser.set({});
    return;
  }
  const body = /** @type {Record<string, unknown>} */ (responseBody);
  const user = body.user && typeof body.user === "object" ? body.user : body;
  currentUser.set(user);
}

/**
 * Calls `POST /api/auth/logout/` and clears the store only once that
 * succeeds — a failed logout leaves the nav showing the logged-in state,
 * rather than silently pretending the session is gone.
 *
 * @returns {Promise<void>}
 */
export async function logout() {
  await apiFetch("/api/auth/logout/", {
    method: "POST",
    credentials: "include",
  });
  currentUser.set(null);
}
