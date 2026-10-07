<script>
  import { onMount } from "svelte";
  import { apiFetch } from "$lib/api";
  import heroImage from "$lib/images/cashmere-hero.webp";

  let status = "checking...";

  onMount(async () => {
    try {
      const data = await apiFetch("/api/health/");
      status = data.status;
    } catch (err) {
      status = "unreachable";
    }
  });
</script>

<section class="hero" style="--hero-image: url({heroImage})">
  <div class="hero-scrim">
    <h1>Cashmire</h1>
    <p class="tagline">Quiet luxury for your everyday budget.</p>
  </div>
</section>

<main>
  <p>API status: <code>{status}</code></p>
</main>

<style>
  .hero {
    background-image: linear-gradient(
        180deg,
        rgba(42, 23, 15, 0.45),
        rgba(42, 23, 15, 0.15)
      ),
      var(--hero-image);
    background-size: cover;
    background-position: center;
  }

  .hero-scrim {
    max-width: 60ch;
    margin: 0 auto;
    padding: var(--space-3xl) var(--space-xl);
  }

  h1 {
    font-size: 2.25rem;
    font-style: italic;
    font-weight: 300;
    color: var(--color-ivory);
  }

  .tagline {
    color: var(--color-ivory);
    font-size: 1.1rem;
  }

  main {
    max-width: 60ch;
    margin: 0 auto;
    padding: var(--space-2xl) var(--space-xl) var(--space-3xl);
  }
</style>
