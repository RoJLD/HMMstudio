import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

/**
 * Accessibility audit using axe-core.
 *
 * Default mode (warns, doesn't fail): runs axe on each main page, prints any
 * serious/critical violations to the test output for review.
 *
 * Strict mode (fails on violations): set STRICT_A11Y=1.
 *   STRICT_A11Y=1 npx playwright test accessibility.spec.ts
 *
 * Rule of thumb: a violation with impact "critical" means the page is unusable
 * for some users (e.g., a button with no accessible name). "Serious" means
 * significant barrier but workable (e.g., low color contrast). "Minor" and
 * "moderate" are filtered out — they get fixed opportunistically.
 */

const STRICT = process.env.STRICT_A11Y === "1";
const IMPACT_LEVELS = ["critical", "serious"] as const;

type PageSpec = { path: string; name: string };

const PAGES: PageSpec[] = [
  { path: "/", name: "Home" },
  { path: "/data", name: "Data upload" },
  { path: "/topology", name: "Topology editor" },
  { path: "/fit", name: "Fit launcher" },
  { path: "/academy", name: "Academy index" },
  { path: "/academy/lesson-1-what-is-an-hmm", name: "Academy lesson 1" },
  { path: "/academy/lesson-2-markov-chains", name: "Academy lesson 2 (D3 demo)" },
];

test.describe("Accessibility audit (axe-core)", () => {
  for (const { path, name } of PAGES) {
    test(`${name} (${path}) — critical + serious violations`, async ({ page }) => {
      await page.goto(path);
      // Let any animated SVG / React Flow finish settling
      await page.waitForTimeout(500);

      const result = await new AxeBuilder({ page })
        // Standard WCAG ruleset — exclude experimental and best-practice rules
        // by default; users opt in to those via tags
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
        .analyze();

      const relevant = result.violations.filter(
        (v) => IMPACT_LEVELS.includes(v.impact as (typeof IMPACT_LEVELS)[number]),
      );

      if (relevant.length > 0) {
        const summary = relevant.map((v) => ({
          id: v.id,
          impact: v.impact,
          help: v.help,
          nodes: v.nodes.length,
          helpUrl: v.helpUrl,
        }));
        // Always log so reports show context
        console.warn(
          `[a11y] ${name}: ${relevant.length} ${IMPACT_LEVELS.join("/")} violation(s)`,
        );
        for (const v of summary) {
          console.warn(`  - [${v.impact}] ${v.id} (${v.nodes} node(s)): ${v.help}`);
          console.warn(`    See: ${v.helpUrl}`);
        }
      }

      if (STRICT) {
        expect(
          relevant,
          `axe found ${relevant.length} critical/serious violation(s) on ${name}`,
        ).toEqual([]);
      } else {
        // Non-strict: only fail on >5 critical violations (catastrophic regression)
        const critical = relevant.filter((v) => v.impact === "critical");
        expect(
          critical.length,
          `${name}: ${critical.length} critical a11y violations (threshold 5)`,
        ).toBeLessThanOrEqual(5);
      }
    });
  }

  // One synthetic test that ALWAYS runs strict on the Home page — a smoke-level
  // safety net. The Home page is the simplest page and should have zero
  // critical violations regardless of mode.
  test("Home page has zero critical accessibility violations (always strict)", async ({
    page,
  }) => {
    await page.goto("/");
    await page.waitForTimeout(200);

    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag21a"])
      .analyze();

    const critical = result.violations.filter((v) => v.impact === "critical");
    if (critical.length > 0) {
      console.warn("[a11y] Home critical violations:");
      for (const v of critical) {
        console.warn(`  - ${v.id} (${v.nodes.length} nodes): ${v.help}`);
      }
    }
    expect(critical).toEqual([]);
  });
});
