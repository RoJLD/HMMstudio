# Guided HMM creation wizard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** A 5-step "New guided model" wizard that assembles a valid topology and loads it into the editor pre-filled.

**Architecture:** A pure core (`lib/buildTopologyYaml.ts`: `suggestEmission`, `allowedTransitionsForShape`, `buildTopologyYaml`) + a single `WizardPage.tsx` that drives the 5 steps and, on Finish, runs `yamlToTopology(buildTopologyYaml(model)) → useTopologyStore.loadTopology(...) → navigate`. Reuses the dataset store, `paramHelp`/`HelpTip`, and the proven topology-load path. Frontend-only, no new dependency.

**Spec:** `docs/specs/2026-05-27-guided-creation-wizard.md` (incl. §9 resolutions).

**Validation:** no JS test runner — `npm run build` (strict tsc) + manual. The pure helpers are unit-test-ready if Vitest is ever added.

## File Structure
- Create `src/hmm_studio/frontend/src/lib/buildTopologyYaml.ts`
- Create `src/hmm_studio/frontend/src/pages/WizardPage.tsx`
- Modify `src/hmm_studio/frontend/src/App.tsx` (route `/topology/new`)
- Modify `src/hmm_studio/frontend/src/pages/TopologyPage.tsx` ("New guided model" button)
- Modify `CHANGELOG.md`

---

### Task 1: pure core — `buildTopologyYaml.ts`

**Files:** Create `src/hmm_studio/frontend/src/lib/buildTopologyYaml.ts`

- [ ] **Step 1: Write the module (complete)**

```ts
import yaml from "js-yaml";
import type { DatasetPreview } from "../api/client";

export type WizardEmissionType = "gaussian" | "gmm" | "multinomial" | "poisson";
export type TransitionShape = "ergodic" | "left-right" | "bakis";

export interface WizardModel {
  name: string;
  emissionType: WizardEmissionType;
  nFeatures: number; // gaussian/gmm/poisson
  covarianceType: "full" | "diag" | "tied" | "spherical"; // gaussian/gmm
  nMix: number; // gmm
  nSymbols: number; // multinomial
  k: number;
  stateNames: string[]; // length k
  shape: TransitionShape;
  initStrategy: "uniform" | "random" | "kmeans" | "data_frequencies";
  seed: number;
  nIter: number;
  tol: number;
  priorAlpha: number | null;
}

export interface EmissionSuggestion {
  type: WizardEmissionType;
  nFeatures: number;
  nSymbols: number;
}

const isIntDtype = (dt: string | undefined): boolean => !!dt && /^u?int/i.test(dt);

/** Best-effort emission suggestion from a dataset preview. Always overridable. */
export function suggestEmission(preview: DatasetPreview | null | undefined): EmissionSuggestion {
  if (!preview || preview.columns.length === 0) {
    return { type: "gaussian", nFeatures: 1, nSymbols: 2 };
  }
  const cols = preview.columns;
  const colValues = (c: string): number[] =>
    preview.head.map((row) => row[c]).filter((v): v is number => typeof v === "number");

  if (cols.length === 1 && isIntDtype(preview.dtypes[cols[0]])) {
    const vals = colValues(cols[0]);
    const maxV = vals.length ? Math.max(...vals) : 1;
    return { type: "multinomial", nFeatures: 1, nSymbols: Math.max(2, maxV + 1) };
  }
  const allInt = cols.every((c) => isIntDtype(preview.dtypes[c]));
  if (allInt && cols.every((c) => colValues(c).every((v) => v >= 0))) {
    return { type: "poisson", nFeatures: cols.length, nSymbols: 2 };
  }
  return { type: "gaussian", nFeatures: cols.length, nSymbols: 2 };
}

/** allowed_transitions name-pairs for a shape. Ergodic → [] (caller omits the key). */
export function allowedTransitionsForShape(shape: TransitionShape, names: string[]): string[][] {
  if (shape === "ergodic") return [];
  const pairs: string[][] = [];
  const K = names.length;
  for (let i = 0; i < K; i++) {
    pairs.push([names[i], names[i]]); // self-loop
    if (i + 1 < K) pairs.push([names[i], names[i + 1]]); // forward
    if (shape === "bakis" && i + 2 < K) pairs.push([names[i], names[i + 2]]); // skip-one
  }
  return pairs;
}

/** Assemble a standard topology YAML string from the wizard model (pure). */
export function buildTopologyYaml(m: WizardModel): string {
  const emission: Record<string, unknown> = { type: m.emissionType };
  if (m.emissionType === "gaussian" || m.emissionType === "gmm" || m.emissionType === "poisson") {
    emission.n_features = m.nFeatures;
  }
  if (m.emissionType === "gaussian" || m.emissionType === "gmm") {
    emission.covariance_type = m.covarianceType;
  }
  if (m.emissionType === "gmm") emission.n_mix = m.nMix;
  if (m.emissionType === "multinomial") emission.n_symbols = m.nSymbols;

  const obj: Record<string, unknown> = {
    name: m.name || "untitled",
    n_states: m.k,
    state_names: m.stateNames,
    emission,
    startprob: "uniform",
    init: { strategy: m.initStrategy, seed: m.seed },
    fit: { algorithm: "baum_welch", n_iter: m.nIter, tol: m.tol },
  };
  const at = allowedTransitionsForShape(m.shape, m.stateNames);
  if (at.length > 0) obj.allowed_transitions = at;
  if (m.priorAlpha !== null) obj.transmat_prior_alpha = m.priorAlpha;

  return yaml.dump(obj, { lineWidth: 100 });
}
```

- [ ] **Step 2:** `npm run lint` (from frontend) → clean.
- [ ] **Step 3: Commit** `git add src/hmm_studio/frontend/src/lib/buildTopologyYaml.ts && git commit` → `feat(ui): pure topology-builder core for the creation wizard`

---

### Task 2: `WizardPage.tsx`

**Files:** Create `src/hmm_studio/frontend/src/pages/WizardPage.tsx`

- [ ] **Step 1: Write the page (complete)**

```tsx
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTopologyStore } from "../store/topologyStore";
import { useDatasetStore } from "../store/datasetStore";
import { yamlToTopology } from "../lib/yaml";
import { HelpTip } from "../components/help/HelpTip";
import {
  buildTopologyYaml,
  suggestEmission,
  type WizardModel,
  type TransitionShape,
  type WizardEmissionType,
} from "../lib/buildTopologyYaml";

const STEPS = ["Emission", "States", "Transitions", "Training", "Review"] as const;
const SHAPES: { id: TransitionShape; label: string; blurb: string }[] = [
  { id: "ergodic", label: "Ergodic", blurb: "Any state can follow any state (fully connected)." },
  { id: "left-right", label: "Left-right", blurb: "Only stay or advance: sᵢ→sᵢ, sᵢ→sᵢ₊₁. No going back." },
  { id: "bakis", label: "Bakis", blurb: "Left-right plus skip-one: sᵢ→sᵢ₊₂." },
];
const inputCls =
  "border border-slate-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/40";

const defaultNames = (k: number) => Array.from({ length: k }, (_, i) => `s${i}`);

export default function WizardPage() {
  const navigate = useNavigate();
  const dataset = useDatasetStore((s) => s.current);

  const initial = useMemo<WizardModel>(() => {
    const sug = suggestEmission(dataset);
    return {
      name: "untitled",
      emissionType: sug.type,
      nFeatures: sug.nFeatures,
      covarianceType: "full",
      nMix: 2,
      nSymbols: sug.nSymbols,
      k: 3,
      stateNames: defaultNames(3),
      shape: "ergodic",
      initStrategy: "kmeans",
      seed: 42,
      nIter: 100,
      tol: 1e-4,
      priorAlpha: null,
    };
    // compute once at mount from the dataset present then
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const [model, setModel] = useState<WizardModel>(initial);
  const [stepIdx, setStepIdx] = useState(0);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const patch = (p: Partial<WizardModel>) => setModel((m) => ({ ...m, ...p }));

  function setK(raw: number) {
    const k = Math.max(1, Number.isFinite(raw) ? raw : 1);
    setModel((m) => {
      const names = m.stateNames.slice(0, k);
      for (let i = names.length; i < k; i++) names.push(`s${i}`);
      return { ...m, k, stateNames: names };
    });
  }

  const hasFeatures =
    model.emissionType === "gaussian" || model.emissionType === "gmm" || model.emissionType === "poisson";

  const mismatch = useMemo<string | null>(() => {
    if (!dataset) return null;
    if (model.emissionType === "multinomial") {
      return dataset.n_cols !== 1
        ? `Dataset has ${dataset.n_cols} columns; multinomial expects a single integer column.`
        : null;
    }
    return model.nFeatures !== dataset.n_cols
      ? `n_features (${model.nFeatures}) ≠ dataset columns (${dataset.n_cols}).`
      : null;
  }, [dataset, model.emissionType, model.nFeatures]);

  function stepValid(idx: number): boolean {
    if (idx === 0) {
      if (model.emissionType === "multinomial") return model.nSymbols >= 2;
      if (model.emissionType === "gmm" && model.nMix < 1) return false;
      return !hasFeatures || model.nFeatures >= 1;
    }
    if (idx === 1) {
      return (
        model.k >= 1 &&
        model.stateNames.every((n) => n.trim() !== "") &&
        new Set(model.stateNames).size === model.stateNames.length
      );
    }
    return true;
  }

  function finish(goToFit: boolean) {
    setError(null);
    try {
      const partial = yamlToTopology(buildTopologyYaml(model));
      useTopologyStore.getState().loadTopology(partial);
      navigate(goToFit ? "/fit" : "/topology");
    } catch (e) {
      setError(e instanceof Error ? e.message : "could not build topology");
    }
  }

  const isLast = stepIdx === STEPS.length - 1;

  return (
    <div className="max-w-2xl">
      <h2 className="text-2xl font-semibold text-slate-900 mb-1">New guided model</h2>
      <p className="text-slate-600 mb-5">
        Build a topology step by step. On finish it opens in the editor, pre-filled.
      </p>

      <ol className="flex flex-wrap items-center gap-x-2 gap-y-1 mb-6 text-xs">
        {STEPS.map((label, i) => (
          <li key={label} className="flex items-center gap-2">
            <span
              className={
                "w-5 h-5 rounded-full inline-flex items-center justify-center font-semibold " +
                (i === stepIdx
                  ? "bg-brand-600 text-white"
                  : i < stepIdx
                    ? "bg-green-500 text-white"
                    : "bg-slate-200 text-slate-600")
              }
            >
              {i + 1}
            </span>
            <span className={i === stepIdx ? "font-medium text-slate-800" : "text-slate-500"}>
              {label}
            </span>
            {i < STEPS.length - 1 && <span className="text-slate-300">—</span>}
          </li>
        ))}
      </ol>

      <div className="border border-slate-200 rounded-md p-4 bg-white mb-4 space-y-3">
        {/* ---- Step 1: Emission ---- */}
        {stepIdx === 0 && (
          <>
            {dataset && (
              <p className="text-xs text-slate-500">
                Dataset <span className="font-mono">{dataset.filename}</span> ({dataset.n_cols} cols)
                — suggestion prefilled.
              </p>
            )}
            <label className="flex items-center justify-between gap-2 text-sm">
              <span className="text-slate-700 inline-flex items-center">
                Type
                <HelpTip paramKey="emission.type" />
              </span>
              <select
                value={model.emissionType}
                onChange={(e) => patch({ emissionType: e.target.value as WizardEmissionType })}
                className={inputCls + " w-40"}
              >
                <option value="gaussian">gaussian</option>
                <option value="gmm">gmm</option>
                <option value="multinomial">multinomial</option>
                <option value="poisson">poisson</option>
              </select>
            </label>
            {hasFeatures && (
              <label className="flex items-center justify-between gap-2 text-sm">
                <span className="text-slate-700 inline-flex items-center">
                  n_features
                  <HelpTip paramKey="emission.n_features" />
                </span>
                <input
                  type="number"
                  min={1}
                  value={model.nFeatures}
                  onChange={(e) => patch({ nFeatures: parseInt(e.target.value, 10) || 1 })}
                  className={inputCls + " w-40"}
                />
              </label>
            )}
            {(model.emissionType === "gaussian" || model.emissionType === "gmm") && (
              <label className="flex items-center justify-between gap-2 text-sm">
                <span className="text-slate-700 inline-flex items-center">
                  covariance
                  <HelpTip paramKey="emission.covariance_type" />
                </span>
                <select
                  value={model.covarianceType}
                  onChange={(e) =>
                    patch({ covarianceType: e.target.value as WizardModel["covarianceType"] })
                  }
                  className={inputCls + " w-40"}
                >
                  <option value="full">full</option>
                  <option value="diag">diag</option>
                  <option value="tied">tied</option>
                  <option value="spherical">spherical</option>
                </select>
              </label>
            )}
            {model.emissionType === "gmm" && (
              <label className="flex items-center justify-between gap-2 text-sm">
                <span className="text-slate-700 inline-flex items-center">
                  n_mix
                  <HelpTip paramKey="emission.n_mix" />
                </span>
                <input
                  type="number"
                  min={1}
                  value={model.nMix}
                  onChange={(e) => patch({ nMix: parseInt(e.target.value, 10) || 1 })}
                  className={inputCls + " w-40"}
                />
              </label>
            )}
            {model.emissionType === "multinomial" && (
              <label className="flex items-center justify-between gap-2 text-sm">
                <span className="text-slate-700 inline-flex items-center">
                  n_symbols
                  <HelpTip paramKey="emission.n_symbols" />
                </span>
                <input
                  type="number"
                  min={2}
                  value={model.nSymbols}
                  onChange={(e) => patch({ nSymbols: parseInt(e.target.value, 10) || 2 })}
                  className={inputCls + " w-40"}
                />
              </label>
            )}
            {mismatch && (
              <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
                ⚠ {mismatch}
              </p>
            )}
          </>
        )}

        {/* ---- Step 2: States ---- */}
        {stepIdx === 1 && (
          <>
            <label className="flex items-center justify-between gap-2 text-sm">
              <span className="text-slate-700 inline-flex items-center">
                Number of states (K)
                <HelpTip paramKey="scan.k_range" />
              </span>
              <input
                type="number"
                min={1}
                value={model.k}
                onChange={(e) => setK(parseInt(e.target.value, 10))}
                className={inputCls + " w-24"}
              />
            </label>
            <p className="text-xs text-slate-500">Optional: rename states (defaults s0…).</p>
            <div className="grid grid-cols-2 gap-2">
              {model.stateNames.map((nm, i) => (
                <input
                  key={i}
                  value={nm}
                  onChange={(e) => {
                    const names = [...model.stateNames];
                    names[i] = e.target.value;
                    patch({ stateNames: names });
                  }}
                  className={inputCls}
                />
              ))}
            </div>
            {!stepValid(1) && (
              <p className="text-xs text-red-700">State names must be non-empty and unique.</p>
            )}
          </>
        )}

        {/* ---- Step 3: Transitions ---- */}
        {stepIdx === 2 && (
          <>
            <span className="text-sm text-slate-700 inline-flex items-center">
              Transition shape
              <HelpTip paramKey="topology.allowed_transitions" />
            </span>
            <div className="space-y-2">
              {SHAPES.map((s) => (
                <label
                  key={s.id}
                  className={
                    "flex items-start gap-2 border rounded p-2 cursor-pointer " +
                    (model.shape === s.id ? "border-brand-400 bg-brand-50" : "border-slate-200")
                  }
                >
                  <input
                    type="radio"
                    name="shape"
                    checked={model.shape === s.id}
                    onChange={() => patch({ shape: s.id })}
                    className="mt-1"
                  />
                  <span>
                    <span className="font-medium text-sm">{s.label}</span>
                    <span className="block text-xs text-slate-500">{s.blurb}</span>
                  </span>
                </label>
              ))}
            </div>
            <p className="text-xs text-slate-500">
              Need a custom structure? Pick Ergodic now and draw the exact edges in the editor.
            </p>
          </>
        )}

        {/* ---- Step 4: Training ---- */}
        {stepIdx === 3 && (
          <>
            <p className="text-sm text-slate-600">
              Sensible defaults are filled in — most users can continue.
            </p>
            <button
              type="button"
              onClick={() => setShowAdvanced((v) => !v)}
              className="text-xs text-brand-700 hover:underline"
            >
              {showAdvanced ? "Hide" : "Show"} advanced training settings
            </button>
            {showAdvanced && (
              <div className="space-y-3 pt-2">
                <label className="flex items-center justify-between gap-2 text-sm">
                  <span className="text-slate-700 inline-flex items-center">
                    init strategy
                    <HelpTip paramKey="init.strategy" />
                  </span>
                  <select
                    value={model.initStrategy}
                    onChange={(e) =>
                      patch({ initStrategy: e.target.value as WizardModel["initStrategy"] })
                    }
                    className={inputCls + " w-40"}
                  >
                    <option value="uniform">uniform</option>
                    <option value="random">random</option>
                    <option value="kmeans">kmeans</option>
                    <option value="data_frequencies">data_frequencies</option>
                  </select>
                </label>
                <label className="flex items-center justify-between gap-2 text-sm">
                  <span className="text-slate-700 inline-flex items-center">
                    seed
                    <HelpTip paramKey="init.seed" />
                  </span>
                  <input
                    type="number"
                    value={model.seed}
                    onChange={(e) => patch({ seed: parseInt(e.target.value, 10) || 0 })}
                    className={inputCls + " w-40"}
                  />
                </label>
                <label className="flex items-center justify-between gap-2 text-sm">
                  <span className="text-slate-700 inline-flex items-center">
                    n_iter
                    <HelpTip paramKey="fit.n_iter" />
                  </span>
                  <input
                    type="number"
                    min={1}
                    value={model.nIter}
                    onChange={(e) => patch({ nIter: parseInt(e.target.value, 10) || 1 })}
                    className={inputCls + " w-40"}
                  />
                </label>
                <label className="flex items-center justify-between gap-2 text-sm">
                  <span className="text-slate-700 inline-flex items-center">
                    tol
                    <HelpTip paramKey="fit.tol" />
                  </span>
                  <input
                    type="number"
                    step={1e-5}
                    value={model.tol}
                    onChange={(e) => patch({ tol: parseFloat(e.target.value) || 1e-4 })}
                    className={inputCls + " w-40"}
                  />
                </label>
                <label className="flex items-center justify-between gap-2 text-sm">
                  <span className="text-slate-700 inline-flex items-center">
                    α (Dirichlet)
                    <HelpTip paramKey="priors.alpha" />
                  </span>
                  <input
                    type="number"
                    step={0.1}
                    min={0}
                    value={model.priorAlpha ?? ""}
                    placeholder="(MLE)"
                    onChange={(e) => {
                      const v = parseFloat(e.target.value);
                      patch({ priorAlpha: Number.isFinite(v) ? v : null });
                    }}
                    className={inputCls + " w-40"}
                  />
                </label>
              </div>
            )}
          </>
        )}

        {/* ---- Step 5: Review ---- */}
        {stepIdx === 4 && (
          <>
            <p className="text-sm text-slate-700">
              <strong>{model.k}-state {model.emissionType}</strong> model,{" "}
              <span className="font-mono">{model.shape}</span> transitions,{" "}
              <span className="font-mono">{model.initStrategy}</span> init.
            </p>
            <pre className="text-xs bg-slate-50 border border-slate-200 rounded p-3 overflow-x-auto whitespace-pre-wrap">
              {buildTopologyYaml(model)}
            </pre>
          </>
        )}
      </div>

      {error && (
        <p className="mb-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
          {error}
        </p>
      )}

      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={stepIdx === 0}
          onClick={() => setStepIdx((i) => Math.max(0, i - 1))}
          className={
            "px-4 py-2 rounded text-sm font-medium " +
            (stepIdx === 0
              ? "bg-slate-100 text-slate-400 cursor-not-allowed"
              : "bg-slate-200 text-slate-700 hover:bg-slate-300")
          }
        >
          Back
        </button>

        {!isLast ? (
          <button
            type="button"
            disabled={!stepValid(stepIdx)}
            onClick={() => setStepIdx((i) => Math.min(STEPS.length - 1, i + 1))}
            className={
              "px-4 py-2 rounded text-sm font-medium " +
              (stepValid(stepIdx)
                ? "bg-brand-600 text-white hover:bg-brand-700"
                : "bg-slate-200 text-slate-500 cursor-not-allowed")
            }
          >
            Next
          </button>
        ) : (
          <>
            <button
              type="button"
              onClick={() => finish(false)}
              className="px-4 py-2 rounded text-sm font-medium bg-brand-600 text-white hover:bg-brand-700"
            >
              Finish → open in editor
            </button>
            {dataset && (
              <button
                type="button"
                onClick={() => finish(true)}
                className="px-4 py-2 rounded text-sm font-medium bg-slate-200 text-slate-700 hover:bg-slate-300"
              >
                Finish & go to Fit
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2:** `npm run lint` → clean (watch strict unused-vars). 
- [ ] **Step 3: Commit** → `feat(ui): 5-step guided model creation wizard`

---

### Task 3: route + entry button

**Files:** Modify `App.tsx`, `TopologyPage.tsx`

- [ ] **Step 1: Route.** In `App.tsx` add `import WizardPage from "./pages/WizardPage";` and, next to the `topology` route, add:
```tsx
        <Route path="topology/new" element={<WizardPage />} />
```

- [ ] **Step 2: Entry button.** In `TopologyPage.tsx`, add `import { Link } from "react-router-dom";` if not already imported, and place a prominent link near the top of the page (above/near the editor controls):
```tsx
<Link
  to="/topology/new"
  className="inline-block px-3 py-1.5 rounded text-sm font-medium bg-brand-600 text-white hover:bg-brand-700"
>
  ✨ New guided model
</Link>
```
(Place it where the page header / toolbar is; do not disturb the existing editor. If `Link` is already imported, don't duplicate.)

- [ ] **Step 3:** `npm run lint` → clean.
- [ ] **Step 4: Commit** → `feat(ui): wire /topology/new route + "New guided model" entry`

---

### Task 4: build + CHANGELOG + spec done-check

**Files:** Modify `CHANGELOG.md`, `docs/specs/2026-05-27-guided-creation-wizard.md`

- [ ] **Step 1:** `npm run build` → tsc clean + bundle.
- [ ] **Step 2:** CHANGELOG `[Unreleased]` → `### Added`:
```markdown
- Guided model creation: a "✨ New guided model" wizard (`/topology/new`) walks
  you through Emission → States → Transitions → Training → Review (data-aware
  emission suggestion, transition-shape presets, sensible training defaults) and
  loads the result into the editor pre-filled. Reuses the topology-load path and
  the param-help copy. Coexists with the free-form editor.
```
- [ ] **Step 3:** Append to the spec:
```markdown
## Update 2026-05-27 — shipped

Implemented per plan. Validated via `npm run build`. Pure core
(`buildTopologyYaml` / `suggestEmission` / `allowedTransitionsForShape`) is
unit-test-ready should Vitest be added (gap stands).
```
- [ ] **Step 4: Commit** → `docs(ui): changelog + spec done-check for guided wizard`

## Definition of done
- [ ] `/topology/new` wizard (5 steps, validation, progress) + entry button.
- [ ] Pure `buildTopologyYaml` / `suggestEmission` / `allowedTransitionsForShape`.
- [ ] Data-aware emission step + mismatch warning; HelpTips on steps.
- [ ] Finish → editor pre-filled; "Finish & go to Fit" when a dataset is loaded.
- [ ] `npm run build` clean; CHANGELOG + spec updated.

## Self-review
- **Spec coverage:** 5 steps, data-aware (suggestEmission), presets (allowedTransitionsForShape), training defaults+advanced, review w/ YAML preview, handoff via yamlToTopology+loadTopology, coexists — all present. ✓
- **Types:** `WizardModel` fields consistent across `buildTopologyYaml.ts` and `WizardPage.tsx`; `paramKey`s used (`emission.*`, `init.*`, `fit.*`, `priors.alpha`, `scan.k_range`, `topology.allowed_transitions`) exist in `paramHelp` (verify `topology.allowed_transitions` is present — it is, per the registry table). ✓
- **No new dep:** only `js-yaml` (already used by `lib/yaml.ts`), react, react-router. ✓
