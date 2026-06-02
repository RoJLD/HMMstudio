import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Separate from vite.config.ts on purpose: the app build config (manualChunks,
// proxy, version inject) is irrelevant to unit tests. jsdom is used so modules
// that import `reactflow` (e.g. MarkerType) resolve cleanly.
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
