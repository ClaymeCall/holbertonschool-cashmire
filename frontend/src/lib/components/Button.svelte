<script>
  // Shared button — issue #104. Replaces the near-identical `<button>` +
  // <style> block that login/+page.svelte and register/+page.svelte each
  // defined on their own.
  import "../styles/tokens.css";

  /**
   * @typedef {Object} Props
   * @property {"primary" | "secondary"} [variant]
   * @property {"button" | "submit"} [type]
   * @property {boolean} [disabled]
   * @property {import("svelte").Snippet} children
   */

  /** @type {Props & Record<string, unknown>} */
  let { variant = "primary", type = "button", disabled = false, children, ...rest } =
    $props();
</script>

<button {type} {disabled} class={variant} {...rest}>
  {@render children?.()}
</button>

<style>
  /* Pill-shaped, Camel fill, Ivory text — docs/specs/issue-104-cashmire-design-system.md
     "Components". `--color-cta-bg` is a deliberately deeper Camel than the
     decorative `--color-camel` token; see tokens.css's header comment for
     why (plain Camel fails contrast with Ivory text). */
  button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.4rem;
    font-family: var(--font-body);
    font-size: var(--font-size-base);
    font-weight: 500;
    padding: var(--space-sm) var(--space-xl);
    border-radius: var(--radius-full);
    border: 1px solid var(--color-cta-bg);
    cursor: pointer;
    transition: background-color var(--motion-duration) var(--motion-ease),
      color var(--motion-duration) var(--motion-ease),
      opacity var(--motion-duration) var(--motion-ease);
  }

  button:disabled {
    cursor: default;
    opacity: 0.65;
  }

  button.primary {
    background: var(--color-cta-bg);
    color: var(--color-cta-text);
  }

  button.primary:hover:not(:disabled) {
    background: var(--color-mocha);
    border-color: var(--color-mocha);
  }

  button.secondary {
    background: transparent;
    color: var(--color-cta-bg);
  }

  button.secondary:hover:not(:disabled) {
    background: var(--color-oatmeal);
  }

  button:focus-visible {
    outline: var(--focus-ring-width) solid var(--focus-ring-color);
    outline-offset: 2px;
  }
</style>
