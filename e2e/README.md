# E2E tests (Playwright)

End-to-end browser tests that drive a running hmm-studio.

## Setup (first time)

```bash
cd e2e
npm install
npx playwright install chromium
```

`npx playwright install chromium` downloads the chromium browser binary
(~100 MB). Only needed once.

## Run

**Manual mode** — start the studio first, then run the tests:

```bash
# Terminal 1
cd ..
hmm-studio   # or .\start.bat

# Terminal 2
cd e2e
npm test
```

**Auto-start mode** — uncomment the `webServer` block in `playwright.config.ts`
to have Playwright start `hmm-studio` automatically. The shell needs the
hmm-studio venv active.

```bash
npm test                # headless
npm run test:headed     # see the browser
npm run test:debug      # step-through with the Playwright inspector
npm run report          # open the HTML report after a run
```

## What the tests cover

- `golden-path.spec.ts` — the full user workflow: home → data upload →
  topology editor → fit → results.
- `topology-editor.spec.ts` — undo/redo + YAML export.

These deliberately do NOT cover:
- The K-scan path (would require multiple parallel fits, slow).
- The Academy lessons (interactive but no data-flow assertions to make).
- WebSocket streaming (covered by Python unit tests).
- Dark mode toggle (visual regression — needs screenshots, future work).

## Accessibility audit

`accessibility.spec.ts` runs axe-core against the main pages and reports
violations.

**Default mode** (the one that runs in CI) — warns and only fails on
catastrophic regressions (>5 critical violations on a page):

```bash
npx playwright test accessibility.spec.ts
```

**Strict mode** — fails on any critical or serious violation. Use this when
working on a11y improvements:

```bash
STRICT_A11Y=1 npx playwright test accessibility.spec.ts
```

Pages audited:
- `/` (Home)
- `/data` (Data upload)
- `/topology` (Topology editor — known SVG-heavy, expect some violations)
- `/fit` (Fit launcher)
- `/academy` (Academy index)
- `/academy/lesson-1-what-is-an-hmm` (lesson with D3 demo)
- `/academy/lesson-2-markov-chains` (lesson with D3 demo)

Severity policy:
- **Critical**: page is unusable for some users (e.g., button with no accessible name). Always fail above 5.
- **Serious**: significant barrier (e.g., low contrast). Logged; fails in strict mode.
- **Moderate / Minor**: opportunistic fixes; not in CI.

If the dark-mode broad CSS overrides cause contrast violations, they appear in this audit. They are tracked in the README "known issues" section.

## Recording a tour video

`tour-recording.spec.ts` runs a slowed-down walkthrough of the studio
(home → data → topology → fit → results → academy) and records a video
via Playwright's built-in video capture.

```bash
# Make sure the studio is running first (or use the auto-start mode)
npx playwright test tour-recording.spec.ts
```

The WebM is written to `test-results/<test-name>/video.webm` (Playwright
names it deterministically once `video: "on"` is set in the test).

Convert to GIF or MP4 with ffmpeg — see [`scripts/convert-tour-to-gif.md`](scripts/convert-tour-to-gif.md).

The video is ~30-45 seconds; final GIF lands around 3-6 MB at 720p / 12 fps.

**Note:** this test is intentionally not part of the CI suite — it's a
manual artifact generator. Add `@tour` to the test name and grep-filter
it out of CI if you wire it up later.

## CI

`.github/workflows/e2e.yml` runs these tests in headless Chromium on each
push. It starts the studio via `python scripts/build_frontend.py && hmm-studio &`
before running playwright.

## Adding a test

1. Drop a new `.spec.ts` under `tests/`.
2. Use the same describe/test pattern; `baseURL` is configured in
   `playwright.config.ts` so you can `page.goto("/your-route")`.
3. Prefer `getByRole`, `getByText`, `getByLabel` over CSS selectors —
   resilient to refactors.
