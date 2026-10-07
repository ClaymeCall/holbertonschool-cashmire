<script>
  // Site-wide footer — extracted from the shared app shell (issue #104
  // componentization follow-up). Self-contained: no props, just the
  // site-wide link to /privacy required by issue #63 (AC-5) and the
  // API health link.
  import textureTile from "$lib/images/cashmere-texture-tile.webp";
</script>

<footer style="--texture-photo: url({textureTile})">
  <a href="/privacy">Privacy &amp; legal</a>
  <a href="/health">API health</a>
</footer>

<style>
  footer {
    /* Sticky footer: pushed to the bottom of a short page by consuming
       all free space in body's column flex (base.css); has no effect
       once content is taller than the viewport, where it flows below it
       as normal. */
    margin-top: auto;
    padding: var(--space-lg) var(--space-xl);
    border-top: 1px dashed var(--color-border-subtle);
    background-color: var(--color-surface);
    background-image: linear-gradient(
        var(--texture-overlay-tint),
        var(--texture-overlay-tint)
      ),
      var(--texture-photo);
    background-size: auto, 150px 150px;
    font-family: var(--font-mono);
    font-size: var(--font-size-sm);
    letter-spacing: var(--tracking-mono-label);
    text-transform: uppercase;
  }

  footer a {
    color: var(--color-primary);
  }
</style>
