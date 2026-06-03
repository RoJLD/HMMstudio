# Topology Editor — Increment 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the 5 round-2 user asks: ergodic topologies show their arrows; a named-saved-models stop-gap stops data loss; a dataset-gated "Fit this topology" button; learned transition probabilities overlaid on the editor arrows via a tri-state none/prior/learned toggle; and self-loops + readable bidirectional edges + a one-click Tidy auto-layout.

**Architecture:** Pure helpers in `src/lib/` (fingerprint, learned-overlay map, auto-layout) are unit-tested in isolation, then wired into the editor. A new UI-only `fitLinkStore` links the editor to its last fit (job id + topology fingerprint) WITHOUT polluting the pure topology model. The existing `probEdgeStyle` and `/api/fit/{jobId}/transmat` are reused unchanged. Custom React Flow edge types (`selfLoop`, `curved`) are introduced via an `edgeTypes` registry. No backend changes.

**Tech Stack:** React 18 + TS + Vite 5, React Flow 11.11, zustand 4 + zundo 2, vitest (Increment 1), Playwright (`e2e/`).

**Spec:** [`docs/superpowers/specs/2026-06-02-topology-editor-ux-overhaul-design.md`](../specs/2026-06-02-topology-editor-ux-overhaul-design.md) — see "Update 2026-06-03 — Round 2" for the design + arbitrations this plan executes.

**Preconditions (not tasks):**
- Work in the worktree root `C:\Users\rdenis\VScode\Tools\hmm_studio-topology-ux` on branch `feat/topology-editor-ux` (continues from Increment 1; `main` already has Increment 1). Frontend commands from `src/hmm_studio/frontend`.
- Commit identity = `roblastar@live.fr`; append `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` to every commit.
- Do NOT use gitnexus tools (stale index in this worktree); read code directly.
- Browser-visual steps: substitute with `npm run lint` + `npm run build` passing + reasoning; flag human visual QA.

---

## Shared contracts (read before any lot)

These cross-lot pieces are defined once here so every lot uses consistent names/signatures.

- **`topologyFingerprint(states, transitions): string`** (`src/lib/topologyFingerprint.ts`) — a stable string from the SORTED state names + SORTED `sourceName→targetName` pairs. Used to detect "topology changed since the fit" (lots H + G). Names are the only key that survives the fit round-trip.
- **`fitLinkStore`** (`src/store/fitLinkStore.ts`) — UI/side zustand+persist store, OWN localStorage key, NOT `topologyStore` (so it never enters undo/serialised model). Shape: `{ lastFitJobId: string | null; fitFingerprint: string | null; setFitLink(jobId, fingerprint): void; clearFitLink(): void }`. Written by lot H at fit-submit; read by lot G.
- **`overlayMode: 'none' | 'prior' | 'learned'`** (replaces the boolean `showPriorPreview` in `editorPrefsStore`, lot G) — with a persist `migrate` mapping the old `showPriorPreview:true → 'prior'`, else `'none'`.
- **`buildLearnedMap(transitions, states, transmat): Map<edgeId, number>`** (`src/lib/learnedOverlay.ts`, lot G) — joins `transmat[i][j]` to editor edges by STATE NAME (`state_names[i]`).
- **`setPositions(positions: Record<stateId, {x,y}>): void`** (new `topologyStore` action, lot J / P-3) — updates ALL state positions in ONE `set()` so a Tidy is a single undo entry.
- **`edgeTypes` registry** (`src/components/topology/edgeTypes.ts`, lot J / P-1) — `{ selfLoop: SelfLoopEdge, curved: CurvedEdge }`, passed to `<ReactFlow edgeTypes={edgeTypes}>`; edge `type` chosen per-edge in `EditorCanvas`.
- **`autoLayout(states, transitions, mode): Record<stateId, {x,y}>`** (`src/lib/autoLayout.ts`, lot J / F.4) — pure; `mode: 'left-right' | 'circular'`.

---

## Lot F.1 — Ergodic topologies show their arrows (quick win)

**Why:** `allowedTransitionsForShape('ergodic', names)` returns `[]`, so `buildTopologyYaml` omits `allowed_transitions`, so an ergodic model has ZERO transitions in the store and renders ZERO arrows. Ergodic means all-to-all — materialize every pair (including self-loops) so the arrows appear and are individually editable.

### Task 1: Materialize ergodic transitions

**Files:**
- Modify: `src/hmm_studio/frontend/src/lib/buildTopologyYaml.ts` (`allowedTransitionsForShape`)
- Create: `src/hmm_studio/frontend/src/lib/buildTopologyYaml.test.ts`

- [ ] **Step 1: Write the failing test.** Create `src/hmm_studio/frontend/src/lib/buildTopologyYaml.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { allowedTransitionsForShape } from "./buildTopologyYaml";

describe("allowedTransitionsForShape", () => {
  it("ergodic → every ordered pair including self-loops (K²)", () => {
    const names = ["s0", "s1", "s2"];
    const pairs = allowedTransitionsForShape("ergodic", names);
    expect(pairs).toHaveLength(9); // 3×3
    // self-loops present
    expect(pairs).toContainEqual(["s0", "s0"]);
    expect(pairs).toContainEqual(["s2", "s2"]);
    // a forward and a backward edge present (all-to-all)
    expect(pairs).toContainEqual(["s0", "s2"]);
    expect(pairs).toContainEqual(["s2", "s0"]);
  });

  it("left-right keeps self-loop + forward only", () => {
    const pairs = allowedTransitionsForShape("left-right", ["s0", "s1", "s2"]);
    expect(pairs).toContainEqual(["s0", "s0"]);
    expect(pairs).toContainEqual(["s0", "s1"]);
    expect(pairs).not.toContainEqual(["s1", "s0"]); // no going back
    expect(pairs).not.toContainEqual(["s0", "s2"]); // no skip
  });

  it("bakis adds skip-one", () => {
    const pairs = allowedTransitionsForShape("bakis", ["s0", "s1", "s2"]);
    expect(pairs).toContainEqual(["s0", "s2"]);
  });
});
```

- [ ] **Step 2: Run `npm test -- buildTopologyYaml`** → FAIL (the ergodic test: current code returns `[]`).

- [ ] **Step 3: Implement.** In `buildTopologyYaml.ts`, replace the `if (shape === "ergodic") return [];` early-return at the top of `allowedTransitionsForShape` with a materialized full mesh:

```ts
export function allowedTransitionsForShape(shape: TransitionShape, names: string[]): string[][] {
  if (shape === "ergodic") {
    // Materialize the full mesh (incl. self-loops) so ergodic models show
    // editable arrows instead of zero. Semantically identical to an omitted
    // mask (all transitions allowed), but now visible + per-edge-prior-able.
    const pairs: string[][] = [];
    for (const a of names) for (const b of names) pairs.push([a, b]);
    return pairs;
  }
  const pairs: string[][] = [];
  const K = names.length;
  for (let i = 0; i < K; i++) {
    pairs.push([names[i], names[i]]); // self-loop
    if (i + 1 < K) pairs.push([names[i], names[i + 1]]); // forward
    if (shape === "bakis" && i + 2 < K) pairs.push([names[i], names[i + 2]]); // skip-one
  }
  return pairs;
}
```

- [ ] **Step 4: Run `npm test -- buildTopologyYaml`** → PASS (3).

- [ ] **Step 5: Lint + build.** `npm run lint` (0), `npm run build` (0), `npm test` (full suite green).

- [ ] **Step 6: (visual — substitute)** Reason: the wizard's default shape is `ergodic` (WizardPage initial), so finishing a guided ergodic model now seeds K² transitions → `EditorCanvas.transitions.map` renders K² arrows. Note human QA: a guided 3-state ergodic model now shows 9 arrows (incl. self-loops, which render poorly until lot F.2 — that's expected and fixed there).

- [ ] **Step 7: Commit.**

```bash
git add src/hmm_studio/frontend/src/lib/buildTopologyYaml.ts src/hmm_studio/frontend/src/lib/buildTopologyYaml.test.ts
git commit -m "feat(topology): ergodic shape materializes its full-mesh arrows (F.1)"
```

---

## Lot I — Named-saved-models stop-gap (prevents data loss)

**Why:** `loadTopology` (wizard finish, YAML import, shared-URL hydrate, Academy try-in-editor) OVERWRITES the current model in place — opening a new guided model silently destroys the open one. Ship the lightweight A2 stop-gap: a sibling store of named saved topologies + a switcher + a "save current first?" guard on the clobber paths. (True multi-tab A1 is on the roadmap; this `saved` map is its exact data structure — a stepping stone, not throwaway.)

### Task 2: `savedTopologiesStore` + pure save/load reducers

**Files:**
- Create: `src/hmm_studio/frontend/src/store/savedTopologiesStore.ts`
- Create: `src/hmm_studio/frontend/src/store/savedTopologiesStore.test.ts`

- [ ] **Step 1: Write the failing test.** Create `src/hmm_studio/frontend/src/store/savedTopologiesStore.test.ts`:

```ts
import { describe, it, expect, beforeEach } from "vitest";
import { useSavedTopologies, type SavedTopology } from "./savedTopologiesStore";

const demo = (name: string): SavedTopology => ({
  name,
  data: {
    name,
    states: [{ id: "a", name: "s0", position: { x: 0, y: 0 } }],
    transitions: [],
    emission: { type: "gaussian", n_features: 1, covariance_type: "full", n_mix: null, n_symbols: null },
    startprob: "uniform",
    init: { strategy: "kmeans", seed: 42 },
    fit: { algorithm: "baum_welch", n_iter: 200, tol: 1e-4 },
    transmat_prior_alpha: null,
  },
  savedAt: 0,
});

describe("savedTopologiesStore", () => {
  beforeEach(() => useSavedTopologies.setState({ saved: {} }));

  it("save then list", () => {
    useSavedTopologies.getState().save(demo("alpha"));
    expect(Object.keys(useSavedTopologies.getState().saved)).toEqual(["alpha"]);
  });

  it("save overwrites a same-name entry", () => {
    useSavedTopologies.getState().save(demo("alpha"));
    useSavedTopologies.getState().save(demo("alpha"));
    expect(Object.keys(useSavedTopologies.getState().saved)).toHaveLength(1);
  });

  it("remove deletes by name", () => {
    useSavedTopologies.getState().save(demo("alpha"));
    useSavedTopologies.getState().remove("alpha");
    expect(useSavedTopologies.getState().saved).toEqual({});
  });
});
```

- [ ] **Step 2: Run `npm test -- savedTopologiesStore`** → FAIL (module missing).

- [ ] **Step 3: Implement.** Create `src/hmm_studio/frontend/src/store/savedTopologiesStore.ts`:

```ts
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { TopologyData } from "./topologyStore";

export interface SavedTopology {
  name: string;
  data: TopologyData;
  savedAt: number;
}

interface SavedTopologiesState {
  saved: Record<string, SavedTopology>;
  save: (entry: SavedTopology) => void;
  remove: (name: string) => void;
}

// Sibling of topologyStore (NOT the active model): a named library of saved
// topologies. Own localStorage key; no undo. This is the A2 stop-gap and the
// exact data shape the future multi-tab (A1) docs-map will reuse.
export const useSavedTopologies = create<SavedTopologiesState>()(
  persist(
    (set) => ({
      saved: {},
      save: (entry) =>
        set((s) => ({ saved: { ...s.saved, [entry.name]: entry } })),
      remove: (name) =>
        set((s) => {
          const next = { ...s.saved };
          delete next[name];
          return { saved: next };
        }),
    }),
    {
      name: "hmm-studio-saved-topologies",
      storage: createJSONStorage(() => localStorage),
    },
  ),
);
```

- [ ] **Step 4: Run `npm test -- savedTopologiesStore`** → PASS (3).

- [ ] **Step 5: Lint** (`npm run lint`, 0). **Commit.**

```bash
git add src/hmm_studio/frontend/src/store/savedTopologiesStore.ts src/hmm_studio/frontend/src/store/savedTopologiesStore.test.ts
git commit -m "feat(topology): savedTopologies sibling store (A2 stop-gap core)"
```

### Task 3: "Save / Load / Delete" switcher in the Toolbar

**Files:**
- Modify: `src/hmm_studio/frontend/src/components/topology/Toolbar.tsx`

- [ ] **Step 1: Add the switcher.** In `Toolbar.tsx`, add imports:

```ts
import { useTopologyStore } from "../../store/topologyStore";
import { useSavedTopologies } from "../../store/savedTopologiesStore";
```

Inside the component, add reads + handlers (place near the existing store reads):

```ts
  const saved = useSavedTopologies((s) => s.saved);
  const saveModel = useSavedTopologies((s) => s.save);
  const removeModel = useSavedTopologies((s) => s.remove);

  function handleSaveCurrent() {
    const st = useTopologyStore.getState();
    if (st.states.length === 0) return;
    const name = window.prompt("Save current model as:", st.name || "untitled");
    if (!name) return;
    const { name: _n, states, transitions, emission, startprob, init, fit, transmat_prior_alpha } = st;
    saveModel({
      name,
      data: { name, states, transitions, emission, startprob, init, fit, transmat_prior_alpha },
      savedAt: Date.now(),
    });
  }

  function handleLoadSaved(name: string) {
    const entry = saved[name];
    if (!entry) return;
    useTopologyStore.getState().loadTopology(entry.data);
  }
```

> Note: `Date.now()` is fine in the app (the no-Date constraint applies only to Workflow scripts, not app code).

Add this control block just before the toolbar's closing `</div>` (after the prior-preview / re-validate controls):

```tsx
      <div className="w-px h-6 bg-slate-300" />
      <button onClick={handleSaveCurrent} className={btn}>💾 Save model</button>
      <select
        className={btn}
        value=""
        onChange={(e) => {
          const v = e.target.value;
          if (v) handleLoadSaved(v);
          e.target.value = "";
        }}
      >
        <option value="">📂 Load saved…</option>
        {Object.keys(saved).map((n) => (
          <option key={n} value={n}>{n}</option>
        ))}
      </select>
      {Object.keys(saved).length > 0 && (
        <select
          className={btn}
          value=""
          onChange={(e) => {
            const v = e.target.value;
            if (v && window.confirm(`Delete saved model "${v}"?`)) removeModel(v);
            e.target.value = "";
          }}
        >
          <option value="">🗑 Delete…</option>
          {Object.keys(saved).map((n) => (
            <option key={n} value={n}>{n}</option>
          ))}
        </select>
      )}
```

- [ ] **Step 2: Lint + build** (both 0). **Step 3: (visual — substitute)** Reason through: Save prompts for a name and writes the current model into the saved map (persisted); Load replaces the active model via the existing `loadTopology`; Delete confirms then removes. Note: loading a saved model still goes through `loadTopology` which clobbers the active model — Task 4 adds the guard so you don't lose unsaved work.

- [ ] **Step 4: Commit.**

```bash
git add src/hmm_studio/frontend/src/components/topology/Toolbar.tsx
git commit -m "feat(topology): save/load/delete named models switcher (A2)"
```

### Task 4: "Save current first?" guard on the clobber paths

**Why:** `loadTopology` (wizard finish, import, share hydrate, Academy try-in-editor) destroys a non-empty active model. Add a shared guard that, when the current model is non-empty, asks to save it first.

**Files:**
- Create: `src/hmm_studio/frontend/src/lib/guardClobber.ts`
- Create: `src/hmm_studio/frontend/src/lib/guardClobber.test.ts`
- Modify: `src/hmm_studio/frontend/src/pages/WizardPage.tsx` (`finish`)
- Modify: `src/hmm_studio/frontend/src/pages/TopologyPage.tsx` (import + share hydrate)

- [ ] **Step 1: Write the failing test (pure decision helper).** Create `src/hmm_studio/frontend/src/lib/guardClobber.test.ts`:

```ts
import { describe, it, expect, vi } from "vitest";
import { confirmClobber } from "./guardClobber";

describe("confirmClobber", () => {
  it("returns true immediately when the current model is empty (no prompt)", () => {
    const onSave = vi.fn();
    expect(confirmClobber(0, onSave, () => false)).toBe(true);
    expect(onSave).not.toHaveBeenCalled();
  });

  it("non-empty + user cancels confirm → false (abort clobber)", () => {
    const onSave = vi.fn();
    expect(confirmClobber(3, onSave, () => false, () => false)).toBe(false);
  });

  it("non-empty + user chooses to save → calls onSave then returns true", () => {
    const onSave = vi.fn();
    expect(confirmClobber(3, onSave, () => true)).toBe(true);
    expect(onSave).toHaveBeenCalledOnce();
  });
});
```

- [ ] **Step 2: Run `npm test -- guardClobber`** → FAIL.

- [ ] **Step 3: Implement.** Create `src/hmm_studio/frontend/src/lib/guardClobber.ts`:

```ts
/** Decide whether to proceed with an action that REPLACES the current model.
 *  Pure + injectable prompts for testability.
 *  - currentStateCount === 0 → proceed silently (nothing to lose).
 *  - else ask "save current first?": if yes → onSave() then proceed; if the
 *    user dismisses the save dialog, still ask a final confirm to proceed.
 *  Returns true to proceed with the clobber, false to abort.
 *  `wantSave`/`confirmProceed` default to window.confirm in the app. */
export function confirmClobber(
  currentStateCount: number,
  onSave: () => void,
  wantSave: () => boolean = () => window.confirm("Save the current model before replacing it?"),
  confirmProceed: () => boolean = () => window.confirm("Replace the current model without saving?"),
): boolean {
  if (currentStateCount === 0) return true;
  if (wantSave()) {
    onSave();
    return true;
  }
  return confirmProceed();
}
```

- [ ] **Step 4: Run `npm test -- guardClobber`** → PASS (3).

- [ ] **Step 5: Wire into WizardPage.finish.** In `WizardPage.tsx`, add imports:

```ts
import { confirmClobber } from "../lib/guardClobber";
import { useSavedTopologies } from "../store/savedTopologiesStore";
```

Replace the body of `finish` so it guards before clobbering:

```ts
  function finish(goToFit: boolean) {
    setError(null);
    try {
      const cur = useTopologyStore.getState();
      const proceed = confirmClobber(cur.states.length, () => {
        const { name, states, transitions, emission, startprob, init, fit, transmat_prior_alpha } = cur;
        useSavedTopologies.getState().save({
          name: name || "untitled",
          data: { name, states, transitions, emission, startprob, init, fit, transmat_prior_alpha },
          savedAt: Date.now(),
        });
      });
      if (!proceed) return;
      const partial = yamlToTopology(buildTopologyYaml(model));
      useTopologyStore.getState().loadTopology(partial);
      navigate(goToFit ? "/fit" : "/topology");
    } catch (e) {
      setError(e instanceof Error ? e.message : "could not build topology");
    }
  }
```

- [ ] **Step 6: Wire into TopologyPage import + share hydrate.** In `TopologyPage.tsx`, add imports:

```ts
import { confirmClobber } from "../lib/guardClobber";
import { useSavedTopologies } from "../store/savedTopologiesStore";
```

Add a shared helper inside the component and use it in both `handleImportFile` and the mount share-hydrate effect:

```ts
  function saveCurrent() {
    const st = useTopologyStore.getState();
    const { name, states, transitions, emission, startprob, init, fit, transmat_prior_alpha } = st;
    useSavedTopologies.getState().save({
      name: name || "untitled",
      data: { name, states, transitions, emission, startprob, init, fit, transmat_prior_alpha },
      savedAt: Date.now(),
    });
  }
```

In `handleImportFile`, before `loadTopology(partial)`:

```ts
        const partial = yamlToTopology(text);
        const cur = useTopologyStore.getState();
        if (!confirmClobber(cur.states.length, saveCurrent)) return;
        useTopologyStore.getState().loadTopology(partial);
```

In the mount effect, before `loadTopology(shared)` (the share-URL hydrate), apply the same guard:

```ts
      const cur = useTopologyStore.getState();
      if (!confirmClobber(cur.states.length, saveCurrent)) { clearTopologyParam(); return; }
      useTopologyStore.getState().loadTopology(shared);
```

> Academy "Try in editor" (`LessonPage.handleTryInEditor`) uses the same `loadTopology` clobber — apply the identical guard there if you touch it; out of scope for this task if `LessonPage` is not in the editor flow, note it as a follow-up.

- [ ] **Step 7: Lint + build** (0). **Step 8: (visual — substitute)** Reason: with a non-empty model open, "New guided model → Finish", "Import YAML", and opening a shared URL now prompt to save first; an empty editor proceeds silently. Note human QA on the 3 paths.

- [ ] **Step 9: Commit.**

```bash
git add src/hmm_studio/frontend/src/lib/guardClobber.ts src/hmm_studio/frontend/src/lib/guardClobber.test.ts src/hmm_studio/frontend/src/pages/WizardPage.tsx src/hmm_studio/frontend/src/pages/TopologyPage.tsx
git commit -m "feat(topology): save-current-first guard on model-clobber paths (A2)"
```

---

## Lot H — "Fit this topology" button (validate stays structural)

**Why:** The user asked that editing transitions then clicking validate recompute everything. Decision (spec): do NOT couple validate→fit (validate is free + debounced on every edit; a fit is a slow async dataset-gated EM job). Instead add an explicit dataset-gated "Fit this topology" button IN the editor. It is ALSO where the fit's `job_id` + topology fingerprint get captured — the prerequisite for lot G's learned overlay.

### Task 5: `topologyFingerprint` helper + `fitLinkStore`

**Files:**
- Create: `src/hmm_studio/frontend/src/lib/topologyFingerprint.ts` + `.test.ts`
- Create: `src/hmm_studio/frontend/src/store/fitLinkStore.ts`

- [ ] **Step 1: Write the failing test.** Create `src/hmm_studio/frontend/src/lib/topologyFingerprint.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { topologyFingerprint } from "./topologyFingerprint";

type S = { id: string; name: string; position: { x: number; y: number } };
type T = { id: string; source: string; target: string };

const states: S[] = [
  { id: "a", name: "s0", position: { x: 0, y: 0 } },
  { id: "b", name: "s1", position: { x: 9, y: 9 } },
];
const trans: T[] = [{ id: "e1", source: "a", target: "b" }];

describe("topologyFingerprint", () => {
  it("is invariant to position changes and transition order", () => {
    const fp1 = topologyFingerprint(states, trans);
    const moved = states.map((s) => ({ ...s, position: { x: 99, y: 99 } }));
    const reordered: T[] = [{ id: "e1", source: "a", target: "b" }];
    expect(topologyFingerprint(moved, reordered)).toBe(fp1);
  });

  it("changes when a state is renamed", () => {
    const fp1 = topologyFingerprint(states, trans);
    const renamed = states.map((s) => (s.id === "b" ? { ...s, name: "X" } : s));
    expect(topologyFingerprint(renamed, trans)).not.toBe(fp1);
  });

  it("changes when a transition is added", () => {
    const fp1 = topologyFingerprint(states, trans);
    const more: T[] = [...trans, { id: "e2", source: "b", target: "a" }];
    expect(topologyFingerprint(states, more)).not.toBe(fp1);
  });
});
```

- [ ] **Step 2: Run `npm test -- topologyFingerprint`** → FAIL.

- [ ] **Step 3: Implement.** Create `src/hmm_studio/frontend/src/lib/topologyFingerprint.ts`:

```ts
interface FpState { id: string; name: string }
interface FpEdge { source: string; target: string }

/** Stable identity of a topology's STRUCTURE (names + edges), independent of
 *  node positions and edge order. Used to detect "the topology changed since
 *  the fit" so a learned-probability overlay can be shown only when it still
 *  matches. Names are the join key that survives the fit YAML round-trip. */
export function topologyFingerprint(states: FpState[], transitions: FpEdge[]): string {
  const idToName = new Map(states.map((s) => [s.id, s.name]));
  const names = states.map((s) => s.name).slice().sort();
  const pairs = transitions
    .map((t) => `${idToName.get(t.source) ?? t.source}>${idToName.get(t.target) ?? t.target}`)
    .sort();
  return JSON.stringify({ names, pairs });
}
```

- [ ] **Step 4: Run `npm test -- topologyFingerprint`** → PASS (3).

- [ ] **Step 5: Create the fit-link store.** Create `src/hmm_studio/frontend/src/store/fitLinkStore.ts`:

```ts
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

// Links the editor to its most recent fit WITHOUT polluting the pure topology
// model: a UI/side store (own localStorage key, no undo, not in topologyStore).
// lot G reads this to overlay learned probabilities; the fingerprint lets it
// detect a topology that changed since the fit and refuse stale numbers.
interface FitLinkState {
  lastFitJobId: string | null;
  fitFingerprint: string | null;
  setFitLink: (jobId: string, fingerprint: string) => void;
  clearFitLink: () => void;
}

export const useFitLink = create<FitLinkState>()(
  persist(
    (set) => ({
      lastFitJobId: null,
      fitFingerprint: null,
      setFitLink: (jobId, fingerprint) =>
        set({ lastFitJobId: jobId, fitFingerprint: fingerprint }),
      clearFitLink: () => set({ lastFitJobId: null, fitFingerprint: null }),
    }),
    {
      name: "hmm-studio-fit-link",
      storage: createJSONStorage(() => localStorage),
    },
  ),
);
```

- [ ] **Step 6: Lint** (0). **Commit.**

```bash
git add src/hmm_studio/frontend/src/lib/topologyFingerprint.ts src/hmm_studio/frontend/src/lib/topologyFingerprint.test.ts src/hmm_studio/frontend/src/store/fitLinkStore.ts
git commit -m "feat(topology): topologyFingerprint + fitLink store (H/G prerequisite)"
```

### Task 6: "Fit this topology" button in the editor

**Files:**
- Modify: `src/hmm_studio/frontend/src/components/topology/Toolbar.tsx`

- [ ] **Step 1: Add the button + handler.** In `Toolbar.tsx`, add imports:

```ts
import { useNavigate } from "react-router-dom";
import { useDatasetStore } from "../../store/datasetStore";
import { startFit } from "../../api/client";
import { topologyToYAML } from "../../lib/yaml";
import { topologyFingerprint } from "../../lib/topologyFingerprint";
import { useFitLink } from "../../store/fitLinkStore";
```

Inside the component, add:

```ts
  const navigate = useNavigate();
  const dataset = useDatasetStore((s) => s.current);
  const statesForFit = useTopologyStore((s) => s.states);
  const setFitLink = useFitLink((s) => s.setFitLink);
  const [fitting, setFitting] = useState(false);

  async function handleFit() {
    if (!dataset || statesForFit.length === 0) return;
    setFitting(true);
    try {
      const st = useTopologyStore.getState();
      const result = await startFit({
        topology_yaml: topologyToYAML(st),
        dataset_id: dataset.id,
      });
      setFitLink(result.id, topologyFingerprint(st.states, st.transitions));
      navigate(`/results/${result.id}`);
    } catch (e) {
      // eslint-disable-next-line no-alert
      alert(`Fit failed: ${e instanceof Error ? e.message : "?"}`);
      setFitting(false);
    }
  }
```

(Add `useState` to the React import: `import { useState } from "react";` at the top if not already present.)

Add this control just after the "+ state" button group (so it's prominent):

```tsx
      <div className="w-px h-6 bg-slate-300" />
      <button
        onClick={handleFit}
        disabled={!dataset || statesForFit.length === 0 || fitting}
        title={dataset ? `Fit on ${dataset.filename}` : "Select a dataset on the Data page first"}
        className={btn}
      >
        {fitting ? "Fitting…" : "▶ Fit this topology"}
      </button>
      {dataset ? (
        <span className="text-xs text-slate-400">on {dataset.filename}</span>
      ) : (
        <span className="text-xs text-amber-600">no dataset — pick one on Data</span>
      )}
```

- [ ] **Step 2: Lint + build** (0), `npm test` green.

- [ ] **Step 3: (visual — substitute)** Reason: the button is disabled with a clear hint until a dataset is selected (reuses the global `datasetStore.current`, the same one FitPage uses). On click it serializes the current topology, calls the EXISTING `/api/fit/start` (no backend change), captures `lastFitJobId` + fingerprint into `fitLinkStore`, and navigates to `/results/{id}` (same flow as FitPage). Note human QA: pick a dataset on Data, open the editor, click Fit → lands on Results; `fitLinkStore` now holds the job id (verify via localStorage `hmm-studio-fit-link`).

- [ ] **Step 4: Commit.**

```bash
git add src/hmm_studio/frontend/src/components/topology/Toolbar.tsx
git commit -m "feat(topology): dataset-gated 'Fit this topology' button (H)"
```

---

## Lot G — Learned probabilities on arrows + tri-state toggle (none / prior / learned)

**Why:** The user wants the actual learned transition probabilities on the arrows. Reuse the shared `probEdgeStyle`; the only missing piece is the DATA (lot H captured the fit link). Replace the boolean prior-preview toggle with a tri-state `none / prior / learned` segmented control. `learned` joins `transmat[i][j]` to editor edges by STATE NAME and is guarded by the topology fingerprint so a changed topology never shows wrong numbers.

### Task 7: Migrate `editorPrefsStore` to `overlayMode` (+ update consumers)

**Files:**
- Modify: `src/hmm_studio/frontend/src/store/editorPrefsStore.ts`
- Create: `src/hmm_studio/frontend/src/store/editorPrefsStore.test.ts`
- Modify: `src/hmm_studio/frontend/src/components/topology/EditorCanvas.tsx`
- Modify: `src/hmm_studio/frontend/src/components/topology/Toolbar.tsx`

- [ ] **Step 1: Write the failing test (pure migrate fn).** Create `src/hmm_studio/frontend/src/store/editorPrefsStore.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { migrateEditorPrefs } from "./editorPrefsStore";

describe("migrateEditorPrefs", () => {
  it("v0 showPriorPreview:true → overlayMode:'prior'", () => {
    expect(migrateEditorPrefs({ showPriorPreview: true }, 0)).toEqual({ overlayMode: "prior" });
  });
  it("v0 showPriorPreview:false → overlayMode:'none'", () => {
    expect(migrateEditorPrefs({ showPriorPreview: false }, 0)).toEqual({ overlayMode: "none" });
  });
  it("already-migrated state passes through", () => {
    expect(migrateEditorPrefs({ overlayMode: "learned" }, 1)).toEqual({ overlayMode: "learned" });
  });
});
```

- [ ] **Step 2: Run `npm test -- editorPrefsStore`** → FAIL.

- [ ] **Step 3: Implement the store.** Replace `src/hmm_studio/frontend/src/store/editorPrefsStore.ts` with:

```ts
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

export type OverlayMode = "none" | "prior" | "learned";

// UI-only editor preferences. SEPARATE from topologyStore so toggling them is
// not undoable and does not enter the serialised model.
interface EditorPrefs {
  overlayMode: OverlayMode;
  setOverlayMode: (m: OverlayMode) => void;
}

/** Persist migration: v0 stored a boolean `showPriorPreview`; v1 stores
 *  `overlayMode`. Pure + exported for testing. */
export function migrateEditorPrefs(
  persisted: unknown,
  version: number,
): { overlayMode: OverlayMode } {
  if (version < 1 && persisted && typeof (persisted as { showPriorPreview?: unknown }).showPriorPreview === "boolean") {
    return { overlayMode: (persisted as { showPriorPreview: boolean }).showPriorPreview ? "prior" : "none" };
  }
  const m = (persisted as { overlayMode?: OverlayMode } | null)?.overlayMode;
  return { overlayMode: m ?? "none" };
}

export const useEditorPrefs = create<EditorPrefs>()(
  persist(
    (set) => ({
      overlayMode: "none",
      setOverlayMode: (m) => set({ overlayMode: m }),
    }),
    {
      name: "hmm-studio-editor-prefs",
      storage: createJSONStorage(() => localStorage),
      version: 1,
      migrate: (persisted, version) => migrateEditorPrefs(persisted, version) as EditorPrefs,
    },
  ),
);
```

- [ ] **Step 4: Run `npm test -- editorPrefsStore`** → PASS (3).

- [ ] **Step 5: Update EditorCanvas to read overlayMode.** In `EditorCanvas.tsx`, change the import + the preview gate:

Replace `import { useEditorPrefs } from "../../store/editorPrefsStore";` usage:

```ts
  const overlayMode = useEditorPrefs((s) => s.overlayMode);
```

Replace the `const previews = showPriorPreview ? ... : null;` line with:

```ts
  const previews =
    overlayMode === "prior" ? priorMeanPreview(transitions, transmatPriorAlpha) : null;
```

(`learned` is wired in Task 9; for now it falls through to the default gray arrows — build stays green.)

- [ ] **Step 6: Update the Toolbar control to a tri-state segmented control.** In `Toolbar.tsx`, change the editorPrefs import/reads:

```ts
import { useEditorPrefs, type OverlayMode } from "../../store/editorPrefsStore";
```
```ts
  const overlayMode = useEditorPrefs((s) => s.overlayMode);
  const setOverlayMode = useEditorPrefs((s) => s.setOverlayMode);
```

Replace the old `prior preview` checkbox `<label>…</label>` block with:

```tsx
      <div className="w-px h-6 bg-slate-300" />
      <div className="inline-flex rounded border border-slate-300 overflow-hidden text-sm">
        {(["none", "prior", "learned"] as OverlayMode[]).map((m) => (
          <button
            key={m}
            onClick={() => setOverlayMode(m)}
            className={
              "px-2 py-1 " +
              (overlayMode === m ? "bg-brand-600 text-white" : "bg-white text-slate-600 hover:bg-slate-50")
            }
            title={
              m === "none" ? "No probabilities"
              : m === "prior" ? "Prior mean (expected P before fit)"
              : "Learned probabilities (after a fit)"
            }
          >
            {m === "none" ? "—" : m}
          </button>
        ))}
      </div>
```

(The `learned` button's enable/stale logic is added in Task 9.)

- [ ] **Step 7: Lint + build** (0), `npm test` green.

- [ ] **Step 8: Commit.**

```bash
git add src/hmm_studio/frontend/src/store/editorPrefsStore.ts src/hmm_studio/frontend/src/store/editorPrefsStore.test.ts src/hmm_studio/frontend/src/components/topology/EditorCanvas.tsx src/hmm_studio/frontend/src/components/topology/Toolbar.tsx
git commit -m "feat(topology): tri-state overlay toggle none/prior/learned (G, scaffold)"
```

### Task 8: `buildLearnedMap` — join learned transmat to editor edges by name

**Files:**
- Create: `src/hmm_studio/frontend/src/lib/learnedOverlay.ts` + `.test.ts`

- [ ] **Step 1: Write the failing test.** Create `src/hmm_studio/frontend/src/lib/learnedOverlay.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { buildLearnedMap } from "./learnedOverlay";

type S = { id: string; name: string };
type T = { id: string; source: string; target: string };

const states: S[] = [
  { id: "ida", name: "s0" },
  { id: "idb", name: "s1" },
];
const trans: T[] = [
  { id: "e_self", source: "ida", target: "ida" },
  { id: "e_fwd", source: "ida", target: "idb" },
];
const transmat = {
  state_names: ["s0", "s1"],
  transmat: [
    [0.8, 0.2],
    [0.3, 0.7],
  ],
  mask: [
    [true, true],
    [true, true],
  ],
  n_states: 2,
};

describe("buildLearnedMap", () => {
  it("maps each edge to transmat[i][j] via state name", () => {
    const m = buildLearnedMap(trans, states, transmat);
    expect(m.get("e_self")).toBeCloseTo(0.8); // s0→s0
    expect(m.get("e_fwd")).toBeCloseTo(0.2); // s0→s1
  });

  it("skips edges whose state name is not in the fitted matrix", () => {
    const extra: T[] = [...trans, { id: "e_x", source: "idGhost", target: "idb" }];
    const statesX: S[] = [...states, { id: "idGhost", name: "ghost" }];
    const m = buildLearnedMap(extra, statesX, transmat);
    expect(m.has("e_x")).toBe(false);
  });
});
```

- [ ] **Step 2: Run `npm test -- learnedOverlay`** → FAIL.

- [ ] **Step 3: Implement.** Create `src/hmm_studio/frontend/src/lib/learnedOverlay.ts`:

```ts
import type { TransmatResponse } from "../api/client";

interface OvState { id: string; name: string }
interface OvEdge { id: string; source: string; target: string }

/** Map each editor transition edge id → learned probability transmat[i][j],
 *  joining by STATE NAME (the only key that survives the fit YAML round-trip:
 *  matrix index i == position of a name in state_names). Edges whose endpoint
 *  names are not in the fitted matrix are omitted (caller styles them as
 *  absent). Self-loops (name==name) read transmat[i][i] naturally. */
export function buildLearnedMap(
  transitions: OvEdge[],
  states: OvState[],
  transmat: TransmatResponse,
): Map<string, number> {
  const idToName = new Map(states.map((s) => [s.id, s.name]));
  const nameToIdx = new Map(transmat.state_names.map((n, i) => [n, i]));
  const out = new Map<string, number>();
  for (const t of transitions) {
    const i = nameToIdx.get(idToName.get(t.source) ?? "");
    const j = nameToIdx.get(idToName.get(t.target) ?? "");
    if (i === undefined || j === undefined) continue;
    const row = transmat.transmat[i];
    if (!row || typeof row[j] !== "number") continue;
    out.set(t.id, row[j]);
  }
  return out;
}
```

- [ ] **Step 4: Run `npm test -- learnedOverlay`** → PASS (2).

- [ ] **Step 5: Lint** (0). **Commit.**

```bash
git add src/hmm_studio/frontend/src/lib/learnedOverlay.ts src/hmm_studio/frontend/src/lib/learnedOverlay.test.ts
git commit -m "feat(topology): name-keyed learned-overlay map builder (G core)"
```

### Task 9: Render learned probabilities + staleness guard

**Files:**
- Modify: `src/hmm_studio/frontend/src/components/topology/EditorCanvas.tsx`
- Modify: `src/hmm_studio/frontend/src/components/topology/Toolbar.tsx`

- [ ] **Step 1: EditorCanvas — fetch + paint learned, guarded by fingerprint.** In `EditorCanvas.tsx`, add imports:

```ts
import { getFitTransmat, type TransmatResponse } from "../../api/client";
import { useFitLink } from "../../store/fitLinkStore";
import { buildLearnedMap } from "../../lib/learnedOverlay";
import { topologyFingerprint } from "../../lib/topologyFingerprint";
```

Add reads + fetch state near the other hooks:

```ts
  const lastFitJobId = useFitLink((s) => s.lastFitJobId);
  const fitFingerprint = useFitLink((s) => s.fitFingerprint);
  const [learnedTransmat, setLearnedTransmat] = useState<TransmatResponse | null>(null);
  const [learnedError, setLearnedError] = useState<string | null>(null);

  useEffect(() => {
    if (overlayMode !== "learned" || !lastFitJobId) {
      setLearnedTransmat(null);
      setLearnedError(null);
      return;
    }
    let cancelled = false;
    getFitTransmat(lastFitJobId)
      .then((t) => { if (!cancelled) { setLearnedTransmat(t); setLearnedError(null); } })
      .catch((e) => { if (!cancelled) { setLearnedTransmat(null); setLearnedError(e instanceof Error ? e.message : "fetch failed"); } });
    return () => { cancelled = true; };
  }, [overlayMode, lastFitJobId]);

  const currentFingerprint = topologyFingerprint(states, transitions);
  const learnedStale =
    overlayMode === "learned" && fitFingerprint !== null && fitFingerprint !== currentFingerprint;
  const learnedMap =
    overlayMode === "learned" && learnedTransmat && !learnedStale
      ? buildLearnedMap(transitions, states, learnedTransmat)
      : null;
```

Add a `learned` branch FIRST in the `edges` map (before the `previews` branch):

```ts
  const edges: Edge[] = transitions.map((t) => {
    if (learnedMap) {
      const p = learnedMap.get(t.id) ?? 0;
      return { ...probEdgeStyle(p), id: t.id, source: t.source, target: t.target, type: "default" };
    }
    if (previews) {
      // …unchanged prior branch…
```

Add a stale/empty banner above the `<ReactFlow>` (inside the wrapper `<div>`):

```tsx
      {overlayMode === "learned" && (learnedStale || !lastFitJobId || learnedError) && (
        <div className="absolute z-10 m-2 px-2 py-1 text-xs rounded bg-amber-50 border border-amber-300 text-amber-800">
          {!lastFitJobId
            ? "No fit yet — click ▶ Fit this topology to compute learned probabilities."
            : learnedStale
              ? "Topology changed since the last fit — re-fit to refresh the learned probabilities."
              : `Could not load learned probabilities: ${learnedError}`}
        </div>
      )}
```

(Add `relative` to the wrapper `<div className="flex-1 border border-slate-200 rounded">` → `"flex-1 border border-slate-200 rounded relative"` so the absolute banner anchors.)

- [ ] **Step 2: Toolbar — disable `learned` unless a matching fit exists.** In `Toolbar.tsx`, add:

```ts
import { useFitLink } from "../../store/fitLinkStore";
import { topologyFingerprint } from "../../lib/topologyFingerprint";
```
```ts
  const lastFitJobId = useFitLink((s) => s.lastFitJobId);
  const fitFingerprint = useFitLink((s) => s.fitFingerprint);
  const allStates = useTopologyStore((s) => s.states);
  const allTransitions = useTopologyStore((s) => s.transitions);
  const learnedAvailable =
    !!lastFitJobId && fitFingerprint === topologyFingerprint(allStates, allTransitions);
```

In the tri-state control, make the `learned` button reflect availability (disable + dim when not available, but still clickable to surface the banner is acceptable — choose disable):

```tsx
          <button
            key={m}
            onClick={() => setOverlayMode(m)}
            disabled={m === "learned" && !learnedAvailable}
            className={
              "px-2 py-1 " +
              (overlayMode === m ? "bg-brand-600 text-white" : "bg-white text-slate-600 hover:bg-slate-50") +
              (m === "learned" && !learnedAvailable ? " opacity-40 cursor-not-allowed" : "")
            }
            title={
              m === "none" ? "No probabilities"
              : m === "prior" ? "Prior mean (expected P before fit)"
              : learnedAvailable ? "Learned probabilities (after a fit)"
              : "Run ▶ Fit this topology first (and don't change the topology after)"
            }
          >
            {m === "none" ? "—" : m}
          </button>
```

- [ ] **Step 3: Lint + build** (0), `npm test` green.

- [ ] **Step 4: (visual — substitute)** Reason through the full flow: pick dataset → Fit this topology (lot H sets fitLink) → return to editor → `learned` is enabled (fingerprint matches) → selecting it fetches `/api/fit/{jobId}/transmat` and paints each arrow with `probEdgeStyle(transmat[i][j])` joined by name. Rename a state → fingerprint mismatches → `learned` auto-disables + banner says "re-fit". Confirm the prior/none branches are unchanged. Note human QA on the happy path + the stale path.

- [ ] **Step 5: Commit.**

```bash
git add src/hmm_studio/frontend/src/components/topology/EditorCanvas.tsx src/hmm_studio/frontend/src/components/topology/Toolbar.tsx
git commit -m "feat(topology): learned-probability overlay on arrows + staleness guard (G)"
```

---

## Lot J — Self-loops + bidirectional edges + Tidy (auto arrow placement)

**Why:** Self-loops (the transmat diagonal — central to HMMs) render as a near-invisible degenerate stub today; reciprocal A→B / B→A edges overlap; and there is no one-click layout. Add an `edgeTypes` registry with custom `selfLoop` (arc) and `curved` (offset) edges, a `setPositions` atomic action, and a Tidy auto-layout button.

### Task 10: `setPositions` action (P-3) + `autoLayout` functions (F.4 core)

**Files:**
- Modify: `src/hmm_studio/frontend/src/store/topologyStore.ts`
- Create: `src/hmm_studio/frontend/src/lib/autoLayout.ts` + `.test.ts`

- [ ] **Step 1: Add `setPositions` to the store.** In `topologyStore.ts`:
  - In the `TopologyState` interface, after `moveState`, add: `setPositions: (positions: Record<string, { x: number; y: number }>) => void;`
  - In the store object, after `moveState`, add the action (ONE `set()` ⇒ one undo entry):
    ```ts
        setPositions: (positions) =>
          set((s) => ({
            states: s.states.map((n) =>
              positions[n.id] ? { ...n, position: positions[n.id] } : n,
            ),
          })),
    ```
  - **CRITICAL:** add `setPositions` to the **temporal `partialize` destructure** (the list of action names that are stripped before tracking — otherwise the function leaks into the undo-tracked `data`). Find the `partialize: (state) => { const { setName, addState, …, ...data } = state; return data; }` and add `setPositions,` to that destructured list. (The persist `partialize` is an explicit allowlist of data fields, so no change needed there.)

- [ ] **Step 2: Write the failing autoLayout test.** Create `src/hmm_studio/frontend/src/lib/autoLayout.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { autoLayout } from "./autoLayout";

type S = { id: string; name: string; position: { x: number; y: number } };

const states: S[] = [
  { id: "b", name: "s1", position: { x: 0, y: 0 } },
  { id: "a", name: "s0", position: { x: 0, y: 0 } },
  { id: "c", name: "s2", position: { x: 0, y: 0 } },
];

describe("autoLayout", () => {
  it("left-right: one row sorted by name, increasing x, constant y", () => {
    const pos = autoLayout(states, "left-right");
    expect(pos["a"].y).toBe(pos["b"].y); // same row
    expect(pos["a"].x).toBeLessThan(pos["b"].x); // s0 left of s1
    expect(pos["b"].x).toBeLessThan(pos["c"].x); // s1 left of s2
  });

  it("circular: all on a circle (equal radius from the center)", () => {
    const pos = autoLayout(states, "circular");
    const xs = Object.values(pos).map((p) => p.x);
    const ys = Object.values(pos).map((p) => p.y);
    const cx = xs.reduce((a, b) => a + b, 0) / xs.length;
    const cy = ys.reduce((a, b) => a + b, 0) / ys.length;
    const radii = Object.values(pos).map((p) => Math.hypot(p.x - cx, p.y - cy));
    for (const r of radii) expect(r).toBeCloseTo(radii[0], 1);
  });

  it("returns a position for every state id", () => {
    const pos = autoLayout(states, "left-right");
    expect(Object.keys(pos).sort()).toEqual(["a", "b", "c"]);
  });
});
```

- [ ] **Step 3: Run `npm test -- autoLayout`** → FAIL (module missing).

- [ ] **Step 4: Implement.** Create `src/hmm_studio/frontend/src/lib/autoLayout.ts`:

```ts
interface LayoutState { id: string; name: string }
export type LayoutMode = "left-right" | "circular";

/** Pure HMM-aware layouts. left-right = a single horizontal chain sorted by
 *  name (natural numeric order s0,s1,…); circular = evenly spaced on a circle
 *  (reuses the Results TransmatGraph radius formula). Returns id→position;
 *  the caller commits via setPositions (one undo entry). */
export function autoLayout(states: LayoutState[], mode: LayoutMode): Record<string, { x: number; y: number }> {
  const out: Record<string, { x: number; y: number }> = {};
  if (mode === "circular") {
    const K = states.length || 1;
    const R = Math.max(110, 26 * K);
    const cx = R + 70;
    const cy = R + 40;
    states.forEach((s, i) => {
      const a = (2 * Math.PI * i) / K - Math.PI / 2;
      out[s.id] = { x: cx + R * Math.cos(a), y: cy + R * Math.sin(a) };
    });
    return out;
  }
  // left-right
  const sorted = [...states].sort((a, b) =>
    a.name.localeCompare(b.name, undefined, { numeric: true }),
  );
  const STEP = 240;
  const X0 = 60;
  const Y = 120;
  sorted.forEach((s, i) => {
    out[s.id] = { x: X0 + i * STEP, y: Y };
  });
  return out;
}
```

- [ ] **Step 5: Run `npm test -- autoLayout`** → PASS (3). **Lint + build** (0).

- [ ] **Step 6: Commit.**

```bash
git add src/hmm_studio/frontend/src/store/topologyStore.ts src/hmm_studio/frontend/src/lib/autoLayout.ts src/hmm_studio/frontend/src/lib/autoLayout.test.ts
git commit -m "feat(topology): setPositions atomic action + autoLayout functions (P-3/F.4 core)"
```

### Task 11: Tidy button

**Files:**
- Modify: `src/hmm_studio/frontend/src/components/topology/Toolbar.tsx`

- [ ] **Step 1: Add a Tidy split-button.** In `Toolbar.tsx`, add:

```ts
import { autoLayout, type LayoutMode } from "../../lib/autoLayout";
```
```ts
  const setPositions = useTopologyStore((s) => s.setPositions);
  function tidy(mode: LayoutMode) {
    const st = useTopologyStore.getState();
    if (st.states.length === 0) return;
    setPositions(autoLayout(st.states, mode));
  }
```

Add the control (two buttons — chain + circle):

```tsx
      <div className="w-px h-6 bg-slate-300" />
      <button onClick={() => tidy("left-right")} className={btn} title="Arrange as a left-right chain">
        ⇥ Tidy (chain)
      </button>
      <button onClick={() => tidy("circular")} className={btn} title="Arrange on a circle (ergodic)">
        ◯ Tidy (circle)
      </button>
```

- [ ] **Step 2: Lint + build** (0). **Step 3: (visual — substitute)** Reason: each Tidy reads the current states and commits ALL new positions via the single `setPositions` action → one undo entry restores the prior layout. Note human QA: build a messy graph, click Tidy (chain) → one row; Ctrl-Z → restored in one step; Tidy (circle) → ring.

- [ ] **Step 4: Commit.**

```bash
git add src/hmm_studio/frontend/src/components/topology/Toolbar.tsx
git commit -m "feat(topology): Tidy auto-layout button (chain + circle) (F.4)"
```

### Task 12: Self-loop + curved bidirectional edges (P-1 registry, C1, B3)

**Files:**
- Create: `src/hmm_studio/frontend/src/components/topology/edges/SelfLoopEdge.tsx`
- Create: `src/hmm_studio/frontend/src/components/topology/edges/CurvedEdge.tsx`
- Create: `src/hmm_studio/frontend/src/components/topology/edgeTypes.ts`
- Modify: `src/hmm_studio/frontend/src/components/topology/EditorCanvas.tsx`
- Modify: `src/hmm_studio/frontend/src/components/topology/StateNode.tsx`

- [ ] **Step 1: SelfLoopEdge component.** Create `src/hmm_studio/frontend/src/components/topology/edges/SelfLoopEdge.tsx`:

```tsx
import { BaseEdge, type EdgeProps } from "reactflow";

/** A self-transition (source===target) drawn as an arc looping above the node,
 *  so the transmat diagonal is visible and editable. */
export function SelfLoopEdge(p: EdgeProps) {
  const { sourceX, sourceY, targetX, targetY, markerEnd, style, label, labelStyle, labelBgStyle, labelBgPadding, labelBgBorderRadius } = p;
  const topY = Math.min(sourceY, targetY) - 70;
  const path = `M ${sourceX} ${sourceY} C ${sourceX + 50} ${topY}, ${targetX - 50} ${topY}, ${targetX} ${targetY}`;
  const midX = (sourceX + targetX) / 2;
  return (
    <BaseEdge
      path={path}
      markerEnd={markerEnd}
      style={style}
      label={label}
      labelX={midX}
      labelY={topY + 12}
      labelStyle={labelStyle}
      labelShowBg
      labelBgStyle={labelBgStyle}
      labelBgPadding={labelBgPadding}
      labelBgBorderRadius={labelBgBorderRadius}
    />
  );
}
```

- [ ] **Step 2: CurvedEdge component.** Create `src/hmm_studio/frontend/src/components/topology/edges/CurvedEdge.tsx`:

```tsx
import { BaseEdge, type EdgeProps } from "reactflow";

/** A bidirectional transition: bow the edge perpendicular to the source→target
 *  line so A→B and B→A don't overlap. `data.dir` (+1/-1) picks the side. */
export function CurvedEdge(p: EdgeProps) {
  const { sourceX, sourceY, targetX, targetY, markerEnd, style, data, label, labelStyle, labelBgStyle, labelBgPadding, labelBgBorderRadius } = p;
  const dir = (data?.dir ?? 1) as number;
  const mx = (sourceX + targetX) / 2;
  const my = (sourceY + targetY) / 2;
  const dx = targetX - sourceX;
  const dy = targetY - sourceY;
  const len = Math.hypot(dx, dy) || 1;
  const off = 45 * dir;
  const cx = mx + (-dy / len) * off;
  const cy = my + (dx / len) * off;
  const path = `M ${sourceX} ${sourceY} Q ${cx} ${cy} ${targetX} ${targetY}`;
  return (
    <BaseEdge
      path={path}
      markerEnd={markerEnd}
      style={style}
      label={label}
      labelX={cx}
      labelY={cy}
      labelStyle={labelStyle}
      labelShowBg
      labelBgStyle={labelBgStyle}
      labelBgPadding={labelBgPadding}
      labelBgBorderRadius={labelBgBorderRadius}
    />
  );
}
```

- [ ] **Step 3: edgeTypes registry.** Create `src/hmm_studio/frontend/src/components/topology/edgeTypes.ts`:

```ts
import type { EdgeTypes } from "reactflow";
import { SelfLoopEdge } from "./edges/SelfLoopEdge";
import { CurvedEdge } from "./edges/CurvedEdge";

export const edgeTypes: EdgeTypes = {
  selfLoop: SelfLoopEdge,
  curved: CurvedEdge,
};
```

- [ ] **Step 4: EditorCanvas — choose edge type per edge.** In `EditorCanvas.tsx`:
  - Add `import { edgeTypes } from "./edgeTypes";`
  - Pass it to `<ReactFlow … edgeTypes={edgeTypes} …>` (next to `nodeTypes`).
  - Build a reciprocal-pair lookup before `edges`:
    ```ts
    const pairKey = (a: string, b: string) => `${a} ${b}`;
    const present = new Set(transitions.map((t) => pairKey(t.source, t.target)));
    ```
  - Refactor the `edges` map so the per-edge STYLE (learned/prior/default) is computed into `styleProps`, then a `type` + `data` are chosen, and both are returned. Replace the whole `const edges: Edge[] = transitions.map((t) => { … });` with:
    ```ts
    const edges: Edge[] = transitions.map((t) => {
      // 1) style props (probability overlay or default)
      let styleProps: Partial<Edge>;
      if (learnedMap) {
        styleProps = probEdgeStyle(learnedMap.get(t.id) ?? 0);
      } else if (previews) {
        styleProps = probEdgeStyle(previews.get(t.id) ?? 0);
      } else {
        styleProps = {
          markerEnd: { type: MarkerType.ArrowClosed, color: t.prior_weight !== undefined ? "#4f46e5" : "#94a3b8" },
          style: { strokeWidth: t.prior_weight !== undefined ? 3 : 2, stroke: t.prior_weight !== undefined ? "#4f46e5" : "#94a3b8" },
          label: t.prior_weight !== undefined ? `α=${t.prior_weight.toFixed(1)}` : undefined,
          labelStyle: { fontSize: 10, fontFamily: "monospace" },
          labelBgPadding: [2, 4] as [number, number],
          labelBgBorderRadius: 4,
          labelBgStyle: { fill: "#eef2ff", fillOpacity: 0.9 },
        };
      }
      // 2) edge type: self-loop, curved (reciprocal pair), or default
      let type = "default";
      let data: Record<string, unknown> | undefined;
      if (t.source === t.target) {
        type = "selfLoop";
      } else if (present.has(pairKey(t.target, t.source))) {
        type = "curved";
        data = { dir: t.source < t.target ? 1 : -1 };
      }
      return { ...styleProps, id: t.id, source: t.source, target: t.target, type, data };
    });
    ```

- [ ] **Step 5: StateNode — a "↺ self-loop" affordance when selected.** In `StateNode.tsx`:
  - Add `const addTransition = useTopologyStore((s) => s.addTransition);`
  - Render a small button inside the node, shown only when `selected`, that adds a self-loop:
    ```tsx
        {selected && (
          <button
            onMouseDown={(e) => e.stopPropagation()}
            onClick={(e) => { e.stopPropagation(); addTransition(id, id); }}
            title="Add a self-transition (loop)"
            className="absolute -top-2 -right-2 w-5 h-5 rounded-full bg-brand-600 text-white text-xs leading-5 text-center shadow"
          >↺</button>
        )}
    ```
    (Ensure the node wrapper `<div>` has `relative` so the absolute button anchors — add `relative` to its className.)

- [ ] **Step 6: Lint + build** (0), `npm test` green.

- [ ] **Step 7: (visual — substitute)** Reason: edges with `source===target` now render via `SelfLoopEdge` (an arc above the node, with the prob/α label); reciprocal pairs render as two `CurvedEdge`s bowed apart so both labels are legible; all others stay default. The `↺` button on a selected node calls `addTransition(id,id)` (already allows self-loops). The probability overlays (prior/learned) flow through because `styleProps` (incl. label) is spread into every edge regardless of type. Note human QA: ergodic 3-state model (from F.1) now shows visible self-loops + non-overlapping reciprocal arrows; add a self-loop via ↺.

- [ ] **Step 8: Commit.**

```bash
git add src/hmm_studio/frontend/src/components/topology/edges/ src/hmm_studio/frontend/src/components/topology/edgeTypes.ts src/hmm_studio/frontend/src/components/topology/EditorCanvas.tsx src/hmm_studio/frontend/src/components/topology/StateNode.tsx
git commit -m "feat(topology): self-loop + curved bidirectional edges + ↺ affordance (P-1/C1/B3)"
```

---

## Task 13: E2E coverage for Increment 2

**Files:**
- Modify: `e2e/tests/topology-editor.spec.ts`

- [ ] **Step 1: Add specs** (append a new `test.describe`). Cover: (a) a guided **ergodic** model shows arrows (≥ 1 `.react-flow__edge` after finishing the wizard with ergodic), (b) **Save model** then **Load saved…** round-trips (save, clear via a new model, load, states reappear), (c) **Fit this topology** button is **disabled without a dataset**, (d) the **tri-state** control toggles and `learned` is disabled with no fit, (e) a **self-loop** created via `↺` renders a `.react-flow__edge` of the self-loop type, (f) **Tidy (chain)** then a single **Undo** restores positions. Use the existing selectors (`+ state`, `.react-flow__node`, `.react-flow__edge`, button roles/text). Mark server-dependent assertions to skip gracefully if `:8000` is unreachable (the suite already targets the served app).

```ts
test.describe("Topology editor — Increment 2", () => {
  test("ergodic guided model renders arrows", async ({ page }) => {
    await page.goto("/topology/new");
    await page.waitForTimeout(400);
    // Step through to Review with default (ergodic) shape, then finish.
    for (let i = 0; i < 4; i++) {
      await page.getByRole("button", { name: /^Next$/ }).click();
      await page.waitForTimeout(120);
    }
    await page.getByRole("button", { name: /Finish → open in editor/i }).click();
    await page.waitForTimeout(500);
    expect(await page.locator(".react-flow__edge").count()).toBeGreaterThan(0);
  });

  test("Fit this topology is disabled without a dataset", async ({ page }) => {
    await page.goto("/topology");
    await page.waitForTimeout(400);
    await page.getByRole("button", { name: /\+ state/i }).click();
    await expect(page.getByRole("button", { name: /Fit this topology/i })).toBeDisabled();
  });
});
```

(Add the remaining cases — save/load, tri-state, self-loop, Tidy+undo — following the same pattern; keep them resilient to timing with short waits.)

- [ ] **Step 2: Validate** with `npx playwright test --list` from `e2e/` (specs discovered). Attempt a run against `:8000` if the app is up; a connection error is acceptable (CI doesn't run e2e). **Step 3: Commit.**

```bash
git add e2e/tests/topology-editor.spec.ts
git commit -m "test(e2e): Increment 2 — ergodic arrows, fit-gating, save/load, self-loop, tidy"
```

---

## Self-Review (run after writing all tasks — fix inline)

- **Spec coverage:** F.1 ergodic → Task 1. I stop-gap (A2) → Tasks 2-4. H Fit button → Tasks 5-6. G learned overlay + tri-state → Tasks 7-9. F.4 Tidy + P-3 → Tasks 10-11. P-1 + C1 + B3 → Task 12. E2E → Task 13. A1 true-tabs is intentionally roadmap-only (not in this plan).
- **Contracts consistency:** `topologyFingerprint` (T5→T9, T12-none), `fitLinkStore.{lastFitJobId,fitFingerprint,setFitLink}` (T5→T6→T9), `overlayMode` enum + `migrateEditorPrefs` (T7→T9), `buildLearnedMap` (T8→T9), `setPositions` (T10→T11), `edgeTypes`/`autoLayout` (T10→T11→T12). Names match across tasks.
- **Build-green per task:** Task 7 changes the editorPrefs API AND updates both consumers in the same task; `learned` is a no-op until Task 9 — no broken intermediate build.
- **Store purity:** `setPositions` MUST be added to the temporal partialize destructure (Task 10 Step 1) or zundo tracks a function — called out explicitly. `fitLinkStore` + `savedTopologiesStore` are separate stores, never in `topologyStore`/undo/serialised model.
- **No placeholders:** every code step shows complete code; run steps show command + expected outcome. The one soft spot is Task 13's "add the remaining cases" — acceptable for E2E (the patterns are shown), but the executor should write them out.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-03-topology-editor-increment-2.md`. Two execution options:

**1. Subagent-Driven (recommended)** — fresh subagent per task + two-stage review, in this session.
**2. Inline Execution** — execute tasks here with checkpoints.

Which approach?

