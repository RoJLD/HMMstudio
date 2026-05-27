# Parameter help tooltips — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A click-popover `?` next to each configuration parameter that shows a concise explanation and, where relevant, a deep link to the matching Academy lesson.

**Architecture:** A single reusable `<HelpTip paramKey="...">` component (hand-rolled click popover, no new dependency) fed by one `paramHelp` content registry. Wired into every surface that has model/fit parameters: the topology editor `SidePanel`, the `FitPage` (K-scan), and the `ComparePage`. Copy lives only in the registry.

**Tech Stack:** React + react-router (`Link`) + Tailwind. No JS test runner exists, so correctness is validated by `npm run build` (strict `tsc`) + manual check.

**Spec:** `docs/specs/2026-05-27-parameter-help-tooltips.md`.

**Decisions resolved here (spec open questions):**
- **Q1 (Data-prep params):** the Data page is upload + warehouse browsing — it has **no** model/fit parameters. So "all input surfaces" = editor `SidePanel` + `FitPage` + `ComparePage`. Data page is N/A (nothing to annotate).
- **Q2 (`emission.type` link):** single overview entry → `lesson-1-what-is-an-hmm`.
- **Q3 (popover impl):** hand-rolled, no dependency; an `align` prop ("left" extends right, "right" extends left) handles the right-edge `SidePanel` vs the wide content pages.

## File Structure

- Create: `src/hmm_studio/frontend/src/components/help/paramHelp.ts` — `ParamHelpEntry` type + `PARAM_HELP` registry.
- Create: `src/hmm_studio/frontend/src/components/help/HelpTip.tsx` — the `?` button + popover.
- Modify: `src/hmm_studio/frontend/src/components/topology/SidePanel.tsx` — `Row` gains `paramKey`; pass keys.
- Modify: `src/hmm_studio/frontend/src/pages/FitPage.tsx` — `?` on seed + k_min/k_max.
- Modify: `src/hmm_studio/frontend/src/pages/ComparePage.tsx` — `?` on emission families, n_mix, k_min/k_max, seed.
- Modify: `CHANGELOG.md`.

All frontend paths are under the repo at `C:\Users\rdenis\VScode\Tools\hmm_studio`. Run `npm` from `src/hmm_studio/frontend`.

---

### Task 1: HelpTip component + paramHelp registry

**Files:**
- Create: `src/hmm_studio/frontend/src/components/help/paramHelp.ts`
- Create: `src/hmm_studio/frontend/src/components/help/HelpTip.tsx`

- [ ] **Step 1: Create the registry**

Create `src/hmm_studio/frontend/src/components/help/paramHelp.ts`:

```ts
export interface ParamHelpEntry {
  title: string;
  body: string;
  lesson?: { id: string; label: string };
}

// Single source of truth for parameter help copy. Keys are stable param ids
// referenced by <HelpTip paramKey="...">. Concepts shared across surfaces
// (seed, K range, n_mix) reuse one entry.
export const PARAM_HELP: Record<string, ParamHelpEntry> = {
  "topology.name": {
    title: "Model name",
    body: "A label for this topology. Saved in result bundles and summaries; it has no effect on the fit.",
  },
  "emission.type": {
    title: "Emission type",
    body: "The distribution each hidden state emits. Gaussian / GMM for continuous data, Multinomial for discrete symbols, Poisson for counts.",
    lesson: { id: "lesson-1-what-is-an-hmm", label: "What is an HMM?" },
  },
  "emission.n_features": {
    title: "Number of features",
    body: "How many observed columns each emission models (the dimensionality of X). Must match your dataset's feature columns.",
    lesson: { id: "lesson-13-choosing-features", label: "Choosing features" },
  },
  "emission.covariance_type": {
    title: "Covariance type",
    body: "Shape of each Gaussian's covariance. 'full' is most flexible (most parameters); 'diag' assumes uncorrelated features; 'tied' shares one matrix; 'spherical' is a single variance per state.",
    lesson: { id: "lesson-5-baum-welch", label: "Baum-Welch" },
  },
  "emission.n_mix": {
    title: "Mixture components",
    body: "Number of Gaussians blended per state (GMM). More components capture sub-modes within a regime but add parameters — let BIC decide if they pay off.",
    lesson: { id: "lesson-8-gmm-hmm", label: "GMM-HMM" },
  },
  "emission.n_symbols": {
    title: "Number of symbols",
    body: "Size of the discrete alphabet for Multinomial emissions. Your single integer column must contain values in [0, n_symbols).",
    lesson: { id: "lesson-2-markov-chains", label: "Markov chains" },
  },
  "init.strategy": {
    title: "Initialisation strategy",
    body: "How parameters are seeded before EM. 'kmeans' clusters the data first (usually best for Gaussian); 'uniform'/'random' are simpler; 'data_frequencies' seeds from observed counts. Init matters — EM finds a local optimum.",
    lesson: { id: "lesson-5-baum-welch", label: "Baum-Welch" },
  },
  "init.seed": {
    title: "Random seed",
    body: "Fixes the RNG so the fit is reproducible. Change it to probe sensitivity to initialisation.",
  },
  "fit.n_iter": {
    title: "Max EM iterations",
    body: "Upper bound on Baum-Welch (EM) iterations. The fit stops earlier if the log-likelihood change drops below tol.",
    lesson: { id: "lesson-5-baum-welch", label: "Baum-Welch" },
  },
  "fit.tol": {
    title: "Convergence tolerance",
    body: "EM stops when the per-iteration log-likelihood improvement falls below this. Smaller = stricter (more iterations).",
    lesson: { id: "lesson-5-baum-welch", label: "Baum-Welch" },
  },
  "priors.alpha": {
    title: "Dirichlet prior (α)",
    body: "Smoothing on the transition rows. α > 1 pulls toward uniform; α = 1 (or empty) is plain MLE. Useful when some transitions are rarely observed.",
    lesson: { id: "lesson-10-bayesian-hmm", label: "Bayesian HMM" },
  },
  "scan.k_range": {
    title: "Number of states (K)",
    body: "The hidden-state count to sweep. A scan/compare fits one model per K in [k_min, k_max] and ranks them by information criterion.",
  },
  "compare.emission_types": {
    title: "Emission families to compare",
    body: "Which P(X) families to put in the grid. All are directly comparable by BIC/AIC/HQIC. Each family is fit at every K in the range.",
    lesson: { id: "lesson-8-gmm-hmm", label: "GMM-HMM" },
  },
};
```

- [ ] **Step 2: Create the HelpTip component**

Create `src/hmm_studio/frontend/src/components/help/HelpTip.tsx`:

```tsx
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { PARAM_HELP } from "./paramHelp";

interface HelpTipProps {
  paramKey: string;
  // Which edge the popover aligns to. "left" (default) extends to the right;
  // "right" extends to the left (use near a right-hand panel edge).
  align?: "left" | "right";
}

export function HelpTip({ paramKey, align = "left" }: HelpTipProps) {
  const entry = PARAM_HELP[paramKey];
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLSpanElement | null>(null);

  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  // Unknown key → render nothing (no orphan "?").
  if (!entry) return null;

  return (
    <span ref={wrapRef} className="relative inline-flex items-center">
      <button
        type="button"
        aria-label={`Help: ${entry.title}`}
        aria-expanded={open}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setOpen((v) => !v);
        }}
        className="ml-1 w-4 h-4 inline-flex items-center justify-center rounded-full border border-slate-300 text-[10px] leading-none text-slate-500 hover:bg-brand-600 hover:text-white hover:border-brand-600"
      >
        ?
      </button>
      {open && (
        <div
          role="dialog"
          onClick={(e) => e.stopPropagation()}
          className={
            "absolute top-full mt-1 z-50 w-64 rounded-md border border-slate-200 bg-white p-3 shadow-lg text-left font-normal normal-case " +
            (align === "right" ? "right-0" : "left-0")
          }
        >
          <div className="text-xs font-semibold text-slate-800 mb-1">{entry.title}</div>
          <div className="text-xs text-slate-600 leading-snug">{entry.body}</div>
          {entry.lesson && (
            <Link
              to={`/academy/${entry.lesson.id}`}
              onClick={() => setOpen(false)}
              className="mt-2 inline-block text-xs text-indigo-600 hover:underline"
            >
              Learn more → {entry.lesson.label}
            </Link>
          )}
        </div>
      )}
    </span>
  );
}
```

(`font-normal normal-case` on the popover protects the copy from inheriting bold/uppercase section styles.)

- [ ] **Step 3: Type-check**

Run (from `src/hmm_studio/frontend`): `npm run lint`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add src/hmm_studio/frontend/src/components/help/paramHelp.ts src/hmm_studio/frontend/src/components/help/HelpTip.tsx
git commit -m "feat(ui): HelpTip popover + paramHelp registry"
```
(End message with the `Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>` trailer.)

---

### Task 2: wire HelpTip into the editor SidePanel

**Files:**
- Modify: `src/hmm_studio/frontend/src/components/topology/SidePanel.tsx`

- [ ] **Step 1: Import HelpTip**

At the top of `src/hmm_studio/frontend/src/components/topology/SidePanel.tsx`, add:

```tsx
import { HelpTip } from "../help/HelpTip";
```

- [ ] **Step 2: Extend the `Row` helper to accept a `paramKey`**

In `GlobalPanel`, replace the `Row` definition:

```tsx
  const Row = ({
    label,
    children,
  }: {
    label: string;
    children: React.ReactNode;
  }) => (
    <label className="flex items-center justify-between gap-2 text-sm">
      <span className="text-slate-700">{label}</span>
      {children}
    </label>
  );
```

with:

```tsx
  const Row = ({
    label,
    paramKey,
    children,
  }: {
    label: string;
    paramKey?: string;
    children: React.ReactNode;
  }) => (
    <label className="flex items-center justify-between gap-2 text-sm">
      <span className="text-slate-700 inline-flex items-center">
        {label}
        {paramKey && <HelpTip paramKey={paramKey} align="right" />}
      </span>
      {children}
    </label>
  );
```

- [ ] **Step 3: Add `paramKey` to each Row**

In `GlobalPanel`'s JSX, add the matching `paramKey` to every `<Row>`:

- `<Row label="Name">` → `<Row label="Name" paramKey="topology.name">`
- `<Row label="Type">` → `<Row label="Type" paramKey="emission.type">`
- `<Row label="n_features">` → `<Row label="n_features" paramKey="emission.n_features">`
- `<Row label="covariance">` → `<Row label="covariance" paramKey="emission.covariance_type">`
- `<Row label="n_mix">` → `<Row label="n_mix" paramKey="emission.n_mix">`
- `<Row label="n_symbols">` → `<Row label="n_symbols" paramKey="emission.n_symbols">`
- `<Row label="Strategy">` → `<Row label="Strategy" paramKey="init.strategy">`
- `<Row label="Seed">` → `<Row label="Seed" paramKey="init.seed">`
- `<Row label="n_iter">` → `<Row label="n_iter" paramKey="fit.n_iter">`
- `<Row label="tol">` → `<Row label="tol" paramKey="fit.tol">`
- `<Row label="α (Dirichlet)">` → `<Row label="α (Dirichlet)" paramKey="priors.alpha">`

(Leave the closing `</Row>` and children untouched.)

- [ ] **Step 4: Type-check**

Run (from `src/hmm_studio/frontend`): `npm run lint`
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add src/hmm_studio/frontend/src/components/topology/SidePanel.tsx
git commit -m "feat(ui): parameter help '?' on the topology editor panel"
```

---

### Task 3: wire HelpTip into FitPage and ComparePage

**Files:**
- Modify: `src/hmm_studio/frontend/src/pages/FitPage.tsx`
- Modify: `src/hmm_studio/frontend/src/pages/ComparePage.tsx`

- [ ] **Step 1: FitPage — import + seed + k_min/k_max**

In `src/hmm_studio/frontend/src/pages/FitPage.tsx`, add the import:

```tsx
import { HelpTip } from "../components/help/HelpTip";
```

Add a `?` to the seed label — replace:

```tsx
          <span className="text-slate-700 w-24">Seed (override)</span>
```

with:

```tsx
          <span className="text-slate-700 w-24 inline-flex items-center">
            Seed (override)
            <HelpTip paramKey="init.seed" />
          </span>
```

Add a `?` to the k_min and k_max labels — replace:

```tsx
              <span className="text-slate-600">k_min</span>
```

with:

```tsx
              <span className="text-slate-600 inline-flex items-center">
                k_min
                <HelpTip paramKey="scan.k_range" />
              </span>
```

and replace:

```tsx
              <span className="text-slate-600">k_max</span>
```

with:

```tsx
              <span className="text-slate-600 inline-flex items-center">
                k_max
                <HelpTip paramKey="scan.k_range" />
              </span>
```

- [ ] **Step 2: ComparePage — import + emission families + n_mix + k_min/k_max + seed**

In `src/hmm_studio/frontend/src/pages/ComparePage.tsx`, add the import:

```tsx
import { HelpTip } from "../components/help/HelpTip";
```

Replace the "Emission families" heading:

```tsx
        <h3 className="text-sm font-semibold text-slate-700 mb-2">Emission families</h3>
```

with:

```tsx
        <h3 className="text-sm font-semibold text-slate-700 mb-2 inline-flex items-center">
          Emission families
          <HelpTip paramKey="compare.emission_types" />
        </h3>
```

Replace the n_mix label:

```tsx
            <span className="text-slate-600">n_mix (GMM)</span>
```

with:

```tsx
            <span className="text-slate-600 inline-flex items-center">
              n_mix (GMM)
              <HelpTip paramKey="emission.n_mix" />
            </span>
```

Replace the k_min label:

```tsx
            <span className="text-slate-600">k_min</span>
```

with:

```tsx
            <span className="text-slate-600 inline-flex items-center">
              k_min
              <HelpTip paramKey="scan.k_range" />
            </span>
```

Replace the k_max label:

```tsx
            <span className="text-slate-600">k_max</span>
```

with:

```tsx
            <span className="text-slate-600 inline-flex items-center">
              k_max
              <HelpTip paramKey="scan.k_range" />
            </span>
```

Replace the seed label:

```tsx
          <span className="text-slate-700 w-24">Seed (override)</span>
```

with:

```tsx
          <span className="text-slate-700 w-24 inline-flex items-center">
            Seed (override)
            <HelpTip paramKey="init.seed" />
          </span>
```

- [ ] **Step 3: Type-check**

Run (from `src/hmm_studio/frontend`): `npm run lint`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add src/hmm_studio/frontend/src/pages/FitPage.tsx src/hmm_studio/frontend/src/pages/ComparePage.tsx
git commit -m "feat(ui): parameter help '?' on Fit and Compare pages"
```

---

### Task 4: build + CHANGELOG + spec done-check

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `docs/specs/2026-05-27-parameter-help-tooltips.md`

- [ ] **Step 1: Full build**

Run (from `src/hmm_studio/frontend`): `npm run build`
Expected: `tsc` clean + `vite build` produces a bundle, no errors.

- [ ] **Step 2: Manual verification checklist** (note results in the commit/PR, not automated)

Run the dev server (`npm run dev`) or the built app and confirm:
- A `?` appears next to each parameter on the Topology editor panel, the Fit page (seed, k_min, k_max), and the Compare page (emission families, n_mix, k_min, k_max, seed).
- Clicking `?` opens the popover; clicking elsewhere or pressing Esc closes it.
- The "Learn more →" link navigates to the right `/academy/<lesson>` page.
- On the right-hand editor panel the popover opens leftward (stays on-screen).

- [ ] **Step 3: Update CHANGELOG**

In `CHANGELOG.md`, under `[Unreleased]` → `### Added`:

```markdown
- Parameter help: a `?` next to each parameter on the Topology editor, Fit, and
  Compare pages opens a popover explaining it, with a "Learn more →" deep link to
  the relevant Academy lesson. Backed by a single `paramHelp` content registry.
```

- [ ] **Step 4: Mark the spec done**

In `docs/specs/2026-05-27-parameter-help-tooltips.md`, append:

```markdown
## Update 2026-05-27 — shipped

Implemented. Open questions resolved: (1) the Data page has no model/fit
parameters, so the wired surfaces are the editor SidePanel + Fit + Compare
(Data page N/A); (2) `emission.type` links to lesson-1; (3) hand-rolled popover
with an `align` prop (no new dependency). No JS test runner exists — validated
via `npm run build` + manual check (gap noted in §5 stands).
```

- [ ] **Step 5: Commit**

```bash
git add CHANGELOG.md docs/specs/2026-05-27-parameter-help-tooltips.md
git commit -m "docs(ui): changelog + spec done-check for parameter help tooltips"
```

---

## Definition of done (per spec §6)

- [ ] `HelpTip.tsx` + `paramHelp.ts` created; `PARAM_HELP` covers all wired keys.
- [ ] `?` on the editor panel, Fit page, and Compare page (Data page N/A — no params).
- [ ] Popover accessible: opens on click, closes on Esc / outside-click; lesson links work.
- [ ] `npm run build` clean.
- [ ] CHANGELOG `[Unreleased]` updated; spec marked shipped.

## Out of scope (deferred)

- Per-state emission / per-edge prior panels (`PerStateEmissionPanel`, `PerEdgePriorPanel`) — v2 if wanted; v1 covers the global panel + run surfaces.
- A JS unit test for `HelpTip` — no test runner exists; introducing Vitest is out of scope (gap noted in the spec).
- Hover-preview / smart viewport-flip positioning — `align` prop suffices for v1.

## Self-review

- **Spec coverage:** HelpTip (click popover, a11y, lesson link), paramHelp registry, wired across every surface that has parameters (editor/Fit/Compare), Data-page N/A resolved → Tasks 1-4. ✓
- **Placeholder scan:** all component + registry code is complete; every wiring edit shows exact old→new strings. ✓
- **Key consistency:** every `paramKey` passed in Tasks 2-3 (`topology.name`, `emission.*`, `init.*`, `fit.*`, `priors.alpha`, `scan.k_range`, `compare.emission_types`) exists in `PARAM_HELP` (Task 1). Lesson ids (`lesson-1-what-is-an-hmm`, `lesson-2-markov-chains`, `lesson-5-baum-welch`, `lesson-8-gmm-hmm`, `lesson-10-bayesian-hmm`, `lesson-13-choosing-features`) all exist in `lessons/index.ts`. ✓
- **No-dep check:** popover is hand-rolled; only `react` + `react-router-dom` (already deps) used. ✓
