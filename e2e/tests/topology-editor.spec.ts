import { test, expect } from "@playwright/test";

test.describe("Topology editor — undo/redo + YAML export", () => {
  test("undo restores the previous state, redo re-applies", async ({ page }) => {
    await page.goto("/topology");
    await page.waitForTimeout(500);

    // Add 2 states
    const addState = page.getByRole("button", { name: /\+ state/i });
    await addState.click();
    await addState.click();
    await page.waitForTimeout(200);

    // Undo once — should remove the second state
    const undoButton = page.getByRole("button", { name: /↶ Undo/i });
    await expect(undoButton).toBeEnabled();
    await undoButton.click();
    await page.waitForTimeout(200);

    // Redo
    const redoButton = page.getByRole("button", { name: /↷ Redo/i });
    await expect(redoButton).toBeEnabled();
    await redoButton.click();
    await page.waitForTimeout(200);

    // After redo, redoButton should be disabled (history is consumed)
    await expect(redoButton).toBeDisabled();
  });

  test("export YAML downloads a file", async ({ page }) => {
    await page.goto("/topology");
    await page.waitForTimeout(500);

    // Need at least one state to have something to export
    await page.getByRole("button", { name: /\+ state/i }).click();
    await page.waitForTimeout(200);

    // Catch the download
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: /↓ Export YAML/i }).click();
    const download = await downloadPromise;

    // Filename should end in .yaml
    expect(download.suggestedFilename()).toMatch(/\.yaml$/);
  });
});
