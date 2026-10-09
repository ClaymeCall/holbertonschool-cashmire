import { sveltekit } from "@sveltejs/kit/vite";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest-setup.js"],
  },
  // Without this, Vite resolves Svelte's server-rendering build during
  // `vitest run` ("mount(...) is not available on the server"), because
  // @sveltejs/kit/vite's SSR-aware resolution wins by default outside a
  // real server/build context.
  resolve: process.env.VITEST ? { conditions: ["browser"] } : undefined,
});
