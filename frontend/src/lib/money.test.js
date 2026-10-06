// Pure unit tests for money.js — no fetch, no component rendering, no I/O
// beyond reading this module's own source text for the source-scan test
// below.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, it, expect } from "vitest";

import {
  isValidDecimalString,
  compareDecimal,
  subtractDecimal,
  percentOf,
  formatAmount,
} from "./money.js";

describe("isValidDecimalString", () => {
  it("accepts plain decimals, with or without a fractional part, signed or not", () => {
    expect(isValidDecimalString("0")).toBe(true);
    expect(isValidDecimalString("400.00")).toBe(true);
    expect(isValidDecimalString("-50.00")).toBe(true);
    expect(isValidDecimalString("-7.5")).toBe(true);
  });

  it("rejects anything that isn't a plain decimal string", () => {
    expect(isValidDecimalString("")).toBe(false);
    expect(isValidDecimalString(" 1.00")).toBe(false);
    expect(isValidDecimalString("1.00 ")).toBe(false);
    expect(isValidDecimalString("1e3")).toBe(false);
    expect(isValidDecimalString(".5")).toBe(false);
    expect(isValidDecimalString("5.")).toBe(false);
    expect(isValidDecimalString("NaN")).toBe(false);
    expect(isValidDecimalString("Infinity")).toBe(false);
    expect(isValidDecimalString(null)).toBe(false);
    expect(isValidDecimalString(undefined)).toBe(false);
    expect(isValidDecimalString(1.5)).toBe(false);
  });
});

describe("compareDecimal", () => {
  it("treats differently-scaled representations of the same value as equal", () => {
    expect(compareDecimal("1.10", "1.1")).toBe(0);
    expect(compareDecimal("1", "1.0")).toBe(0);
    expect(compareDecimal("-0", "0")).toBe(0);
  });

  it("orders by value, not lexicographically", () => {
    // "9.0" >= "80" is true under native string/number-ish comparison —
    // this function exists specifically so that bug class can't happen.
    expect(compareDecimal("9.0", "80")).toBe(-1);
    expect(compareDecimal("80", "9.0")).toBe(1);
  });

  it("handles negative values correctly", () => {
    expect(compareDecimal("-5", "-3")).toBe(-1);
    expect(compareDecimal("-3", "-5")).toBe(1);
    expect(compareDecimal("-1", "1")).toBe(-1);
  });

  it("rejects a malformed operand", () => {
    expect(() => compareDecimal("1.2.3", "1")).toThrow(TypeError);
    expect(() => compareDecimal("1", "abc")).toThrow(TypeError);
  });
});

describe("subtractDecimal", () => {
  it("subtracts exactly, at the larger of the two operands' scales", () => {
    expect(subtractDecimal("400.00", "352.18")).toBe("47.82");
    expect(subtractDecimal("10", "3.5")).toBe("6.5");
  });

  it("can go negative", () => {
    expect(subtractDecimal("50.00", "75.00")).toBe("-25.00");
  });

  it("is exact where float subtraction famously isn't", () => {
    // 0.1 - 0.2 in IEEE754 is roughly -0.1 but not clean.
    expect(subtractDecimal("0.3", "0.2")).toBe("0.1");
  });
});

describe("percentOf", () => {
  it("computes an exact percentage to one decimal place", () => {
    expect(percentOf("50", "200")).toBe("25.0");
    expect(percentOf("90", "100")).toBe("90.0");
  });

  it("truncates toward zero rather than rounding", () => {
    // 1/3 = 33.333...% — rounding to one place would give "33.3" too, so use
    // a case where rounding and truncation actually disagree.
    expect(percentOf("9996", "10000")).toBe("99.9"); // 99.96%, would round to 100.0
    expect(percentOf("1", "3")).toBe("33.3");
  });

  it("can exceed 100% without clamping — that's the caller's job", () => {
    expect(percentOf("150", "100")).toBe("150.0");
  });

  it("throws RangeError when dividing by zero", () => {
    expect(() => percentOf("10", "0")).toThrow(RangeError);
  });
});

describe("formatAmount", () => {
  it("pads to exactly two decimal places", () => {
    expect(formatAmount("400")).toBe("400.00");
    expect(formatAmount("5.5")).toBe("5.50");
    expect(formatAmount("0")).toBe("0.00");
  });

  it("truncates beyond two decimal places rather than rounding", () => {
    expect(formatAmount("5.555")).toBe("5.55");
    expect(formatAmount("5.999")).toBe("5.99");
  });

  it("preserves the sign", () => {
    expect(formatAmount("-50")).toBe("-50.00");
  });

  it("rejects a malformed amount", () => {
    expect(() => formatAmount("not-a-number")).toThrow(TypeError);
  });
});

describe("source-text ban on float coercion", () => {
  // The whole point of this module is that money never becomes a JS number.
  // This scans money.js's own source — with comments stripped, so the
  // module's documentation of the ban (which necessarily names the banned
  // calls) can't trip the ban itself — for the forbidden calls, so a future
  // edit can't reintroduce float coercion without a test failing immediately.
  // `import.meta.url` isn't a `file:` URL under Vite's test module graph, so
  // this resolves relative to the vitest process's cwd instead (the
  // `frontend/` directory `npm test` is run from).
  const sourcePath = join(process.cwd(), "src/lib/money.js");
  const source = readFileSync(sourcePath, "utf8");
  const codeOnly = source
    .replace(/\/\*[\s\S]*?\*\//g, "") // block comments, incl. JSDoc
    .replace(/^\s*\/\/.*$/gm, "") // whole-line `//` comments
    .replace(/[ \t]+\/\/.*$/gm, ""); // trailing `//` comments

  it("never calls Number(), parseFloat(), or parseInt()", () => {
    expect(codeOnly).not.toMatch(/\bNumber\(/);
    expect(codeOnly).not.toMatch(/\bparseFloat\(/);
    expect(codeOnly).not.toMatch(/\bparseInt\(/);
  });

  it("never touches the global Math object or .toFixed()", () => {
    expect(codeOnly).not.toMatch(/\bMath\./);
    expect(codeOnly).not.toMatch(/\.toFixed\(/);
  });

  it("never calls Intl.NumberFormat", () => {
    expect(codeOnly).not.toMatch(/\bIntl\.NumberFormat/);
  });
});
