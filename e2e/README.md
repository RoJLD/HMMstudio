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
