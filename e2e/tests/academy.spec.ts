import { test, expect } from "@playwright/test";

test.describe("Academy — lesson index + Try in editor bridge", () => {
  test("navigates to academy and lists published lessons", async ({ page }) => {
    await page.goto("/academy");
    await expect(page.locator("h2")).toContainText("Academy");

    // Progress summary line should be visible (X / N published lessons)
    await expect(page.getByText(/Completed:.*published lesson/i)).toBeVisible();

    // At least 7 lesson cards present (all 7 lessons in the manifest)
    // Cards are either <a> (published, clickable) or <div> (planned)
    // The lesson titles are unique — use them to verify
    await expect(page.getByText(/What is an HMM\?/i)).toBeVisible();
    await expect(page.getByText(/Markov chains/i)).toBeVisible();
    await expect(page.getByText(/Forward algorithm/i)).toBeVisible();
    await expect(page.getByText(/Viterbi/i)).toBeVisible();
    await expect(page.getByText(/Baum-Welch/i)).toBeVisible();
    await expect(page.getByText(/Constrained topologies/i)).toBeVisible();
    await expect(page.getByText(/Non-homogeneous HMM \(NHMM\)/i)).toBeVisible();

    // Difficulty badges visible
    await expect(page.getByText(/Beginner/i).first()).toBeVisible();
    await expect(page.getByText(/Advanced/i).first()).toBeVisible();
  });

  test("opens a lesson and renders its content", async ({ page }) => {
    await page.goto("/academy");

    // Click on the Markov chains lesson card (anchor)
    await page.getByRole("link", { name: /Markov chains/i }).click();

    // URL should be /academy/lesson-2-markov-chains
    await expect(page).toHaveURL(/\/academy\/lesson-2-markov-chains/);

    // The lesson title is the H1
    await expect(page.locator("h1")).toContainText("Markov chains");

    // "Before 'hidden', just 'Markov'" heading from the lesson body (h2)
    await expect(
      page.getByRole("heading", { name: /Before.*hidden.*just.*Markov/i }),
    ).toBeVisible();

    // "The transition matrix" heading
    await expect(
      page.getByRole("heading", { name: /The transition matrix/i }),
    ).toBeVisible();

    // ProbabilitySimplex SVG is rendered (D3 appends text labels to the SVG)
    // The top vertex label is "→ s0 (prob 1)"
    await expect(page.getByText(/→ s0/)).toBeVisible();

    // "Try in editor" button visible (since this lesson has a preset)
    await expect(
      page.getByRole("button", { name: /Try in editor/i }),
    ).toBeVisible();

    // Mark as complete button visible
    await expect(
      page.getByRole("button", { name: /Mark as complete/i }),
    ).toBeVisible();
  });

  test("Try in editor bridge loads preset topology and navigates to /topology", async ({
    page,
  }) => {
    await page.goto("/academy/lesson-2-markov-chains");

    // Click "Try in editor"
    await page.getByRole("button", { name: /Try in editor/i }).click();

    // URL should be /topology
    await expect(page).toHaveURL(/\/topology/);

    // Give React Flow + the topology store a moment to render
    await page.waitForTimeout(500);

    // The preset has 3 states: sunny, cloudy, rainy
    // These appear as inline editable inputs inside React Flow nodes
    const sunnyInput = page.locator('input[value="sunny"]').first();
    const cloudyInput = page.locator('input[value="cloudy"]').first();
    const rainyInput = page.locator('input[value="rainy"]').first();

    await expect(sunnyInput).toBeVisible({ timeout: 5000 });
    await expect(cloudyInput).toBeVisible();
    await expect(rainyInput).toBeVisible();

    // The model name input in the side panel should show the preset name
    // (lesson_2_demo per the preset YAML in lessons/index.ts)
    await expect(page.locator('input[value="lesson_2_demo"]')).toBeVisible();
  });

  test("mark-complete toggle persists across page reloads", async ({ page }) => {
    await page.goto("/academy/lesson-1-what-is-an-hmm");

    // Initially "Mark as complete"
    const completeButton = page.getByRole("button", {
      name: /Mark as complete/i,
    });
    await expect(completeButton).toBeVisible();
    await completeButton.click();

    // Now should show "✓ Marked complete"
    await expect(
      page.getByRole("button", { name: /Marked complete/i }),
    ).toBeVisible();

    // Reload — the state persists via localStorage
    await page.reload();
    await expect(
      page.getByRole("button", { name: /Marked complete/i }),
    ).toBeVisible();

    // Click to un-mark
    await page.getByRole("button", { name: /Marked complete/i }).click();
    await expect(
      page.getByRole("button", { name: /Mark as complete/i }),
    ).toBeVisible();
  });

  test("lesson-16 model validity renders and shows the convergence curve", async ({ page }) => {
    await page.goto("/academy/lesson-16-model-validity");
    await page.waitForTimeout(400);
    await expect(page.getByRole("heading", { name: /Why this matters/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /When NOT to use an HMM/i })).toBeVisible();
    // The reused ProgressCurve renders an <svg>.
    expect(await page.locator("svg").count()).toBeGreaterThan(0);
  });

  test("planned lessons are not clickable", async ({ page }) => {
    await page.goto("/academy");

    // None of the lessons in the manifest are currently planned (all 7 were
    // promoted to published in the lessons 3-7 PR). The test guards future
    // additions: if a "planned" badge appears, the card should NOT be a link.
    const plannedBadges = page.getByText(/^Planned$/);
    const count = await plannedBadges.count();

    if (count > 0) {
      for (let i = 0; i < count; i++) {
        const badge = plannedBadges.nth(i);
        const card = badge.locator(
          "xpath=ancestor::*[contains(@class, 'rounded-md')][1]",
        );
        // The card should NOT be a link (`<a>`) — it should be a `<div>`
        const tag = await card.evaluate((el) => el.tagName.toLowerCase());
        expect(tag).not.toBe("a");
      }
    } else {
      // No planned lessons — test trivially passes; document the expected state
      test
        .info()
        .annotations.push({
          type: "note",
          description:
            "No planned lessons in the current manifest. Test ensures behavior if any are added later.",
        });
    }
  });
});
