import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { resolve } from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
      "@routes": resolve(__dirname, "src/routes"),
      "@utils": resolve(__dirname, "src/utils"),
      "@ui": resolve(__dirname, "src/ui"),
      "@assets": resolve(__dirname, "src/assets"),
    },
  },

  test: {
    name: "react",
    browser: {
      enabled: true,
      provider: "playwright",
      headless: true,
    },
    exclude: ["test/browser/**/*"],
  },
});
