import { test, expect } from "@playwright/test";

/**
 * Phase B.10c — Data warehouse E2E tests.
 *
 * Assumes the server is started with HMM_STUDIO_WAREHOUSE_PATH pointing at
 * ``e2e/fixtures/warehouse``. See e2e/README.md "Data warehouse fixture".
 *
 * The fixture directory contains:
 *   - btc_2024.csv          (51 rows, 3 cols) + btc_2024.csv.hmm.yaml sidecar
 *   - eth_2024.csv          (30 rows, 2 cols)
 *   - archive/legacy_2023.csv (20 rows, 2 cols)
 *
 * Tests do NOT touch the Settings UI (separate dispatch). Warehouse is
 * env-var-configured at server startup.
 */

/** The canonical sidecar contents that ship with the fixture. The "edit"
 *  test mutates the sidecar then restores it via this constant in
 *  ``test.afterEach``. If a test crashes mid-run, the operator can rewrite
 *  ``btc_2024.csv.hmm.yaml`` to match this object (see e2e/README.md). */
const ORIGINAL_BTC_SIDECAR = {
  schema_version: 1,
  name: "BTC daily 2024",
  description: "Daily BTC log returns with realized vol",
  notes: "Vol on 20-day window",
  columns: [
    { name: "timestamp", role: "index", dtype: "datetime" },
    { name: "log_return", role: "observation", dtype: "float64" },
    { name: "vol", role: "covariate", dtype: "float64" },
  ],
};

test.describe("Warehouse — sidebar, preview, sidecar, promote", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/data");
    // Wait for the warehouse sidebar to render (depends on /api/warehouse).
    await expect(
      page.getByRole("heading", { name: /^Warehouse$/i }),
    ).toBeVisible({ timeout: 10_000 });
  });

  test("warehouse_sidebar_displays_files", async ({ page }) => {
    // All three fixture filenames visible
    await expect(page.getByText("btc_2024.csv", { exact: true })).toBeVisible();
    await expect(page.getByText("eth_2024.csv", { exact: true })).toBeVisible();
    await expect(
      page.getByText("legacy_2023.csv", { exact: true }),
    ).toBeVisible();

    // Subdirectory header "archive/" should appear (uppercase via CSS, lowercase in DOM)
    await expect(page.getByText("archive/", { exact: true })).toBeVisible();

    // Format badges show "CSV" (uppercase via CSS). We assert at least 3
    // distinct CSV badges by scoping to the sidebar's badge elements.
    const csvBadges = page.locator("span").filter({ hasText: /^csv$/i });
    await expect(csvBadges).toHaveCount(3);

    // Sidecar marker ★ for btc_2024.csv (the only file with a sidecar)
    await expect(page.getByTitle("Has sidecar metadata")).toHaveCount(1);
  });

  test("select_dataset_shows_preview", async ({ page }) => {
    // Click the btc_2024.csv entry in the sidebar
    await page.getByRole("button", { name: /btc_2024\.csv/i }).click();

    // The DatasetPreviewCard header shows "<rel_path>" as the filename;
    // for warehouse files it's the rel_path "btc_2024.csv".
    await expect(
      page.getByRole("heading", { name: "btc_2024.csv" }),
    ).toBeVisible({ timeout: 10_000 });

    // "51 rows × 3 cols" line from DatasetPreviewCard
    await expect(page.getByText(/51 rows .* 3 cols/i)).toBeVisible();

    // Column headers visible inside the preview table
    await expect(
      page.locator("th").filter({ hasText: "timestamp" }),
    ).toBeVisible();
    await expect(
      page.locator("th").filter({ hasText: "log_return" }),
    ).toBeVisible();
    await expect(page.locator("th").filter({ hasText: "vol" })).toBeVisible();

    // At least one data row — the first timestamp value
    await expect(page.getByText("2024-01-01").first()).toBeVisible();
  });

  test.describe("sidecar edit roundtrip", () => {
    // Restore the original sidecar after EACH test in this describe — even
    // on failure — so the fixture stays deterministic. Uses the same API
    // the UI hits (PUT /api/warehouse/{rel_path}/meta).
    test.afterEach(async ({ request }) => {
      const r = await request.put("/api/warehouse/btc_2024.csv/meta", {
        data: ORIGINAL_BTC_SIDECAR,
      });
      // Soft check — log if the restore failed but don't fail the test (it
      // already may have failed for other reasons; the operator will see
      // the warning in the report).
      if (!r.ok()) {
        // eslint-disable-next-line no-console
        console.warn(
          `[warehouse.spec] sidecar restore failed: ${r.status()} ${await r.text()}`,
        );
      }
    });

    test("edit_sidecar_persists", async ({ page }) => {
      // Open btc_2024.csv preview
      await page.getByRole("button", { name: /btc_2024\.csv/i }).click();

      // The sidecar's "name" is rendered as plain text under "Name:".
      // Wait for the sidecar block to populate.
      await expect(page.getByText("BTC daily 2024")).toBeVisible({
        timeout: 10_000,
      });

      // Click [Edit sidecar]
      await page.getByRole("button", { name: /Edit sidecar/i }).click();

      // The description textarea is the second textarea (after Notes is fourth).
      // Easier: find by associated label text "Description".
      const descLabel = page.locator("label").filter({ hasText: "Description" });
      const descTextarea = descLabel.locator("textarea");
      const NEW_DESCRIPTION = "EDITED by warehouse.spec — should be reverted";
      await descTextarea.fill(NEW_DESCRIPTION);

      // Save
      await page.getByRole("button", { name: /Save sidecar/i }).click();

      // After save, view-mode shows the new description
      await expect(page.getByText(NEW_DESCRIPTION)).toBeVisible({
        timeout: 10_000,
      });

      // Reload the page — the new description should persist (sidecar on disk)
      await page.reload();
      await page.getByRole("button", { name: /btc_2024\.csv/i }).click();
      await expect(page.getByText(NEW_DESCRIPTION)).toBeVisible({
        timeout: 10_000,
      });
      // (test.afterEach restores the original sidecar)
    });
  });

  test("use_for_fit_navigates_to_fit_with_dataset", async ({ page }) => {
    // Open btc_2024.csv preview
    await page.getByRole("button", { name: /btc_2024\.csv/i }).click();
    await expect(
      page.getByRole("heading", { name: "btc_2024.csv" }),
    ).toBeVisible({ timeout: 10_000 });

    // Click [Use for fit →]
    await page.getByRole("button", { name: /Use for fit/i }).click();

    // URL becomes /fit
    await page.waitForURL(/\/fit$/, { timeout: 10_000 });
    await expect(page.locator("h2")).toContainText("Fit");

    // FitPage Status row for Dataset shows the promoted filename.
    // promote_warehouse_dataset() stores it as full.name -> "btc_2024.csv".
    // The row reads: "btc_2024.csv (51 × 3)".
    await expect(
      page.getByText(/btc_2024\.csv\s*\(51\s*[×x]\s*3\)/i),
    ).toBeVisible({ timeout: 10_000 });
  });
});
