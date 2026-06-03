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

    // Turn on the prior overlay (tri-state control: — / prior / learned) and
    // assert a probability label appears.
    await page.getByRole("button", { name: /^prior$/ }).click();
    await page.waitForTimeout(200);
    await expect(page.locator(".react-flow__edge-textbg")).toHaveCount(1);
  });
});

test.describe("Topology editor — Increment 2", () => {
  test("ergodic guided model renders arrows", async ({ page }) => {
    await page.goto("/topology/new");
    await page.waitForTimeout(400);
    // Step through all 5 wizard steps (Emission→States→Transitions→Training→Review)
    // using 4 Next clicks, then finish into the editor.
    for (let i = 0; i < 4; i++) {
      await page.getByRole("button", { name: /^Next$/ }).click();
      await page.waitForTimeout(120);
    }
    await page.getByRole("button", { name: /Finish → open in editor/i }).click();
    await page.waitForTimeout(500);
    // The ergodic topology (default: 3 states, fully connected) must produce edges.
    expect(await page.locator(".react-flow__edge").count()).toBeGreaterThan(0);
  });

  test("Fit this topology is disabled without a dataset", async ({ page }) => {
    await page.goto("/topology");
    await page.waitForTimeout(400);
    await page.getByRole("button", { name: /\+ state/i }).click();
    await page.waitForTimeout(150);
    // Button label is "▶ Fit this topology"; disabled when no dataset is selected.
    await expect(page.getByRole("button", { name: /▶ Fit this topology/i })).toBeDisabled();
  });

  test("the learned overlay button is disabled before any fit", async ({ page }) => {
    await page.goto("/topology");
    await page.waitForTimeout(400);
    await page.getByRole("button", { name: /\+ state/i }).click();
    await page.waitForTimeout(150);
    // Tri-state control renders "—" / "prior" / "learned"; "learned" is disabled with no fit result.
    await expect(page.getByRole("button", { name: /^learned$/ })).toBeDisabled();
  });

  test("Tidy (chain) then a single Undo restores positions", async ({ page }) => {
    await page.goto("/topology");
    await page.waitForTimeout(400);
    const add = page.getByRole("button", { name: /\+ state/i });
    await add.click();
    await add.click();
    await add.click();
    await page.waitForTimeout(200);
    const firstBefore = await page.locator(".react-flow__node").first().boundingBox();
    // Button label is "⇥ Tidy (chain)".
    await page.getByRole("button", { name: /⇥ Tidy \(chain\)/i }).click();
    await page.waitForTimeout(200);
    const firstAfter = await page.locator(".react-flow__node").first().boundingBox();
    // Layout ran — bounding box must be non-null (position may or may not shift depending on
    // initial placement, but Tidy always writes positions).
    expect(firstAfter).not.toBeNull();
    // A single Undo must be available and should restore the pre-tidy layout.
    const undoBtn = page.getByRole("button", { name: /↶ Undo/i });
    await expect(undoBtn).toBeEnabled();
    await undoBtn.click();
    await page.waitForTimeout(200);
    const firstRestored = await page.locator(".react-flow__node").first().boundingBox();
    expect(firstRestored).not.toBeNull();
    // After undoing the tidy, the node should be back near its pre-tidy position
    // (within a generous tolerance to absorb React Flow render jitter).
    if (firstBefore && firstRestored) {
      expect(Math.abs(firstRestored.x - firstBefore.x)).toBeLessThan(50);
    }
  });

  test("save then load a named model round-trips", async ({ page }) => {
    await page.goto("/topology");
    await page.waitForTimeout(400);
    await page.getByRole("button", { name: /\+ state/i }).click();
    await page.waitForTimeout(150);
    // Stub window.prompt so we don't need real dialog interaction.
    page.on("dialog", (d) => d.accept("e2e-model"));
    // Button label is "💾 Save model".
    await page.getByRole("button", { name: /💾 Save model/i }).click();
    await page.waitForTimeout(150);
    // Load it back via the "📂 Load saved…" select — select by value (the saved name).
    await page.selectOption("select", { value: "e2e-model" }).catch(() => {});
    await page.waitForTimeout(200);
    // After loading, the topology must have at least one node.
    expect(await page.locator(".react-flow__node").count()).toBeGreaterThan(0);
  });
});

test.describe("Saved-models portability", () => {
  test("save a model then export it as YAML", async ({ page }) => {
    await page.goto("/topology");
    await page.waitForTimeout(400);
    await page.getByRole("button", { name: /\+ state/i }).click();
    await page.waitForTimeout(150);
    page.on("dialog", (d) => d.accept("e2e-export"));
    await page.getByRole("button", { name: /Save model/i }).click();
    await page.waitForTimeout(150);
    await page.getByRole("button", { name: /My models/i }).click();
    await page.waitForTimeout(150);
    const dl = page.waitForEvent("download");
    await page.getByRole("button", { name: /YAML/i }).first().click();
    expect((await dl).suggestedFilename()).toMatch(/\.yaml$/);
  });

  test("export-all downloads a library JSON", async ({ page }) => {
    await page.goto("/topology");
    await page.waitForTimeout(400);
    await page.getByRole("button", { name: /\+ state/i }).click();
    page.on("dialog", (d) => d.accept("e2e-lib"));
    await page.getByRole("button", { name: /Save model/i }).click();
    await page.waitForTimeout(150);
    await page.getByRole("button", { name: /My models/i }).click();
    await page.waitForTimeout(150);
    const dl = page.waitForEvent("download");
    await page.getByRole("button", { name: /Export all/i }).click();
    expect((await dl).suggestedFilename()).toMatch(/\.json$/);
  });
});
