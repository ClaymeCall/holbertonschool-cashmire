<script>
  // Minimal shared app shell — see docs/decisions/0001-shared-app-shell-layout.md.
  // Renders page content, then a footer with the site-wide link to /privacy
  // required by issue #63 (AC-5). Nothing else: no header, no nav, no theme
  // switcher, no global stylesheet.
  let { children } = $props();
</script>

{#if children}
  {@render children()}
{/if}

<footer>
  <a href="/privacy">Privacy &amp; legal</a>
  <a href="/health">API health</a>
</footer>

<style>
  footer {
    padding: 1rem 1.25rem;
    border-top: 1px solid #c8c8c8;
    font-size: 0.95rem;
  }

  footer a {
    color: #0b3d91;
  }

  footer a:focus-visible {
    outline: 3px solid #0b3d91;
    outline-offset: 2px;
  }
</style>
