// Exact decimal arithmetic over decimal *strings*.
//
// WHY THIS EXISTS: `api.js`'s file-top comment states a binding rule — a
// response body's money fields are JSON strings (the backend serializes
// NUMERIC that way) and no caller may apply numeric coercion to them, ever.
// But budget/expense screens (#52, #53, and whatever expense work follows)
// genuinely need `limit - spent` and `spent / limit`. The only way to have
// both is exact integer arithmetic, which `BigInt` gives us as a language
// built-in (no new dependency).
//
// FORBIDDEN IN THIS FILE, enforced by money.test.js's source-text scan:
//   Number(), parseFloat(), parseInt(), any member of the global Math
//   object, toFixed(), Intl.NumberFormat.
// `BigInt(digitString)` is the ONLY permitted conversion, and it is exact by
// construction. Do not "simplify" any of this with floating point.
//
// This module is not a mock and should not be deleted when #92 (replacing
// the mocked auth/expense/budget API clients) lands — it is pure arithmetic,
// independent of whether the data it operates on came from a mock or a real
// response.

/**
 * Matches an optionally-signed plain decimal. Deliberately strict: no
 * whitespace, no exponent, no bare leading/trailing dot, no "NaN"/"Infinity".
 */
const DECIMAL_RE = /^-?\d+(\.\d+)?$/;

/**
 * @param {unknown} s
 * @returns {boolean} true iff `s` is a string this module can operate on.
 */
export function isValidDecimalString(s) {
  return typeof s === "string" && DECIMAL_RE.test(s);
}

/**
 * Internal representation: the value equals `units * 10^-scale`.
 * "400.00" -> { units: 40000n, scale: 2 }; "-7.5" -> { units: -75n, scale: 1 }.
 *
 * @param {string} s
 * @param {string} label used in the thrown message so callers can see which
 *   argument was bad.
 * @returns {{ units: bigint, scale: number }}
 */
function parseDecimal(s, label) {
  if (!isValidDecimalString(s)) {
    // Throwing beats returning NaN: a silent NaN is exactly the failure mode
    // this module exists to prevent.
    throw new TypeError(
      `${label} must be a plain decimal string like "0", "400.00" or "-50.00"; received ${JSON.stringify(s)}`,
    );
  }
  const negative = s.startsWith("-");
  const unsigned = negative ? s.slice(1) : s;
  const dotIndex = unsigned.indexOf(".");
  const digits =
    dotIndex === -1 ? unsigned : unsigned.slice(0, dotIndex) + unsigned.slice(dotIndex + 1);
  const scale = dotIndex === -1 ? 0 : unsigned.length - dotIndex - 1;
  const units = BigInt(digits);
  return { units: negative ? -units : units, scale };
}

/**
 * Rescale `value` UP to `targetScale` by multiplying by a power of ten.
 * Lossless. Never call this with a smaller target — scaling down would round.
 *
 * @param {{ units: bigint, scale: number }} value
 * @param {number} targetScale
 * @returns {bigint}
 */
function unitsAtScale(value, targetScale) {
  let units = value.units;
  for (let i = value.scale; i < targetScale; i += 1) {
    units *= 10n;
  }
  return units;
}

/**
 * Render scaled integer units back to a decimal string at `scale` places.
 *
 * @param {bigint} units
 * @param {number} scale
 * @returns {string}
 */
function unitsToString(units, scale) {
  const negative = units < 0n;
  const digits = (negative ? -units : units).toString().padStart(scale + 1, "0");
  const whole = digits.slice(0, digits.length - scale);
  const fraction = scale === 0 ? "" : `.${digits.slice(digits.length - scale)}`;
  return `${negative ? "-" : ""}${whole}${fraction}`;
}

/**
 * Larger of two scales. A tiny local helper rather than the global Math
 * object's `max`, because this file is kept literally `Math`-free so the
 * source-text ban in money.test.js stays simple and unambiguous — it cannot
 * tell a safe `max` on two small integer scales from an unsafe `round` on
 * money.
 *
 * @param {number} a
 * @param {number} b
 * @returns {number}
 */
function maxScale(a, b) {
  return a > b ? a : b;
}

/**
 * Exact comparison. `compareDecimal("1.10", "1.1") === 0`.
 *
 * Use this ANYWHERE two money/percentage strings are compared. Never use the
 * native `<` / `>=` operators on decimal strings: those compare
 * lexicographically, so `"9.0" >= "80"` is `true` — a real bug class this
 * function exists to eliminate.
 *
 * @param {string} a
 * @param {string} b
 * @returns {-1 | 0 | 1}
 */
export function compareDecimal(a, b) {
  const left = parseDecimal(a, "a");
  const right = parseDecimal(b, "b");
  const scale = maxScale(left.scale, right.scale);
  const leftUnits = unitsAtScale(left, scale);
  const rightUnits = unitsAtScale(right, scale);
  if (leftUnits < rightUnits) return -1;
  if (leftUnits > rightUnits) return 1;
  return 0;
}

/**
 * `a - b`, exact. Result scale is `max(scale(a), scale(b))`, so
 * `subtractDecimal("400.00", "352.18") === "47.82"`. May be negative.
 *
 * @param {string} a
 * @param {string} b
 * @returns {string}
 */
export function subtractDecimal(a, b) {
  const left = parseDecimal(a, "a");
  const right = parseDecimal(b, "b");
  const scale = maxScale(left.scale, right.scale);
  return unitsToString(unitsAtScale(left, scale) - unitsAtScale(right, scale), scale);
}

/**
 * `a + b`, exact. Result scale is `max(scale(a), scale(b))`, so
 * `addDecimal("400.00", "352.18") === "752.18"`.
 *
 * @param {string} a
 * @param {string} b
 * @returns {string}
 */
export function addDecimal(a, b) {
  const left = parseDecimal(a, "a");
  const right = parseDecimal(b, "b");
  const scale = maxScale(left.scale, right.scale);
  return unitsToString(unitsAtScale(left, scale) + unitsAtScale(right, scale), scale);
}

/**
 * Sum a list of decimal strings, exact. An empty list returns `"0"` (the
 * additive identity) rather than throwing — summing a category/day with no
 * matching expenses is a normal case callers shouldn't have to special-case.
 *
 * @param {string[]} values
 * @returns {string}
 */
export function sumDecimal(values) {
  return values.reduce((acc, value) => addDecimal(acc, value), "0");
}

/**
 * `part / whole * 100`, as a string with exactly one decimal place.
 *
 * TRUNCATED toward zero, not rounded — deliberate. With rounding, spending
 * 99.96% of a budget would display as "100.0" while a status badge driven by
 * the same threshold still said "Close to limit", so the number would
 * contradict the badge. Truncation can only ever under-state consumption, so
 * that contradiction is impossible.
 *
 * @param {string} part
 * @param {string} whole
 * @returns {string} e.g. "88.0", "137.5"
 * @throws {RangeError} if `whole` is zero.
 */
export function percentOf(part, whole) {
  const partValue = parseDecimal(part, "part");
  const wholeValue = parseDecimal(whole, "whole");
  const scale = maxScale(partValue.scale, wholeValue.scale);
  const partUnits = unitsAtScale(partValue, scale);
  const wholeUnits = unitsAtScale(wholeValue, scale);

  if (wholeUnits === 0n) {
    // Guard, not a code path expected to be reached in normal use: a caller
    // dividing by a budget's limit should reject a zero limit before it ever
    // gets here.
    throw new RangeError("percentOf: `whole` must not be zero");
  }

  // x1000 then take one decimal place back out => one decimal place of
  // precision, with BigInt division truncating toward zero for us.
  const scaled = (partUnits * 1000n) / wholeUnits;
  return unitsToString(scaled, 1);
}

/**
 * Display helper: render a decimal string with exactly two decimal places,
 * by string surgery only. Truncates toward zero rather than rounding, for the
 * same reason as `percentOf`.
 *
 * No thousands separators and no currency symbol — locale-aware formatting
 * without float coercion is a separate concern. `Intl.NumberFormat` is NOT an
 * option here: it takes a `number`, so it is a float coercion wearing a
 * nicer hat.
 *
 * @param {string} s
 * @returns {string} e.g. "400.00", "-50.00"
 */
export function formatAmount(s) {
  const value = parseDecimal(s, "amount");
  const targetScale = 2;
  if (value.scale <= targetScale) {
    return unitsToString(unitsAtScale(value, targetScale), targetScale);
  }
  // More than 2 dp: truncate toward zero by dividing the units down.
  let divisor = 1n;
  for (let i = targetScale; i < value.scale; i += 1) {
    divisor *= 10n;
  }
  return unitsToString(value.units / divisor, targetScale);
}
