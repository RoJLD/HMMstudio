import { test, expect } from "@playwright/test";
import { fileURLToPath } from "url";
import { dirname, resolve } from "path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const FIXTURE_PATH = resolve(__dirname, "../fixtures/data_3state.csv");

// Force video recording for this test regardless of global config.
test.use({
  video: "on",
  viewport: { width: 1280, height: 800 },
});

// Slow each action so the video is watchable.
const SLOW_MS = 800;

async function pause(page: import("@playwright/test").Page, ms = SLOW_MS) {
  await page.waitForTimeout(ms);
}

test.describe("Studio tour (records a video walkthrough)", () => {
  test("walkthrough: home → data → topology → fit → results", async ({ page }) => {
    test.setTimeout(120_000); // generous

    // ---- Scene 1: Home ----
    await page.goto("/");
    await pause(page, 1200);

    // Health check button — show it works
    const healthButton = page.getByRole("button", { name: /GET \/health/i });
    if (await healthButton.isVisible().catch(() => false)) {
      await healthButton.click();
      await pause(page, 1500);
    }

    // ---- Scene 2: Data upload ----
    await page.goto("/data");
    await pause(page, 1200);

    // Target the dropzone input by test id (see golden-path.spec.ts comment):
    // with a warehouse configured, `input[type=file].first()` would hit the
    // sidebar's warehouse-upload input instead, leaving the dataset unloaded
    // and the "Launch fit" button disabled later in this walkthrough.
    const fileInput = page.getByTestId("dataset-upload-input");
    await fileInput.setInputFiles(FIXTURE_PATH);
    // Wait for the local preview card to render (proves `current` was set).
    await expect(
      page.getByRole("heading", { name: /data_3state\.csv/i }),
    ).toBeVisible({ timeout: 10000 });
    await pause(page, 2000);

    // ---- Scene 3: Topology editor ----
    // Client-side nav (not page.goto): a reload would clear the in-memory
    // datasetStore and disable "Launch fit" in Scene 4. Only topologyStore
    // persists to localStorage.
    await page.getByRole("link", { name: "Topology editor" }).click();
    await expect(page).toHaveURL(/\/topology/);
    await pause(page, 1000);

    const addState = page.getByRole("button", { name: /\+ state/i });
    for (let i = 0; i < 3; i++) {
      await addState.click();
      await pause(page, 600);
    }
    await pause(page, 1500);

    // Toggle dark mode briefly (visual flair)
    const darkButton = page.getByRole("button", { name: /Dark/i }).first();
    if (await darkButton.isVisible().catch(() => false)) {
      await darkButton.click();
      await pause(page, 1500);
      const lightButton = page.getByRole("button", { name: /Light/i }).first();
      if (await lightButton.isVisible().catch(() => false)) {
        await lightButton.click();
        await pause(page, 1000);
      }
    }

    // ---- Scene 4: Fit launcher ----
    await page.getByRole("link", { name: "Fit", exact: true }).click();
    await expect(page).toHaveURL(/\/fit/);
    await pause(page, 1200);

    const launchButton = page.getByRole("button", { name: /Launch fit/i });
    await expect(launchButton).toBeEnabled({ timeout: 5000 });
    await pause(page, 800);
    await launchButton.click();

    // ---- Scene 5: Results ----
    await page.waitForURL(/\/results\/[a-f0-9-]+/i, { timeout: 15000 });
    await pause(page, 1000);

    // Wait for "done" status
    await expect(page.getByText(/done/i).first()).toBeVisible({ timeout: 30000 });
    await pause(page, 3000); // let viewer take in the heatmap + viterbi

    // ---- Scene 6: Academy peek ----
    await page.goto("/academy");
    await pause(page, 2000);

    // Hover over a couple of lesson cards to show variety
    await page.getByText(/Markov chains/i).first().hover();
    await pause(page, 1000);
    await page.getByText(/NHMM/i).first().hover();
    await pause(page, 1500);

    // End: back to home for a clean close
    await page.goto("/");
    await pause(page, 1500);
  });
});
