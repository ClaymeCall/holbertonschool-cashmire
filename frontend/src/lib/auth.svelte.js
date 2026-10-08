// Shared current-user state for the app shell's auth-aware nav (issue #104
// follow-up). Backed by GET /api/auth/me/ (issue #26) — one reactive source
// of "am I logged in" instead of each page re-deriving it.
//
// `.svelte.js` extension is required for `$state` runes outside a
// `.svelte` component file.
import { apiFetch, ApiError } from "./api.js";

/** @typedef {{ id: number, email: string }} CurrentUser */
/** @type {CurrentUser | null} */
let user = $state(null);
/** @typedef {"loading" | "authenticated" | "anonymous"} AuthStatus */
/** @type {AuthStatus} */
let status = $state("loading");

/**
 * Read-only view of the current auth state. Exposed as getters (not a
 * plain object literal) so consumers reading `authState.user` see live
 * updates rather than a snapshot taken at import time.
 */
export const authState = {
  get user() {
    return user;
  },
  get status() {
    return status;
  },
};

/**
 * Sets the current user directly from an already-fetched response body
 * (the register and login endpoints both return the `UserSerializer`
 * shape on success) — avoids an extra round trip to /api/auth/me/ just to
 * learn what the server already told us.
 * @param {CurrentUser | null} nextUser
 */
export function setCurrentUser(nextUser) {
  user = nextUser;
  status = nextUser ? "authenticated" : "anonymous";
}

/**
 * Fetches the current session's user from the server. Called once on app
 * shell mount to resolve the initial auth state; a 401 is the normal
 * "not logged in" response, not an error to surface.
 */
export async function refreshCurrentUser() {
  try {
    const current = /** @type {CurrentUser} */ (
      await apiFetch("/api/auth/me/", { credentials: "include" })
    );
    setCurrentUser(current);
  } catch (err) {
    if (!(err instanceof ApiError) || err.status !== 401) {
      console.error("Failed to resolve current user:", err);
    }
    setCurrentUser(null);
  }
}
