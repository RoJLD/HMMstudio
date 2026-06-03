# Academy emission lessons — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct the now-false claims in `lesson-14-comparing-models.tsx` and add a new `lesson-15-choosing-emission.tsx` ("diagnostic-first") that teaches when an emission is wrong, the in-app GMM-HMM remedy, and a sourced "Beyond GMM" panorama backed by a deep-research run.

**Architecture:** Pure frontend content change. Two TSX lessons + one index entry + one bibliography update. No new dependency, no new component, no backend touch. Verification is `npm run lint` (tsc) + `npm run build` (Vite) — there is no per-lesson test runner.

**Tech Stack:** React 18, TypeScript 5.5, Vite 5, Tailwind 3, react-router-dom 6. Frontend lives in `src/hmm_studio/frontend/`.

**Spec:** `docs/superpowers/specs/2026-05-28-academy-emission-lessons-design.md`

**Execution convention:** all `npm` commands run from `src/hmm_studio/frontend/`.

**Commit policy:** the user handles commits. To execute: `git add` the modified files at each task's end and STOP. Do NOT run `git commit`. The commit lines below describe the intended commit for reference.

**Branch policy:** if the repo is on `main`/`master` at execution start, create a feature branch first (workspace CLAUDE.md mandates branching off the default before implementation): `git checkout -b academy-emission-lessons`. Then run Task 1.

---

## Task 1: Setup — confirm baseline green

**Files:**
- None modified. Sanity check the toolchain.

- [ ] **Step 1: Verify node_modules present**

From `src/hmm_studio/frontend/`:
Run: `test -d node_modules && echo OK || npm install`
Expected: `OK` (if installed) or pip-style install logs ending without errors.

- [ ] **Step 2: Baseline lint (tsc --noEmit)**

Run (from `src/hmm_studio/frontend/`): `npm run lint`
Expected: exit 0, no TypeScript errors. (If errors exist pre-change, STOP and escalate — this plan assumes a green baseline.)

- [ ] **Step 3: Baseline build**

Run (from `src/hmm_studio/frontend/`): `npm run build`
Expected: exit 0; `dist/` produced. The build runs `tsc && vite build`, so it doubles as a stricter typecheck.

(No commit on this task — it only validates the starting state.)

---

## Task 2: Correct `lesson-14-comparing-models.tsx`

**Files:**
- Modify: `src/hmm_studio/frontend/src/lessons/lesson-14-comparing-models.tsx`

The current file already imports `Link` from `react-router-dom` and `FurtherReading`. Three surgical edits + one append.

- [ ] **Step 1: Replace the "simplest model often wins" paragraph**

In `src/hmm_studio/frontend/src/lessons/lesson-14-comparing-models.tsx`, replace this exact block:

```tsx
      <p className="text-slate-700 mb-4">
        In a real unsupervised crypto regime-detection study, a plain{" "}
        <strong>GMM-HMM</strong> outperformed a more elaborate non-homogeneous HMM
        (NHMM) with covariate-driven transitions. More parameters bought a higher raw
        likelihood, but not a better penalized score. The lesson generalizes: start
        simple, and make each added ingredient earn its place.
      </p>
```

with:

```tsx
      <p className="text-slate-700 mb-4">
        In a first pass of this study, a plain <strong>GMM-HMM</strong> appeared to
        outperform a non-homogeneous HMM (NHMM) — but that headline did not survive a
        clean re-benchmark. The original comparison mixed two libraries, used K=2 for
        the GMM-HMM but K=3 for the others, and applied a per-sample normalization by
        hand outside the script. A re-run with a single library, the same K, the same
        features, and time-series cross-validation showed the parsimony lesson still
        holds — but on a different axis : it's the{" "}
        <strong>emission distribution</strong> that dominates (heavy-tailed Student-T
        crushes Gaussian on held-out log-likelihood), while{" "}
        <strong>non-homogeneous transitions add essentially nothing</strong> over the
        homogeneous Student-T HMM. Start simple, and make each added ingredient earn
        its place — but be honest about <em>which</em> ingredient.
      </p>
```

- [ ] **Step 2: Append a "four pitfalls" paragraph at the end of the "You can't compare everything" section**

Locate the existing block that ends with the line `it shows them, but never crowns them "best by BIC".` (this is inside a `<p>...</p>` closing the second paragraph of "You can't compare everything"). Immediately after that closing `</p>` and BEFORE the `<div className="my-6 border-l-4 ...">` case-study credit block, insert:

```tsx
      <p className="text-slate-700 mb-4">
        The first version of this case study tripped on four concrete pitfalls, worth
        knowing : (i) mixing two libraries with different likelihood conventions in one
        table ; (ii) comparing in-sample vs hold-out scores ; (iii) applying a
        per-observation normalization by hand outside the script — invisible to anyone
        reading the code ; (iv) evaluating a held-out predictive density under a
        Gaussian approximation for models with heavy-tailed emissions, which mismodels
        the tails and makes the metric non-comparable across families. Fixing all four
        turned the original "GMM-HMM wins, NHMM +60%" claim into "emission dominates,
        transitions don't".
      </p>
```

- [ ] **Step 3: Replace the "Case study credit" callout body**

Replace this exact block:

```tsx
        <p className="text-sm text-slate-700">
          <strong>Case study credit.</strong> The empirical findings above are adapted
          from Nathan Berbinau's unsupervised crypto regime-detection research (
          <a
            href="https://github.com/NathanBerbinau"
            target="_blank"
            rel="noopener noreferrer"
            className="text-brand-700 hover:underline"
          >
            github.com/NathanBerbinau
          </a>
          ). We reuse the <em>methodology and its honest caveats</em> — not the
          out-of-scope models. Read the numbers as a qualitative case study: the
          benchmark used a single dataset and a metric that isn't defined across model
          families, so the takeaway is the <em>method</em>, not specific scores.
        </p>
```

with:

```tsx
        <p className="text-sm text-slate-700">
          <strong>Case study credit.</strong> The empirical findings above are adapted
          from Nathan Berbinau's unsupervised crypto regime-detection research, with a
          methodology re-benchmark in the sibling crypto-experiment repo
          (<code>Projet_Robin/benchmark/</code>). We reuse the methodology, the{" "}
          <strong>honest re-benchmark</strong>, and its <strong>corrected</strong>{" "}
          negative results — not the out-of-scope models. Read the numbers as a
          qualitative case study : a single dataset, several metrics not all
          comparable across model families.
        </p>
```

- [ ] **Step 4: Append a "See also" link to lesson 15 after the existing "Try it" paragraph**

Locate the existing "Try it" paragraph (ends with `decide — including which "obvious upgrade" doesn't actually pay.`). Immediately after that closing `</p>` and BEFORE the `<FurtherReading ... />` element, insert:

```tsx
      <p className="text-slate-700 mb-4">
        <strong>See also.</strong>{" "}
        <Link
          to="/academy/lesson-15-choosing-emission"
          className="text-brand-700 hover:underline"
        >
          Lesson 15 — Choosing the emission distribution
        </Link>{" "}
        : the diagnostic recipe and the upgrade ladder once you know the emission is
        the bottleneck.
      </p>
```

- [ ] **Step 5: Lint + build**

Run (from `src/hmm_studio/frontend/`): `npm run lint && npm run build`
Expected: both exit 0. (JSX changes don't break types; the `Link` import is already in lesson 14.)

- [ ] **Step 6: Stage (no commit)**

Run (from repo root): `git add src/hmm_studio/frontend/src/lessons/lesson-14-comparing-models.tsx`

Intended commit (left to user): `docs(academy): correct lesson 14 with re-benchmark findings`

---

## Task 3: Create `lesson-15-choosing-emission.tsx`

**Files:**
- Create: `src/hmm_studio/frontend/src/lessons/lesson-15-choosing-emission.tsx`

- [ ] **Step 1: Write the full lesson 15 file**

Create `src/hmm_studio/frontend/src/lessons/lesson-15-choosing-emission.tsx` with this exact content:

```tsx
import { Link } from "react-router-dom";
import { FurtherReading } from "../components/academy/FurtherReading";

export function Lesson15ChoosingEmission() {
  return (
    <>
      <h2 className="text-xl font-semibold text-slate-900 mb-3">
        When the emission is wrong
      </h2>
      <p className="text-slate-700 mb-4">
        Your transitions are clean, your features are decorrelated, your K is
        sensible — and yet held-out log-likelihood collapses. The culprit is often the{" "}
        <strong>emission distribution</strong> : the family chosen to model{" "}
        <code className="bg-slate-100 px-1 rounded text-sm">p(y | z)</code> simply
        does not fit the shape of the data inside each regime.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        Symptoms of a wrong emission
      </h2>
      <ul className="list-disc pl-6 space-y-2 text-slate-700 mb-4">
        <li>
          <strong>Held-out log-likelihood collapses</strong> with very high variance
          between cross-validation folds. A Gaussian assigns near-zero density to tail
          observations ; one fat-tailed fold can move the LL by hundreds of nats.
        </li>
        <li>
          <strong>Train LL is fine but eval LL is catastrophic.</strong> The model
          fits the bulk and is destroyed by the tails — the classic
          mismatched-family signature.
        </li>
        <li>
          <strong>Residuals per state don't match the assumed density.</strong> A
          heavy-tailed residual histogram against a fitted Gaussian curve is the
          clearest visual diagnostic.
        </li>
      </ul>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        Diagnostic recipe
      </h2>
      <ol className="list-decimal pl-6 space-y-2 text-slate-700 mb-4">
        <li>Fit the model, then decode states (Viterbi or posterior).</li>
        <li>
          For each state, plot the histogram of observed values assigned to that
          state, overlaid with the fitted emission density.
        </li>
        <li>
          If the visual mismatch is flagrant — or if held-out LL/obs has a standard
          deviation much larger than its mean — the emission family is the suspect.
        </li>
      </ol>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        The remedy inside hmm-studio : GMM-HMM
      </h2>
      <p className="text-slate-700 mb-4">
        The native remedy in the app is to switch from a single Gaussian per state to
        a <strong>mixture of Gaussians</strong> (GMM-HMM). With a handful of
        components per state, the mixture can mimic heavier tails and multi-modal
        regimes that a single Gaussian cannot capture. See{" "}
        <Link
          to="/academy/lesson-8-gmm-hmm"
          className="text-brand-700 hover:underline"
        >
          Lesson 8 — GMM-HMM
        </Link>{" "}
        for the full story, and the topology preset attached to this lesson for a
        ready-to-fit example.
      </p>
      <p className="text-slate-700 mb-4">
        Caveat : a GMM with Gaussian components is still a sum of{" "}
        <em>thin-tailed</em> densities. It approximates fat tails by spending
        components on the tails, which costs parameters. For genuinely heavy-tailed
        data, a proper heavy-tailed emission is more parsimonious — but those don't
        yet live in hmm-studio (see below).
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">Beyond GMM</h2>
      <p className="text-slate-700 mb-4">
        If even GMM isn't enough, the research literature offers stronger emission
        families. Ranked by the evidence base for our regime (n ≈ a few thousand,
        low-dimensional, heavy-tailed financial returns) :
      </p>
      <ul className="list-disc pl-6 space-y-2 text-slate-700 mb-4">
        <li>
          <strong>Multivariate skew-T mixture</strong> — strict, low-risk upgrade
          from Student-T. Handles heavy tails AND asymmetry, with an exact EM
          algorithm (no Monte Carlo). <em>Recommendation #1.</em>
        </li>
        <li>
          <strong>Generalized Hyperbolic (GH) HMM</strong> — nests Student-T, NIG and
          VG as special cases. Published specifically for multivariate financial
          returns, with penalized EM and L1 on state-specific precisions.{" "}
          <em>Recommendation #2.</em>
        </li>
        <li>
          <strong>Normalizing flows as emission</strong> (FlowHMM and variants) —
          architecturally viable with an EM + SGD hybrid M-step. But no peer-reviewed
          evidence they beat Student-T on financial held-out LL at n ≈ 3500, and
          neural density estimators overfit severely under MLE with scarce data.{" "}
          <em>Defer.</em>
        </li>
        <li>
          <strong>Fourier-basis / characteristic-function HMM emissions</strong> —
          sometimes raised as an idea. No primary source surfaces this as a working
          HMM emission family : prefer skew-T mixture or GH.
        </li>
      </ul>

      <div className="my-6 border-l-4 border-brand-300 bg-brand-50 px-4 py-3 rounded-r">
        <p className="text-sm text-slate-700">
          <strong>Case study.</strong> On a daily ETH dataset (4 post-correlation
          features, ~3500 observations), a Gaussian HMM produces LL/obs around −200
          to −400 with huge variance — its tails are catastrophic on held-out folds.
          A Student-T HMM in the same setup gives LL/obs ≈ −6.3 stably. A
          non-homogeneous HMM with the same Student-T emission adds essentially
          nothing. Skew-T (single, not mixture) underperforms plain Student-T. The
          driver is the emission, not the transition structure. (Re-benchmark in{" "}
          <code>Projet_Robin/benchmark/</code> of the sibling crypto experiment repo.)
        </p>
      </div>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">Try it</h2>
      <p className="text-slate-700 mb-4">
        Open the topology preset attached to this lesson : a 3-state GMM-HMM with 3
        mixture components per state on 2D features. Fit it, decode states, and
        inspect the residuals per state. If your data is heavy-tailed, the GMM
        components will cluster around the tails.
      </p>

      <FurtherReading
        references={[
          {
            label: "Lee & McLachlan 2011",
            title:
              "Finite mixtures of multivariate skew t distributions — exact EM",
            url: "https://arxiv.org/pdf/1109.4706",
            note: "the recommended strict upgrade from Student-T",
          },
          {
            label: "Foroni, Merlo & Petrella 2024",
            title:
              "Hidden Markov graphical models with state-dependent generalized hyperbolic distributions",
            url: "https://arxiv.org/pdf/2412.03668",
            note: "GH HMM applied to multivariate financial returns",
          },
          {
            label: "FlowHMM (NeurIPS 2022)",
            title: "Flow-based HMM emissions trained by hybrid EM + SGD",
            url: "https://proceedings.neurips.cc/paper_files/paper/2022/file/39c5871aa13be86ab978cba7069cbcec-Paper-Conference.pdf",
            note: "feasible architecture, but no financial held-out evidence at small n",
          },
          {
            label: "Rothfuss et al. (ICLR 2020)",
            title:
              "Noise regularization for conditional density estimation",
            url: "https://openreview.net/pdf?id=rygtPhVtDS",
            note: "documents the overfitting failure mode of neural density estimators at small sample size",
          },
          {
            label: "Academy bibliography",
            title: "Central sourced reference list for all Academy lessons",
            url: "https://github.com/RoJLD/HMMstudio/blob/main/docs/sources/academy-references.md",
          },
        ]}
      />
    </>
  );
}
```

- [ ] **Step 2: Lint + build**

Run (from `src/hmm_studio/frontend/`): `npm run lint && npm run build`
Expected: both exit 0. (The file is a standalone component — it compiles even without an `index.ts` entry yet, because nothing imports it until Task 4.)

- [ ] **Step 3: Stage (no commit)**

Run (from repo root): `git add src/hmm_studio/frontend/src/lessons/lesson-15-choosing-emission.tsx`

Intended commit (left to user): `feat(academy): add lesson 15 — choosing the emission distribution`

---

## Task 4: Wire lesson 15 into `lessons/index.ts`

**Files:**
- Modify: `src/hmm_studio/frontend/src/lessons/index.ts`

- [ ] **Step 1: Add the import**

In `src/hmm_studio/frontend/src/lessons/index.ts`, locate this line:

```ts
import { Lesson14ComparingModels } from "./lesson-14-comparing-models";
```

Replace it with these two lines (the new import goes immediately after):

```ts
import { Lesson14ComparingModels } from "./lesson-14-comparing-models";
import { Lesson15ChoosingEmission } from "./lesson-15-choosing-emission";
```

- [ ] **Step 2: Add the LessonMeta entry at the end of the `LESSONS` array**

Locate the last entry in the `LESSONS` array (the lesson 14 object) and the closing `];`. Insert a new object literal after the lesson 14 entry's closing `},`. The result must look like:

```ts
  {
    id: "lesson-14-comparing-models",
    category: "selection",
    order: 3,
    title: "Comparing models honestly",
    estimatedMinutes: 12,
    difficulty: "Advanced",
    description:
      "When does complexity pay? A regime-detection case study: benchmark, don't assume; simpler can win; negative results count; and why you can't compare log-likelihoods across model families.",
    status: "published",
    content: Lesson14ComparingModels,
  },
  {
    id: "lesson-15-choosing-emission",
    category: "selection",
    order: 4,
    title: "Choosing the emission distribution",
    estimatedMinutes: 12,
    difficulty: "Intermediate",
    description:
      "Your transitions are fine, your features are clean, yet held-out log-likelihood collapses. The culprit is often the emission. A diagnostic recipe, what to do inside hmm-studio, and what's beyond.",
    status: "published",
    content: Lesson15ChoosingEmission,
    presetTopologyYaml: `name: lesson_15_gmm_emission_demo
n_states: 3
state_names: [calm, normal, stressed]
emission:
  type: gmm
  n_features: 2
  n_mix: 3
  covariance_type: full
startprob: uniform
init: {strategy: kmeans, seed: 42}
fit: {algorithm: baum_welch, n_iter: 100, tol: 1.0e-4}
`,
  },
];
```

(Only the lesson-15 object literal and the comma after lesson-14 are new; the lesson-14 entry above is shown verbatim only as the anchor point.)

- [ ] **Step 3: Lint + build**

Run (from `src/hmm_studio/frontend/`): `npm run lint && npm run build`
Expected: both exit 0. The build now bundles lesson 15 as part of the Academy.

- [ ] **Step 4: Smoke-check by spot-grepping the produced bundle (optional but cheap)**

Run (from `src/hmm_studio/frontend/`): `grep -l "lesson-15-choosing-emission" dist/assets/*.js | head -1`
Expected: at least one path printed — confirms the id made it into the bundle.

- [ ] **Step 5: Stage (no commit)**

Run (from repo root): `git add src/hmm_studio/frontend/src/lessons/index.ts`

Intended commit (left to user): `feat(academy): register lesson 15 in the lessons index`

---

## Task 5: Update `docs/sources/academy-references.md`

**Files:**
- Modify: `docs/sources/academy-references.md`

Two edits : append four new references at the end of the Tier 3 section, and add two rows to the per-lesson citation table.

- [ ] **Step 1: Append four Tier-3 entries**

Open `docs/sources/academy-references.md`. Find the section heading `## Tier 3 — Variant-specific` (NHMM / GMM / Factorial / Hierarchical / Bayesian / semi-supervised). Locate the end of that section — the last entry there ends BEFORE the `## How each Academy lesson cites these` heading. Immediately before that next-section heading, insert:

```markdown
### Lee & McLachlan 2011 — *Finite mixtures of multivariate skew t distributions*

Sharon X. Lee, Geoffrey J. McLachlan. arXiv:1109.4706 (preprint of the
2014 *Statistics and Computing* paper).

EM updates for unrestricted multivariate skew-t mixtures reduce to truncated
multivariate-t moments computable without Monte Carlo. The authors' R
packages `EMMIXuskew` and `EMMIXcskew` implement this directly. The
practical low-risk upgrade from a Student-T emission when the data is
heavy-tailed AND asymmetric.

— **PDF** : <https://arxiv.org/pdf/1109.4706>

### Foroni, Merlo & Petrella 2024 — *Hidden Markov graphical models with state-dependent generalized hyperbolic distributions*

Beatrice Foroni, Luca Merlo, Lea Petrella. arXiv:2412.03668 (Dec 2024).

HMM with state-conditional generalized hyperbolic emissions, fit by
penalized EM with L1 regularization on state-specific precision matrices.
Applied directly to multivariate financial returns. GH nests Student-T,
NIG and VG as special cases, so this is a strict generalization of the
Student-T baseline.

— **PDF** : <https://arxiv.org/pdf/2412.03668>

### FlowHMM — NeurIPS 2022

Lorek et al. *Advances in Neural Information Processing Systems 35*.

Normalizing-flow emission for an HMM, trained by a hybrid Baum-Welch (EM)
for the transition parameters and mini-batch SGD for the flow M-step.
Reference implementation : github.com/tooploox/flowhmm. Published
experiments are on speech (TIMIT) and generic continuous benchmarks ; no
peer-reviewed financial held-out evidence at small sample size.

— **PDF** : <https://proceedings.neurips.cc/paper_files/paper/2022/file/39c5871aa13be86ab978cba7069cbcec-Paper-Conference.pdf>

### Rothfuss et al. ICLR 2020 — *Noise regularization for conditional density estimation*

Jonas Rothfuss, Fábio Ferreira, Simon Boehm, Simon Walther, Maxim Ulrich,
Tamim Asfour, Andreas Krause. ICLR 2020 (arXiv:1907.08982).

Documents the severe MLE overfitting failure mode of MDN, KMN, and
Normalizing Flow Networks on small datasets (including financial returns)
and proposes noise regularization as a remedy. Critical reference when
considering neural density estimators as HMM emissions at n ≈ a few thousand.

— **PDF** : <https://openreview.net/pdf?id=rygtPhVtDS>

```

- [ ] **Step 2: Append two rows to the per-lesson citation table**

Find the table that begins with the heading `## How each Academy lesson cites these` and the header row `| Lesson | Primary references |`. Append two new rows at the end of that table (after the existing last row, currently for lesson 7). Append BEFORE the next heading (`## Open follow-ups`). The two new lines:

```markdown
| 14. *Comparing models honestly* | re-benchmark methodology in `Projet_Robin/benchmark/` (no central refs cited) |
| 15. *Choosing the emission distribution* | Lee & McLachlan 2011, Foroni-Merlo-Petrella 2024, FlowHMM NeurIPS 2022, Rothfuss et al. ICLR 2020 |
```

- [ ] **Step 3: Sanity-check markdown links**

Run (from repo root): `grep -E "1109.4706|2412.03668|39c5871aa13be86ab978cba7069cbcec|rygtPhVtDS" docs/sources/academy-references.md | wc -l`
Expected: `4` (one match per new reference URL).

- [ ] **Step 4: Stage (no commit)**

Run (from repo root): `git add docs/sources/academy-references.md`

Intended commit (left to user): `docs(academy): add Tier-3 emission references for lessons 14 & 15`

---

## Task 6: End-to-end verification

**Files:**
- None modified. Final whole-frontend check.

- [ ] **Step 1: Full clean build**

Run (from `src/hmm_studio/frontend/`): `npm run build`
Expected: exit 0. `dist/` contains the lesson-15 bundle.

- [ ] **Step 2: Visual smoke test (recommended, optional)**

Run (from `src/hmm_studio/frontend/`): `npm run dev` (in another shell), then open `http://localhost:5173/academy` in a browser. Navigate to lesson 14 (sees corrected text + "See also") and lesson 15 (new lesson renders, preset YAML is loadable in editor via the card). Stop the dev server when done.

- [ ] **Step 3: Confirm staged set**

Run (from repo root): `git status --short`
Expected output should include (only the four touched files staged):

```
 M docs/sources/academy-references.md
 M src/hmm_studio/frontend/src/lessons/index.ts
 M src/hmm_studio/frontend/src/lessons/lesson-14-comparing-models.tsx
 A src/hmm_studio/frontend/src/lessons/lesson-15-choosing-emission.tsx
```

(Exact letters may vary depending on prior staging; what matters is that exactly these four paths show up and nothing else under `src/hmm_studio/frontend/src/lessons/` or `docs/sources/`.)

(No commit on this task — the user commits the staged set.)

---

## Notes
- **No new dependency** was added. The lesson reuses `Link` (already a `react-router-dom` import in lesson 14) and the existing `FurtherReading` component.
- **No backend / `hmm_core` change**. The lesson refers to existing GMM-HMM support, the existing `unsupervised_feature_selection`, and points to the sibling crypto repo for the rest.
- **The "Open follow-ups" section** of `academy-references.md` still mentions "Choosing features" — that entry has been satisfied by lesson 13. Removing or relocating it is out of scope for this plan (cosmetic).
- **Routing.** The `<Link to="/academy/lesson-15-choosing-emission">` and `<Link to="/academy/lesson-8-gmm-hmm">` paths assume the AcademyPage routes by `id`. This matches the convention used by lessons 13 and 14 (which link to `/compare` etc. without breaking) — if the route shape differs in AcademyPage, the link still renders without error and the worst case is a 404; verify quickly in the dev server smoke test (Task 6, Step 2).
