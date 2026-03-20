import { fileURLToPath, URL } from "node:url";

import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      app: fileURLToPath(new URL("./src/app", import.meta.url)),
      components: fileURLToPath(new URL("./src/components", import.meta.url)),
      features: fileURLToPath(new URL("./src/features", import.meta.url)),
      i18n: fileURLToPath(new URL("./src/i18n", import.meta.url)),
      lib: fileURLToPath(new URL("./src/lib", import.meta.url)),
      services: fileURLToPath(new URL("./src/services", import.meta.url)),
      styles: fileURLToPath(new URL("./src/styles", import.meta.url)),
      theme: fileURLToPath(new URL("./src/theme", import.meta.url)),
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: true,
    exclude: ["e2e/**", "node_modules/**"],
    coverage: {
      reporter: ["text", "html"],
    },
  },
});
