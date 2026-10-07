<script>
  // Minimal shared app shell — see docs/decisions/0001-shared-app-shell-layout.md
  // and its amendment for issue #15. Renders the site-wide nav, then page
  // content, then the footer. The nav and footer themselves live in
  // `$lib/components/Navbar.svelte` and `Footer.svelte` (issue #104
  // componentization follow-up) — this file is just the shell that
  // composes them with each page's content and the document-wide
  // stylesheets. No global stylesheet beyond those, no theme switcher —
  // styling stays component-scoped (decision 0001 point 6).
  import "$lib/styles/tokens.css";
  import "$lib/styles/fonts.css";
  import "$lib/styles/base.css";
  import Navbar from "$lib/components/Navbar.svelte";
  import Footer from "$lib/components/Footer.svelte";

  let { children } = $props();
</script>

<Navbar />

{#if children}
  {@render children()}
{/if}

<Footer />
