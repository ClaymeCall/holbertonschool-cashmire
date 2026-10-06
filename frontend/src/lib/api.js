// Shared API client helper for the Cashmire front-end.
// See docs/specs/issue-15-svelte-skeleton.md §4.3 for the full contract.
//
// Error-shape decision (§4.3.4): a `fetch` rejection caused by a network
// failure, DNS failure or CORS rejection is wrapped into an `ApiError` with
// `status: 0`, rather than left to propagate as a raw `TypeError`. This
// gives every caller exactly one error type (`ApiError`) to catch, which is
// the spec's documented preference.
//
// Money rule (§4.3.6, binding): this helper applies NO numeric coercion of
// any kind to response bodies — no `Number()`, no `parseFloat()`, no
// "normalise amounts" step, ever. The backend serialises `NUMERIC` money
// fields as JSON strings; silently turning them into JS floats here would
// reintroduce float money across the whole app. Decimal-aware formatting is
// a separate, future concern. Do not "improve" this.

/** @type {string} */
const DEFAULT_BASE_URL = "http://localhost:8000";

/**
 * Resolve the API base URL from a raw env value, applying the "unset or
 * blank falls back to the default, trailing slash stripped" rule (§4.3.3).
 *
 * Exported for testability only (see
 * docs/specs/issue-15-svelte-skeleton.md §6.1) — `import.meta.env` is read
 * once at module scope below, so this is not part of the supported public
 * surface; callers should use {@link API_BASE_URL} instead.
 *
 * @param {string | undefined | null} raw
 * @returns {string}
 */
export function resolveBaseUrl(raw) {
  if (raw === undefined || raw === null || raw.trim() === "") {
    return DEFAULT_BASE_URL;
  }
  return raw.replace(/\/+$/, "");
}

/**
 * Resolved base URL for the Cashmire API, without a trailing slash.
 * Read once at module scope from `import.meta.env.VITE_API_URL`, falling
 * back to {@link DEFAULT_BASE_URL} when that is unset or blank. Vite inlines
 * `import.meta.env` at build/serve time, so this is effectively a
 * build-time constant — there is nothing to re-evaluate at runtime.
 * @type {string}
 */
export const API_BASE_URL = resolveBaseUrl(import.meta.env.VITE_API_URL);

/**
 * Build an absolute API URL from a path.
 *
 * Joins with exactly one `/` between base and path, and preserves the
 * caller's trailing slash verbatim — Django's routes are declared with
 * trailing slashes (e.g. `health/`), so this must never add, strip or
 * "tidy" one.
 *
 * @param {string} path Path relative to the API root; leading slash optional.
 * @returns {string}
 */
export function apiUrl(path) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
}

/**
 * Thrown when the API responds with a non-2xx status, when a response body
 * that should be JSON cannot be parsed, or when the underlying `fetch` call
 * itself fails (network/DNS/CORS failure — see the file-top comment), in
 * which case `status` is `0`.
 */
export class ApiError extends Error {
  /**
   * @param {string} message
   * @param {{ status: number, url: string, body?: unknown }} details
   */
  constructor(message, { status, url, body }) {
    super(message);
    this.name = "ApiError";
    /** @type {number} */
    this.status = status;
    /** @type {string} */
    this.url = url;
    /** @type {unknown} */
    this.body = body;
  }
}

/**
 * @param {unknown} body
 * @returns {boolean} true when `body` should be JSON-encoded by `apiFetch`.
 */
function isJsonEncodable(body) {
  if (body === undefined || body === null || typeof body !== "object") {
    return false;
  }
  if (typeof FormData !== "undefined" && body instanceof FormData) {
    return false;
  }
  if (typeof Blob !== "undefined" && body instanceof Blob) {
    return false;
  }
  if (typeof URLSearchParams !== "undefined" && body instanceof URLSearchParams) {
    return false;
  }
  if (typeof ArrayBuffer !== "undefined" && body instanceof ArrayBuffer) {
    return false;
  }
  return true;
}

/**
 * fetch wrapper: resolves the URL against {@link API_BASE_URL}, sets JSON
 * headers, JSON-encodes a plain-object body, and rejects on non-2xx.
 *
 * - Default `method` is `GET`.
 * - `Accept: application/json` is set on every request.
 * - `credentials` defaults to the `fetch` default (i.e. is NOT forced to
 *   `"include"`) — there is no cookie auth yet, see §4.3.4.
 * - No retry, no caching, no timeout, no interceptor chain. A timeout can be
 *   added by the caller via `AbortSignal` (the `signal` option is forwarded
 *   unchanged).
 *
 * @param {string} path
 * @param {RequestInit & { body?: unknown }} [options]
 * @returns {Promise<unknown>} parsed JSON, or `null` for 204/empty bodies
 */
export async function apiFetch(path, options = {}) {
  const { body, headers, ...rest } = options;
  const url = apiUrl(path);

  /** @type {Record<string, string>} */
  const requestHeaders = { Accept: "application/json" };

  /** @type {BodyInit | undefined} */
  let requestBody;
  if (isJsonEncodable(body)) {
    requestHeaders["Content-Type"] = "application/json";
    requestBody = JSON.stringify(body);
  } else if (body !== undefined) {
    // FormData, Blob, string, etc: passed through untouched, no
    // Content-Type set — the platform (or the caller) decides it.
    requestBody = /** @type {BodyInit} */ (body);
  }

  // Caller's headers win over the defaults above.
  Object.assign(requestHeaders, headers);

  /** @type {Response} */
  let response;
  try {
    response = await fetch(url, {
      method: "GET",
      ...rest,
      headers: requestHeaders,
      ...(requestBody !== undefined ? { body: requestBody } : {}),
    });
  } catch (err) {
    throw new ApiError("Network request failed", {
      status: 0,
      url,
      body: err,
    });
  }

  if (response.status === 204) {
    return null;
  }

  const rawText = await response.text();

  if (rawText === "") {
    if (response.ok) {
      return null;
    }
    throw new ApiError(
      `API request to ${url} failed with status ${response.status}`,
      { status: response.status, url, body: null },
    );
  }

  /** @type {unknown} */
  let parsedBody;
  try {
    parsedBody = JSON.parse(rawText);
  } catch {
    throw new ApiError(`API response from ${url} was not valid JSON`, {
      status: response.status,
      url,
      body: rawText,
    });
  }

  if (!response.ok) {
    throw new ApiError(
      `API request to ${url} failed with status ${response.status}`,
      { status: response.status, url, body: parsedBody },
    );
  }

  return parsedBody;
}
