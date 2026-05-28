import { test, expect } from "@playwright/test";

test.describe("HMM Academy standalone smoke", () => {
  test("root redirects to /academy and lists lessons", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/academy$/);
    // A few representative lesson titles (heading role to avoid card-desc matches)
    await expect(
      page.getByRole("heading", { name: /What is an HMM\?/i }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: /Markov chains/i }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: /Viterbi/i }),
    ).toBeVisible();
  });

  test("opens a lesson and renders its body", async ({ page }) => {
    await page.goto("/academy");
    await page.getByRole("link", { name: /Markov chains/i }).click();
    await expect(page).toHaveURL(/\/academy\/lesson-2-markov-chains/);
    await expect(
      page.getByRole("heading", { level: 1, name: /Markov chains/i }),
    ).toBeVisible();
  });

  test("studio button is hidden when no studioUrl configured", async ({
    page,
  }) => {
    // lesson-2 ships a presetTopologyYaml; with studioUrl "" the link must NOT render.
    await page.goto("/academy/lesson-2-markov-chains");
    await expect(
      page.getByRole("link", { name: /Open in HMM Studio/i }),
    ).toHaveCount(0);
  });

  test("mark-complete persists across reload (localStorage store works)", async ({
    page,
  }) => {
    await page.goto("/academy/lesson-1-what-is-an-hmm");
    await page.getByRole("button", { name: /Mark as complete/i }).click();
    await expect(
      page.getByRole("button", { name: /Marked complete/i }),
    ).toBeVisible();
    await page.reload();
    await expect(
      page.getByRole("button", { name: /Marked complete/i }),
    ).toBeVisible();
  });
});
