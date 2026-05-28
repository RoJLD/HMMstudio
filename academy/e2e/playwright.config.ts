import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  use: { baseURL: "http://localhost:4173" },
  webServer: {
    // Build then preview the production bundle (serves dist/config.js with the
    // committed default: studioUrl "" => studio button hidden).
    command: "npm --prefix .. run build && npm --prefix .. run preview",
    url: "http://localhost:4173/academy",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
