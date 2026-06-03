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

test.describe("Topology editor — drag + prior preview", () => {
  test("a dragged state persists across reload", async ({ page }) => {
    await page.goto("/topology");
    await page.waitForTimeout(500);
    await page.getByRole("button", { name: /\+ state/i }).click();
    await page.waitForTimeout(200);

    const node = page.locator(".react-flow__node").first();
    const before = await node.boundingBox();
    if (!before) throw new Error("node not found");

    // Drag the node by ~150px.
    await page.mouse.move(before.x + before.width / 2, before.y + before.height / 2);
    await page.mouse.down();
    await page.mouse.move(before.x + 150, before.y + 80, { steps: 10 });
    await page.mouse.up();
    await page.waitForTimeout(200);

    const after = await node.boundingBox();
    expect(after!.x).toBeGreaterThan(before.x + 50);

    // Reload — the position must persist.
    await page.reload();
    await page.waitForTimeout(500);
    const reloaded = await page.locator(".react-flow__node").first().boundingBox();
    expect(Math.abs(reloaded!.x - after!.x)).toBeLessThan(40);
  });

  test("prior preview toggle puts probability labels on edges", async ({ page }) => {
    await page.goto("/topology");
    await page.waitForTimeout(500);

    // Two states + an edge between them.
    const addState = page.getByRole("button", { name: /\+ state/i });
    await addState.click();
    await addState.click();
    await page.waitForTimeout(200);

    // Draw an edge: drag from the first node's source handle to the second's target.
    const handles = page.locator(".react-flow__handle-right");
    const target = page.locator(".react-flow__handle-left").nth(1);
    const from = await handles.first().boundingBox();
    const to = await target.boundingBox();
    if (from && to) {
      await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2);
      await page.mouse.down();
      await page.mouse.move(to.x + to.width / 2, to.y + to.height / 2, { steps: 8 });
      await page.mouse.up();
      await page.waitForTimeout(200);
    }

    // Turn on the preview and assert a probability label appears.
    await page.getByText("prior preview").click();
    await page.waitForTimeout(200);
    await expect(page.locator(".react-flow__edge-textbg")).toHaveCount(1);
  });
});
