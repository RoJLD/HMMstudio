import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config for hmm-studio E2E tests.
 *
 * The tests assume hmm-studio is running at http://127.0.0.1:8000.
 *
 * LOCAL: launch the studio manually (`hmm-studio` or `.\start.bat`), then
 *        `cd e2e && npm install && npm test`.
 *
 * CI:    the GitHub Actions workflow (.github/workflows/e2e.yml) starts the
 *        server in the background before running playwright. Playwright's
 *        webServer config below is OPTIONAL — uncomment only if you want
 *        local runs to auto-start the server (requires the studio venv to
 *        be active in the shell that runs `npm test`).
 */

const BASE_URL = process.env.E2E_BASE_URL ?? "http://127.0.0.1:8000";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false, // backend has shared SQLite, serial is safer
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: BASE_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  // webServer: {
  //   command: "hmm-studio",
  //   url: "http://127.0.0.1:8000/health",
  //   reuseExistingServer: !process.env.CI,
  //   timeout: 60_000,
  // },
});
