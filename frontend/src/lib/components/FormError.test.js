// Shared FormError component — introduced for issue #104 (frontend design
// system). Follows this project's existing conventions: @testing-library/svelte,
// no @testing-library/jest-dom (not installed).
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/svelte";
import FormError from "./FormError.svelte";

describe("FormError (#104)", () => {
  it("renders nothing when there are no messages", () => {
    const { container } = render(FormError, { props: { messages: [] } });
    expect(container.querySelector('[role="alert"]')).toBeNull();
  });

  it("renders a single message as plain text inside an alert", () => {
    render(FormError, { props: { messages: ["Incorrect email or password."] } });
    const alert = screen.getByRole("alert");
    expect(alert.textContent).toMatch(/incorrect email or password/i);
    expect(alert.querySelector("ul")).toBeNull();
  });

  it("renders multiple messages as a list inside the same alert", () => {
    render(FormError, {
      props: { messages: ["Enter a password.", "Passwords do not match."] },
    });
    const alert = screen.getByRole("alert");
    const items = alert.querySelectorAll("li");
    expect(items).toHaveLength(2);
    expect(items[0].textContent).toMatch(/enter a password/i);
    expect(items[1].textContent).toMatch(/passwords do not match/i);
  });
});
