// Shared TextField component — introduced for issue #104 (frontend design
// system). Follows this project's existing conventions: @testing-library/svelte,
// no @testing-library/jest-dom (not installed).
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/svelte";
import TextField from "./TextField.svelte";

describe("TextField (#104)", () => {
  it("associates the label with the input via id, and reflects type/required/disabled", () => {
    render(TextField, {
      props: {
        id: "email",
        label: "Email",
        type: "email",
        value: "",
        required: true,
      },
    });

    const input = screen.getByLabelText("Email");
    expect(input.tagName).toBe("INPUT");
    expect(input.getAttribute("type")).toBe("email");
    expect(input.hasAttribute("required")).toBe(true);
    expect(input.hasAttribute("disabled")).toBe(false);
  });

  it("renders an optional hint", () => {
    render(TextField, {
      props: {
        id: "password",
        label: "Password",
        type: "password",
        value: "",
        hint: "At least 8 characters.",
      },
    });

    expect(screen.getByText("At least 8 characters.")).toBeTruthy();
  });
});
