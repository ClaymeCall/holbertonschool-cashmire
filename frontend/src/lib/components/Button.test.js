// Shared Button component — introduced for issue #104 (frontend design
// system). Follows this project's existing conventions: @testing-library/svelte,
// no @testing-library/jest-dom (not installed), `createRawSnippet` for the
// Svelte 5 `children` snippet prop (see frontend/src/routes/layout.test.js).
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import { createRawSnippet } from "svelte";
import Button from "./Button.svelte";

/** @param {string} text */
const textSnippet = (text) =>
  createRawSnippet(() => ({
    render: () => `<span>${text}</span>`,
  }));

describe("Button (#104)", () => {
  it("renders its content as a type=button, primary-variant element by default", () => {
    render(Button, { props: { children: textSnippet("Save") } });
    const button = screen.getByRole("button", { name: "Save" });
    expect(button.getAttribute("type")).toBe("button");
    expect(button.classList.contains("primary")).toBe(true);
  });

  it("supports the secondary variant and a submit type", () => {
    render(Button, {
      props: {
        children: textSnippet("Cancel"),
        variant: "secondary",
        type: "submit",
      },
    });
    const button = screen.getByRole("button", { name: "Cancel" });
    expect(button.getAttribute("type")).toBe("submit");
    expect(button.classList.contains("secondary")).toBe(true);
  });

  it("sets the disabled attribute when disabled", () => {
    render(Button, { props: { children: textSnippet("Go"), disabled: true } });
    const button = screen.getByRole("button", { name: "Go" });
    expect(button.hasAttribute("disabled")).toBe(true);
  });

  it("forwards extra attributes such as onclick when enabled", async () => {
    const onclick = vi.fn();
    render(Button, { props: { children: textSnippet("Go"), onclick } });

    await fireEvent.click(screen.getByRole("button", { name: "Go" }));
    expect(onclick).toHaveBeenCalledTimes(1);
  });
});
