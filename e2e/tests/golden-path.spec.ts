import { test, expect } from "@playwright/test";
import { fileURLToPath } from "url";
import { dirname, resolve } from "path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const FIXTURE_PATH = resolve(__dirname, "../fixtures/data_3state.csv");

test.describe("Golden path: home → data → topology → fit → results", () => {
  test("complete workflow lands on results with a finite log-likelihood", async ({
    page,
  }) => {
    // ---- 1. Home page + health check ----
    await page.goto("/");
    await expect(page.locator("h2")).toContainText("Welcome", {
      ignoreCase: true,
    });

    // Click the health-check button
    const healthButton = page.getByRole("button", { name: /GET \/health/i });
    await healthButton.click();
    await expect(page.getByText(/Backend says:/i)).toBeVisible({
      timeout: 5000,
    });
    await expect(page.locator("code").filter({ hasText: "ok" })).toBeVisible();

    // ---- 2. Data upload ----
    await page.goto("/data");
    await expect(page.locator("h2")).toContainText("Data");

    // Trigger the dropzone's hidden file input by uploading directly.
    // Target it by test id, not `input[type=file].first()`: when a warehouse
    // is configured (HMM_STUDIO_WAREHOUSE_PATH set, as in CI), the sidebar's
    // "Upload to warehouse" input is first in the DOM, so `.first()` would
    // mis-route the upload into the warehouse instead of the local dataset
    // flow — leaving `current` unset (no preview card) and polluting the
    // warehouse fixture for the warehouse spec.
    const fileInput = page.getByTestId("dataset-upload-input");
    await fileInput.setInputFiles(FIXTURE_PATH);

    // Preview card appears
    await expect(page.getByText(/data_3state\.csv/i)).toBeVisible({
      timeout: 10000,
    });
    await expect(page.getByText(/24 rows/i)).toBeVisible();

    // ---- 3. Topology editor ----
    // Navigate via the nav link (client-side routing), NOT page.goto(): a full
    // reload would reset the in-memory datasetStore (only topologyStore is
    // persisted to localStorage), dropping the dataset we just uploaded and
    // leaving "Launch fit" disabled on the Fit page.
    await page.getByRole("link", { name: "Topology editor" }).click();
    await expect(page).toHaveURL(/\/topology/);

    // Click "+ state" 3 times to create 3 nodes
    const addStateButton = page.getByRole("button", { name: /\+ state/i });
    await addStateButton.click();
    await addStateButton.click();
    await addStateButton.click();
    // Give React Flow a beat to render
    await page.waitForTimeout(500);

    // ---- 4. Fit launcher ----
    await page.getByRole("link", { name: "Fit", exact: true }).click();
    await expect(page).toHaveURL(/\/fit/);
    await expect(page.locator("h2")).toContainText("Fit");

    // Status rows: scope to the exact status labels (the word "Topology" also
    // appears in the nav link "Topology editor" and the page description, so
    // an unscoped /Topology/i regex hits 3 elements under strict mode).
    await expect(page.getByText("Topology", { exact: true })).toBeVisible();
    await expect(page.getByText("Dataset", { exact: true })).toBeVisible();

    // Launch fit button enabled — click it
    const launchButton = page.getByRole("button", { name: /Launch fit/i });
    await expect(launchButton).toBeEnabled({ timeout: 5000 });
    await launchButton.click();

    // ---- 5. Results page ----
    // Wait for redirect to /results/:jobId
    await page.waitForURL(/\/results\/[a-f0-9-]+/i, { timeout: 15000 });
    await expect(page.locator("h2")).toContainText("Results");

    // Poll for status "done" (the page auto-updates)
    await expect(page.getByText(/done/i).first()).toBeVisible({
      timeout: 30000,
    });

    // log-likelihood should be a number (not "—" or NaN)
    const logLikText = await page
      .locator("text=/^-?\\d+\\.\\d+$/")
      .first()
      .textContent({ timeout: 10000 });
    expect(logLikText).not.toBeNull();
    expect(Number.isFinite(parseFloat(logLikText!))).toBe(true);

    // Transmat heatmap rendered (an SVG with class .block on the transmat card)
    // We just check that an SVG is present somewhere in the page content section.
    await expect(page.locator("svg").first()).toBeVisible();
  });
});
