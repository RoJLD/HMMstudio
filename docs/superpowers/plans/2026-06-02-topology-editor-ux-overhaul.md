# Topology Editor UX Overhaul — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the topology editor so states aren't glued, bubbles follow the cursor when dragged, and arrows can show a (honest, pre-fit) transition-probability preview — then lay the test-infra foundation for the rest of the UX overhaul.

**Architecture:** The editor is a controlled React Flow v11 canvas backed by a zustand store (`topologyStore`, with `zundo` undo + localStorage persist). This plan introduces (1) a vitest unit tier for pure logic, (2) pure helper modules in `src/lib/` (edge styling, prior-mean preview, node reconciliation, node placement) tested in isolation, then (3) wires them into `EditorCanvas`/`Toolbar`/`StateNode` and (4) adds Playwright E2E. It deliberately ships only the three user-visible complaints first; structural items (self-loops, Tidy, etc.) follow in later increments.

**Tech Stack:** React 18 + TypeScript + Vite 5, React Flow 11.11, zustand 4 + zundo 2, Tailwind, vitest (new), Playwright (existing, `e2e/`).

**Scope of THIS plan:** Increment 1 only — see "Increment roadmap" at the bottom for Increments 2-4 (which will be detailed in follow-on `writing-plans` passes once Increment 1 lands). Spec: [`docs/superpowers/specs/2026-06-02-topology-editor-ux-overhaul-design.md`](../specs/2026-06-02-topology-editor-ux-overhaul-design.md).

**Preconditions (not tasks — set up before executing):**
- Be on a **dedicated branch off `main`** (e.g. `feat/topology-editor-ux`). The current `academy-emission-lessons` branch has unrelated uncommitted work (lesson 15) — do not mix. Commit/stash that first, then branch.
- Verify commit identity: `git config user.email` → `roblastar@live.fr` (mandatory, per repo `CLAUDE.md`). All commit messages get the standard `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` trailer.
- All frontend commands run from `src/hmm_studio/frontend/`.

---

## Task 1: Stand up a vitest unit tier (test infra)

**Why:** The frontend has **no** JS unit runner today (`package.json` scripts = dev/build/preview/lint only). The pure helpers in Tasks 2-5 need one. This resolves spec §5 Q6.

**Files:**
- Modify: `src/hmm_studio/frontend/package.json`
- Create: `src/hmm_studio/frontend/vitest.config.ts`
- Modify: `src/hmm_studio/frontend/tsconfig.json` (exclude test files from the app build)
- Create: `src/hmm_studio/frontend/src/lib/_smoke.test.ts` (temporary, deleted in step 6)
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Add vitest + jsdom and test scripts to package.json**

In `src/hmm_studio/frontend/package.json`, add to `devDependencies`:

```json
    "jsdom": "^25.0.1",
    "vitest": "^2.1.8",
```

And add to `scripts` (after `"lint"`):

```json
    "test": "vitest run",
    "test:watch": "vitest"
```

- [ ] **Step 2: Create the vitest config**

Create `src/hmm_studio/frontend/vitest.config.ts`:

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Separate from vite.config.ts on purpose: the app build config (manualChunks,
// proxy, version inject) is irrelevant to unit tests. jsdom is used so modules
// that import `reactflow` (e.g. MarkerType) resolve cleanly.
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
```

- [ ] **Step 3: Keep test files out of the production `tsc` build**

Read `src/hmm_studio/frontend/tsconfig.json`. Add `"src/**/*.test.ts"` and `"src/**/*.test.tsx"` to its `exclude` array (create the array if absent). This stops `npm run build` (`tsc && vite build`) from compiling test files into the bundle.

- [ ] **Step 4: Install**

Run (from `src/hmm_studio/frontend/`): `npm install`
Expected: `vitest` and `jsdom` added to `node_modules`, `package-lock.json` updated.

- [ ] **Step 5: Write a smoke test and run it**

Create `src/hmm_studio/frontend/src/lib/_smoke.test.ts`:

```ts
import { describe, it, expect } from "vitest";

describe("vitest smoke", () => {
  it("runs", () => {
    expect(1 + 1).toBe(2);
  });
});
```

Run: `npm test`
Expected: 1 passed.

- [ ] **Step 6: Delete the smoke test**

Delete `src/hmm_studio/frontend/src/lib/_smoke.test.ts` (it has served its purpose).

- [ ] **Step 7: Wire a frontend job into CI**

In `.github/workflows/ci.yml`, add a new job under `jobs:` (sibling of `test:`):

```yaml
  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: src/hmm_studio/frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
          cache-dependency-path: src/hmm_studio/frontend/package-lock.json
      - run: npm ci
      - run: npm run lint
      - run: npm test
```

Note: if `src/hmm_studio/frontend/package-lock.json` does not exist yet, step 4 created it — commit it too.

- [ ] **Step 8: Commit**

```bash
git add src/hmm_studio/frontend/package.json src/hmm_studio/frontend/package-lock.json src/hmm_studio/frontend/vitest.config.ts src/hmm_studio/frontend/tsconfig.json .github/workflows/ci.yml
git commit -m "test(frontend): add vitest unit tier + CI job"
```

---

## Task 2: Shared `probEdgeStyle(p)` helper + refactor TransmatGraph (spec B1)

**Why:** Both the Results graph and (soon) the editor style arrows by probability. Extract the recipe once to avoid divergence. The `isActive`/animated branch stays local to TransmatGraph.

**Files:**
- Create: `src/hmm_studio/frontend/src/lib/edgeStyle.ts`
- Create: `src/hmm_studio/frontend/src/lib/edgeStyle.test.ts`
- Modify: `src/hmm_studio/frontend/src/components/results/TransmatGraph.tsx:118-138`

- [ ] **Step 1: Write the failing test**

Create `src/hmm_studio/frontend/src/lib/edgeStyle.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { MarkerType } from "reactflow";
import { probEdgeStyle } from "./edgeStyle";

describe("probEdgeStyle", () => {
  it("scales strokeWidth as 1 + 5p", () => {
    expect(probEdgeStyle(0).style.strokeWidth).toBe(1);
    expect(probEdgeStyle(0.5).style.strokeWidth).toBe(3.5);
    expect(probEdgeStyle(1).style.strokeWidth).toBe(6);
  });

  it("labels with 2 decimals and uses a closed arrow", () => {
    const s = probEdgeStyle(0.42);
    expect(s.label).toBe("0.42");
    expect(s.markerEnd.type).toBe(MarkerType.ArrowClosed);
  });

  it("encodes p in the stroke opacity", () => {
    expect(probEdgeStyle(1).style.stroke).toBe("rgba(79,70,229,1.00)");
    expect(probEdgeStyle(0).style.stroke).toBe("rgba(79,70,229,0.30)");
  });
});
```

- [ ] **Step 2: Run the test, verify it FAILS**

Run: `npm test -- edgeStyle`
Expected: FAIL — cannot find module `./edgeStyle`.

- [ ] **Step 3: Implement the helper**

Create `src/hmm_studio/frontend/src/lib/edgeStyle.ts`:

```ts
import { MarkerType } from "reactflow";

/** Pure mapping `p in [0,1]` → React Flow edge style props: thickness ∝ p,
 *  opacity ∝ p, a 2-decimal label in a pill, and a closed arrowhead. Shared by
 *  the Results TransmatGraph (learned probabilities) and the editor's prior
 *  preview. The active/animated highlight is intentionally NOT here — it is a
 *  Results-only concern and stays local to TransmatGraph. */
export function probEdgeStyle(p: number) {
  return {
    label: p.toFixed(2),
    style: {
      strokeWidth: 1 + 5 * p,
      stroke: `rgba(79,70,229,${(0.3 + 0.7 * p).toFixed(2)})`,
    },
    labelStyle: { fontSize: 10, fontFamily: "monospace", fill: "#3730a3" },
    labelBgPadding: [2, 3] as [number, number],
    labelBgBorderRadius: 4,
    labelBgStyle: { fill: "#eef2ff", fillOpacity: 0.9 },
    markerEnd: {
      type: MarkerType.ArrowClosed,
      color: "#6366f1",
      width: 16,
      height: 16,
    },
  };
}
```

- [ ] **Step 4: Run the test, verify it PASSES**

Run: `npm test -- edgeStyle`
Expected: 3 passed.

- [ ] **Step 5: Refactor TransmatGraph to use the helper**

In `src/hmm_studio/frontend/src/components/results/TransmatGraph.tsx`, replace the edge push (lines 118-138) with a spread of `probEdgeStyle(p)` overridden by the active branch. Add the import at the top:

```ts
import { probEdgeStyle } from "../../lib/edgeStyle";
```

Replace the `edges.push({...})` block with:

```ts
      const base = probEdgeStyle(p);
      edges.push({
        ...base,
        id: `${i}-${j}`,
        source: `s${i}`,
        target: `s${j}`,
        animated: isActive,
        style: isActive
          ? { strokeWidth: 4, stroke: "#4f46e5" }
          : base.style,
        markerEnd: isActive
          ? { type: MarkerType.ArrowClosed, color: "#4f46e5", width: 16, height: 16 }
          : base.markerEnd,
      });
```

- [ ] **Step 6: Verify the build + lint pass**

Run: `npm run lint`
Expected: exit 0 (no type errors).

- [ ] **Step 7: Commit**

```bash
git add src/hmm_studio/frontend/src/lib/edgeStyle.ts src/hmm_studio/frontend/src/lib/edgeStyle.test.ts src/hmm_studio/frontend/src/components/results/TransmatGraph.tsx
git commit -m "refactor(viz): extract shared probEdgeStyle helper (B1)"
```

---

## Task 3: Pure `priorMeanPreview` calculation (spec B2)

**Why:** The honest pre-fit number to show on an editor arrow is the Dirichlet **prior mean** = `α_eff / Σα_eff` over the source's out-edges. With no overrides it degenerates to uniform `1/out-degree`. In MLE mode (`globalAlpha === null`) it is ALWAYS uniform `1/d` (stray overrides ignored — see spec B2). It is **scale-invariant in α** (the locked-in test).

**Files:**
- Create: `src/hmm_studio/frontend/src/lib/priorPreview.ts`
- Create: `src/hmm_studio/frontend/src/lib/priorPreview.test.ts`

- [ ] **Step 1: Write the failing test**

Create `src/hmm_studio/frontend/src/lib/priorPreview.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { priorMeanPreview } from "./priorPreview";

type E = { id: string; source: string; target: string; prior_weight?: number };

describe("priorMeanPreview", () => {
  const twoOut: E[] = [
    { id: "e1", source: "a", target: "b" },
    { id: "e2", source: "a", target: "c" },
  ];

  it("no overrides → uniform 1/out-degree", () => {
    const m = priorMeanPreview(twoOut, 1);
    expect(m.get("e1")).toBeCloseTo(0.5);
    expect(m.get("e2")).toBeCloseTo(0.5);
  });

  it("is scale-invariant in global alpha with no overrides", () => {
    const a1 = priorMeanPreview(twoOut, 1);
    const a2 = priorMeanPreview(twoOut, 2);
    const a100 = priorMeanPreview(twoOut, 100);
    for (const id of ["e1", "e2"]) {
      expect(a2.get(id)).toBeCloseTo(a1.get(id)!);
      expect(a100.get(id)).toBeCloseTo(a1.get(id)!);
    }
  });

  it("MLE mode (globalAlpha null) → always uniform, ignoring stray overrides", () => {
    const withOverride: E[] = [
      { id: "e1", source: "a", target: "b", prior_weight: 5 },
      { id: "e2", source: "a", target: "c" },
    ];
    const m = priorMeanPreview(withOverride, null);
    expect(m.get("e1")).toBeCloseTo(0.5);
    expect(m.get("e2")).toBeCloseTo(0.5);
  });

  it("numeric globalAlpha + one override → weighted mean", () => {
    const withOverride: E[] = [
      { id: "e1", source: "a", target: "b", prior_weight: 3 },
      { id: "e2", source: "a", target: "c" }, // falls back to globalAlpha=1
    ];
    const m = priorMeanPreview(withOverride, 1);
    expect(m.get("e1")).toBeCloseTo(0.75); // 3 / (3+1)
    expect(m.get("e2")).toBeCloseTo(0.25);
  });

  it("a self-loop counts as an out-edge of its source", () => {
    const withSelf: E[] = [
      { id: "e1", source: "a", target: "a" },
      { id: "e2", source: "a", target: "b" },
    ];
    const m = priorMeanPreview(withSelf, 1);
    expect(m.get("e1")).toBeCloseTo(0.5);
    expect(m.get("e2")).toBeCloseTo(0.5);
  });
});
```

- [ ] **Step 2: Run the test, verify it FAILS**

Run: `npm test -- priorPreview`
Expected: FAIL — cannot find module `./priorPreview`.

- [ ] **Step 3: Implement**

Create `src/hmm_studio/frontend/src/lib/priorPreview.ts`:

```ts
interface PreviewEdge {
  id: string;
  source: string;
  prior_weight?: number;
}

/** Per-edge Dirichlet prior MEAN = expected transition probability *before* any
 *  fit. Grouped by source node. Returns a Map edgeId → p.
 *
 *  - MLE mode (globalAlpha === null): ALWAYS uniform 1/out-degree per source —
 *    stray per-edge overrides are ignored (there is no global prior to weight
 *    against), so the display can honestly be labelled "uniform".
 *  - Otherwise: α_eff = prior_weight ?? globalAlpha; p = α_eff / Σ α_eff.
 *
 *  This is a MEAN, not a smoothing strength: it is invariant to the overall α
 *  magnitude. The UI labels it "prior mean (expected P before fit)" and must
 *  NOT present it as "what raising α does". */
export function priorMeanPreview(
  transitions: PreviewEdge[],
  globalAlpha: number | null,
): Map<string, number> {
  const bySource = new Map<string, PreviewEdge[]>();
  for (const t of transitions) {
    const arr = bySource.get(t.source) ?? [];
    arr.push(t);
    bySource.set(t.source, arr);
  }

  const result = new Map<string, number>();
  const mle = globalAlpha === null;
  for (const outs of bySource.values()) {
    const d = outs.length;
    if (d === 0) continue; // unreachable (an edge always has its source)
    if (mle) {
      for (const t of outs) result.set(t.id, 1 / d);
    } else {
      const alphaEff = (t: PreviewEdge) => t.prior_weight ?? globalAlpha;
      const sum = outs.reduce((acc, t) => acc + alphaEff(t)!, 0);
      for (const t of outs) result.set(t.id, alphaEff(t)! / sum);
    }
  }
  return result;
}
```

- [ ] **Step 4: Run the test, verify it PASSES**

Run: `npm test -- priorPreview`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/hmm_studio/frontend/src/lib/priorPreview.ts src/hmm_studio/frontend/src/lib/priorPreview.test.ts
git commit -m "feat(topology): pure prior-mean preview calc (B2 core)"
```

---

## Task 4: Pure `reconcileNodes` for the drag fix (spec A1)

**Why:** A1 moves React Flow into a local node array. The reconciliation effect must MERGE store state into the existing nodes **by id**, preserving the transient fields React Flow maintains in place (`selected`, `dragging`, measured `width`/`height`) — otherwise every store commit wipes the selection ring and side panel (the blocker the review caught).

**Files:**
- Create: `src/hmm_studio/frontend/src/lib/reconcileNodes.ts`
- Create: `src/hmm_studio/frontend/src/lib/reconcileNodes.test.ts`

- [ ] **Step 1: Write the failing test**

Create `src/hmm_studio/frontend/src/lib/reconcileNodes.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import type { Node } from "reactflow";
import { reconcileNodes } from "./reconcileNodes";

type S = { id: string; name: string; position: { x: number; y: number } };

describe("reconcileNodes", () => {
  it("creates nodes for new states", () => {
    const states: S[] = [{ id: "s1", name: "s0", position: { x: 0, y: 0 } }];
    const out = reconcileNodes([], states);
    expect(out).toHaveLength(1);
    expect(out[0]).toMatchObject({ id: "s1", type: "state", data: { label: "s0" } });
  });

  it("preserves selected/dragging/measured fields of existing nodes", () => {
    const prev: Node[] = [
      {
        id: "s1",
        type: "state",
        position: { x: 0, y: 0 },
        data: { label: "s0" },
        selected: true,
        dragging: true,
        width: 120,
        height: 40,
      } as Node,
    ];
    const states: S[] = [{ id: "s1", name: "renamed", position: { x: 10, y: 20 } }];
    const out = reconcileNodes(prev, states);
    expect(out[0].selected).toBe(true);
    expect(out[0].dragging).toBe(true);
    expect(out[0].width).toBe(120);
    expect(out[0].height).toBe(40);
    // position + label come from the store
    expect(out[0].position).toEqual({ x: 10, y: 20 });
    expect(out[0].data).toEqual({ label: "renamed" });
  });

  it("drops nodes whose state was removed", () => {
    const prev: Node[] = [
      { id: "s1", type: "state", position: { x: 0, y: 0 }, data: { label: "s0" } } as Node,
      { id: "s2", type: "state", position: { x: 0, y: 0 }, data: { label: "s1" } } as Node,
    ];
    const states: S[] = [{ id: "s2", name: "s1", position: { x: 0, y: 0 } }];
    const out = reconcileNodes(prev, states);
    expect(out.map((n) => n.id)).toEqual(["s2"]);
  });
});
```

- [ ] **Step 2: Run the test, verify it FAILS**

Run: `npm test -- reconcileNodes`
Expected: FAIL — cannot find module `./reconcileNodes`.

- [ ] **Step 3: Implement**

Create `src/hmm_studio/frontend/src/lib/reconcileNodes.ts`:

```ts
import type { Node } from "reactflow";

interface StoreState {
  id: string;
  name: string;
  position: { x: number; y: number };
}

/** Merge the store's states into the existing React Flow node array BY ID.
 *  New states → fresh nodes; removed states → dropped; surviving states keep
 *  React Flow's transient fields (selected, dragging, positionAbsolute, measured
 *  width/height) while taking position + label from the store. This is what
 *  keeps the selection ring and measured layout alive across store commits. */
export function reconcileNodes(prev: Node[], states: StoreState[]): Node[] {
  const prevById = new Map(prev.map((n) => [n.id, n]));
  return states.map((s) => {
    const existing = prevById.get(s.id);
    if (existing) {
      return { ...existing, position: s.position, data: { label: s.name } };
    }
    return {
      id: s.id,
      type: "state",
      position: s.position,
      data: { label: s.name },
    } as Node;
  });
}
```

- [ ] **Step 4: Run the test, verify it PASSES**

Run: `npm test -- reconcileNodes`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/hmm_studio/frontend/src/lib/reconcileNodes.ts src/hmm_studio/frontend/src/lib/reconcileNodes.test.ts
git commit -m "feat(topology): pure node reconciliation for drag/selection (A1 core)"
```

---

## Task 5: Node placement helpers — anti-collision + lowest-free name (spec A4)

**Why:** `+ state` currently drops nodes at `Math.random()` (overlap-prone) and names them `s${states.length}` (duplicates after a deletion). Replace both with deterministic, collision-free logic.

**Files:**
- Create: `src/hmm_studio/frontend/src/lib/nodePlacement.ts`
- Create: `src/hmm_studio/frontend/src/lib/nodePlacement.test.ts`

- [ ] **Step 1: Write the failing test**

Create `src/hmm_studio/frontend/src/lib/nodePlacement.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { nextFreePosition, lowestFreeStateName } from "./nodePlacement";

describe("lowestFreeStateName", () => {
  it("empty → s0", () => {
    expect(lowestFreeStateName([])).toBe("s0");
  });
  it("contiguous → next index", () => {
    expect(lowestFreeStateName([{ name: "s0" }, { name: "s1" }])).toBe("s2");
  });
  it("fills the gap left by a deletion", () => {
    expect(lowestFreeStateName([{ name: "s0" }, { name: "s2" }])).toBe("s1");
  });
});

describe("nextFreePosition", () => {
  it("empty canvas → the base anchor", () => {
    expect(nextFreePosition([])).toEqual({ x: 120, y: 120 });
  });
  it("nudges away from an occupied anchor", () => {
    const pos = nextFreePosition([{ position: { x: 120, y: 120 } }]);
    expect(pos.x).toBeGreaterThan(120);
    expect(pos.y).toBeGreaterThan(120);
  });
});
```

- [ ] **Step 2: Run the test, verify it FAILS**

Run: `npm test -- nodePlacement`
Expected: FAIL — cannot find module `./nodePlacement`.

- [ ] **Step 3: Implement**

Create `src/hmm_studio/frontend/src/lib/nodePlacement.ts`:

```ts
interface Positioned {
  position: { x: number; y: number };
}

/** Lowest unused `s<N>` name, so deleting a middle state then adding one reuses
 *  the freed index instead of duplicating a name. */
export function lowestFreeStateName(states: { name: string }[]): string {
  const used = new Set(states.map((s) => s.name));
  let i = 0;
  while (used.has(`s${i}`)) i++;
  return `s${i}`;
}

/** A canvas position that does not overlap an existing node: start at a fixed
 *  anchor and nudge diagonally until clear. Deterministic (no Math.random). */
export function nextFreePosition(states: Positioned[]): { x: number; y: number } {
  const STEP = 40;
  const THRESHOLD = 60;
  let pos = { x: 120, y: 120 };
  const collides = (p: { x: number; y: number }) =>
    states.some(
      (s) =>
        Math.abs(s.position.x - p.x) < THRESHOLD &&
        Math.abs(s.position.y - p.y) < THRESHOLD,
    );
  let guard = 0;
  while (collides(pos) && guard++ < 200) {
    pos = { x: pos.x + STEP, y: pos.y + STEP };
  }
  return pos;
}
```

- [ ] **Step 4: Run the test, verify it PASSES**

Run: `npm test -- nodePlacement`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/hmm_studio/frontend/src/lib/nodePlacement.ts src/hmm_studio/frontend/src/lib/nodePlacement.test.ts
git commit -m "feat(topology): deterministic node placement + naming helpers (A4 core)"
```

---

## Task 6: Wire A4 into the store + Toolbar (anti-collision add)

**Files:**
- Modify: `src/hmm_studio/frontend/src/store/topologyStore.ts:124-133` (addState name)
- Modify: `src/hmm_studio/frontend/src/components/topology/Toolbar.tsx:11,22-29`

- [ ] **Step 1: Use the lowest-free name in the store**

In `topologyStore.ts`, add the import at the top:

```ts
import { lowestFreeStateName } from "../lib/nodePlacement";
```

Replace `addState` (lines 124-133) so the name comes from `lowestFreeStateName`:

```ts
        addState: (position) =>
          set((s) => {
            const id = _uid("s");
            const newState: StateNode = {
              id,
              name: lowestFreeStateName(s.states),
              position,
            };
            return { states: [...s.states, newState] };
          }),
```

- [ ] **Step 2: Use the non-overlapping position in the Toolbar**

In `Toolbar.tsx`, add imports and read `states`:

```ts
import { useTopologyStore, useTopologyTemporal } from "../../store/topologyStore";
import { nextFreePosition } from "../../lib/nodePlacement";
```

Add inside the component (next to the other store reads):

```ts
  const states = useTopologyStore((s) => s.states);
```

Replace the `+ state` button `onClick` (lines 22-29):

```tsx
      <button
        onClick={() => addState(nextFreePosition(states))}
        className={btn}
      >
        + state
      </button>
```

- [ ] **Step 3: Verify lint + existing e2e add-state still works**

Run: `npm run lint`
Expected: exit 0.

- [ ] **Step 4: Commit**

```bash
git add src/hmm_studio/frontend/src/store/topologyStore.ts src/hmm_studio/frontend/src/components/topology/Toolbar.tsx
git commit -m "feat(topology): anti-collision add + gap-filling state names (A4)"
```

---

## Task 7: Visual quick wins — spacing, fitView bound, bounded pill width (spec A2/A3/A5)

**Files:**
- Modify: `src/hmm_studio/frontend/src/lib/yaml.ts:124` (grid step, A2 transitional)
- Modify: `src/hmm_studio/frontend/src/components/topology/EditorCanvas.tsx:111` (A3)
- Modify: `src/hmm_studio/frontend/src/components/topology/StateNode.tsx:15,30` (A5)

> Note: A2 here is the **transitional** grid widening (per spec §3.1). The durable fix (auto-layout on load + `_layout` round-trip) lands in Increment 2 with Tidy/D1.

- [ ] **Step 1: Widen the load grid step (A2)**

In `yaml.ts`, change the position formula on line 124 from:

```ts
    position: { x: 80 + (i % 4) * 180, y: 80 + Math.floor(i / 4) * 140 },
```

to:

```ts
    position: { x: 60 + (i % 4) * 240, y: 60 + Math.floor(i / 4) * 160 },
```

- [ ] **Step 2: Bound fitView so small graphs aren't blown up (A3)**

In `EditorCanvas.tsx`, change the `fitView` prop (line 111) to:

```tsx
        fitView
        fitViewOptions={{ padding: 0.3, maxZoom: 1 }}
```

- [ ] **Step 3: Bound the pill width so a long label can't exceed the step (A5)**

In `StateNode.tsx`, line 15, add `max-w-[160px]` to the wrapper className:

```ts
        "px-4 py-2 rounded-full border-2 bg-white shadow-sm min-w-[80px] max-w-[160px] text-center " +
```

And on the `<input>` (line 30), add `truncate`:

```tsx
        className="w-full bg-transparent text-center text-sm font-medium text-slate-900 outline-none truncate"
```

- [ ] **Step 4: Visual check**

Run (from `src/hmm_studio/frontend/`): `npm run dev`, open `http://localhost:5173/topology`, click `✨ New guided model` (or `+ state` ×3). Confirm states render visibly separated at k=2/3/5 and a >4-state model wraps without crowding. Stop the dev server.

- [ ] **Step 5: Commit**

```bash
git add src/hmm_studio/frontend/src/lib/yaml.ts src/hmm_studio/frontend/src/components/topology/EditorCanvas.tsx src/hmm_studio/frontend/src/components/topology/StateNode.tsx
git commit -m "fix(topology): visibly space states, bound fitView zoom + pill width (A2/A3/A5)"
```

---

## Task 8: Drag follows the cursor + selection survives commits (spec A1 wiring)

**Why:** This is the headline bug. Move React Flow to a local node array seeded/merged from the store via `reconcileNodes`; feed ALL change types through `applyNodeChanges`; keep the single `moveState` commit on drag-end and `removeState` on remove.

**Files:**
- Modify: `src/hmm_studio/frontend/src/components/topology/EditorCanvas.tsx` (imports, node state, `onNodesChange`, `<ReactFlow nodes>`)

- [ ] **Step 1: Update imports + node state**

In `EditorCanvas.tsx`, change the React import (line 1) and add the helper import:

```ts
import { useCallback, useEffect, useState } from "react";
```

Add after the existing `nodeTypes`/store import (line 16 area):

```ts
import { reconcileNodes } from "../../lib/reconcileNodes";
```

Replace the derived `nodes` const (lines 28-33) with local state + a reconciliation effect:

```ts
  const [rfNodes, setRfNodes] = useState<Node[]>(() => reconcileNodes([], states));

  // Re-seed local nodes whenever the store's states identity changes (commit,
  // add, remove, YAML load). Merge-by-id preserves React Flow's transient
  // fields (selected, dragging, measured size) — see reconcileNodes.
  useEffect(() => {
    setRfNodes((prev) => reconcileNodes(prev, states));
  }, [states]);
```

- [ ] **Step 2: Rewrite `onNodesChange` to apply ALL changes locally**

Replace `onNodesChange` (lines 56-74) with:

```ts
  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      // Apply every change type to the local array so in-flight drags AND
      // selection render. setRfNodes uses the functional updater to avoid a
      // stale closure.
      setRfNodes((nds) => applyNodeChanges(changes, nds));
      // Commit side effects to the store: final drag position (once, on
      // drop) and removals.
      changes.forEach((change) => {
        if (
          change.type === "position" &&
          change.position &&
          change.dragging === false
        ) {
          moveState(change.id, change.position);
        }
        if (change.type === "remove") {
          removeState(change.id);
        }
      });
    },
    [moveState, removeState],
  );
```

- [ ] **Step 3: Feed local nodes to ReactFlow**

Change the `<ReactFlow nodes={nodes}` prop (line 104) to:

```tsx
        nodes={rfNodes}
```

- [ ] **Step 4: Lint**

Run: `npm run lint`
Expected: exit 0. (If TS flags `nodes` unused elsewhere, ensure the old `const nodes` is fully removed.)

- [ ] **Step 5: Manual verification**

Run `npm run dev`, open `/topology`, add 2 states. Drag a bubble — it must **follow the cursor**. Drop it, reload the page — it stays where dropped. Select a node, then type a new label / add a transition — the **selection ring and side panel persist** (no snap to GlobalPanel). Stop the dev server.

- [ ] **Step 6: Commit**

```bash
git add src/hmm_studio/frontend/src/components/topology/EditorCanvas.tsx
git commit -m "fix(topology): bubbles follow cursor on drag; selection survives commits (A1)"
```

---

## Task 9: Prior-mean preview toggle on editor arrows (spec B2)

**Why:** Let users overlay the honest pre-fit prior mean on arrows, OFF by default, as a UI-only preference outside the topology store (never undoable).

**Files:**
- Create: `src/hmm_studio/frontend/src/store/editorPrefsStore.ts`
- Modify: `src/hmm_studio/frontend/src/components/topology/Toolbar.tsx` (toggle control)
- Modify: `src/hmm_studio/frontend/src/components/topology/EditorCanvas.tsx` (apply preview to edges)

- [ ] **Step 1: Create the UI-prefs store (separate from topologyStore)**

Create `src/hmm_studio/frontend/src/store/editorPrefsStore.ts`:

```ts
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

// UI-only editor preferences. Deliberately SEPARATE from topologyStore so that
// toggling them is NOT undoable (zundo) and does NOT enter the topology's
// persisted/serialised model. Persisted under its own localStorage key.
interface EditorPrefs {
  showPriorPreview: boolean;
  setShowPriorPreview: (v: boolean) => void;
}

export const useEditorPrefs = create<EditorPrefs>()(
  persist(
    (set) => ({
      showPriorPreview: false,
      setShowPriorPreview: (v) => set({ showPriorPreview: v }),
    }),
    {
      name: "hmm-studio-editor-prefs",
      storage: createJSONStorage(() => localStorage),
    },
  ),
);
```

- [ ] **Step 2: Add the toggle to the Toolbar**

In `Toolbar.tsx`, add the import:

```ts
import { useEditorPrefs } from "../../store/editorPrefsStore";
```

Read the pref inside the component:

```ts
  const showPriorPreview = useEditorPrefs((s) => s.showPriorPreview);
  const setShowPriorPreview = useEditorPrefs((s) => s.setShowPriorPreview);
```

Add this control just before the closing `</div>` of the toolbar (after the Re-validate button):

```tsx
      <div className="w-px h-6 bg-slate-300" />
      <label className="flex items-center gap-1.5 text-sm text-slate-600 select-none">
        <input
          type="checkbox"
          checked={showPriorPreview}
          onChange={(e) => setShowPriorPreview(e.target.checked)}
        />
        prior preview
        <span className="text-xs text-slate-400">(expected P before fit)</span>
      </label>
```

- [ ] **Step 3: Apply the preview to the editor edges**

In `EditorCanvas.tsx`, add imports:

```ts
import { probEdgeStyle } from "../../lib/edgeStyle";
import { priorMeanPreview } from "../../lib/priorPreview";
import { useEditorPrefs } from "../../store/editorPrefsStore";
```

Read the pref + the global alpha near the other store reads:

```ts
  const transmatPriorAlpha = useTopologyStore((s) => s.transmat_prior_alpha);
  const showPriorPreview = useEditorPrefs((s) => s.showPriorPreview);
```

Replace the `edges` derivation (lines 35-54) so that, when the preview is on, each edge gets `probEdgeStyle(p)`; otherwise the current α-only styling is kept:

```ts
  const previews = showPriorPreview
    ? priorMeanPreview(transitions, transmatPriorAlpha)
    : null;

  const edges: Edge[] = transitions.map((t) => {
    if (previews) {
      const p = previews.get(t.id) ?? 0;
      return {
        ...probEdgeStyle(p),
        id: t.id,
        source: t.source,
        target: t.target,
        type: "default",
      };
    }
    return {
      id: t.id,
      source: t.source,
      target: t.target,
      type: "default",
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: t.prior_weight !== undefined ? "#4f46e5" : "#94a3b8",
      },
      style: {
        strokeWidth: t.prior_weight !== undefined ? 3 : 2,
        stroke: t.prior_weight !== undefined ? "#4f46e5" : "#94a3b8",
      },
      label:
        t.prior_weight !== undefined ? `α=${t.prior_weight.toFixed(1)}` : undefined,
      labelStyle: { fontSize: 10, fontFamily: "monospace" },
      labelBgPadding: [2, 4] as [number, number],
      labelBgBorderRadius: 4,
      labelBgStyle: { fill: "#eef2ff", fillOpacity: 0.9 },
    };
  });
```

- [ ] **Step 4: Lint**

Run: `npm run lint`
Expected: exit 0.

- [ ] **Step 5: Manual verification**

Run `npm run dev`, open `/topology`, build a 3-state left-right model (wizard or `+ state` + draw edges). Toggle **prior preview** on — arrows show probability bubbles (e.g. `0.50`) and thickness scales. Confirm the model YAML (Export YAML) is **unchanged** by toggling. Stop the dev server.

- [ ] **Step 6: Commit**

```bash
git add src/hmm_studio/frontend/src/store/editorPrefsStore.ts src/hmm_studio/frontend/src/components/topology/Toolbar.tsx src/hmm_studio/frontend/src/components/topology/EditorCanvas.tsx
git commit -m "feat(topology): honest prior-mean preview toggle on arrows (B2)"
```

---

## Task 10: E2E coverage for the new behavior

**Why:** The existing `e2e/tests/topology-editor.spec.ts` only covers undo/redo + export. Add NEW specs for drag-persist, selection survival, and the preview toggle. (Per spec §6, these are additions, not an "extend".)

**Files:**
- Modify: `e2e/tests/topology-editor.spec.ts`

- [ ] **Step 1: Add the drag-persist + preview tests**

Append to `e2e/tests/topology-editor.spec.ts` (inside the existing `test.describe`, or a new describe block):

```ts
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

    // Turn on the preview and assert a probability label appears.
    await page.getByText("prior preview").click();
    await page.waitForTimeout(200);
    await expect(page.locator(".react-flow__edge-textbg")).toHaveCount(1);
  });
});
```

- [ ] **Step 2: Run the editor E2E**

Run (from `e2e/`): `npm test -- topology-editor`
Expected: all topology-editor specs pass (the new ones + the existing undo/redo + export). Note: the E2E suite needs the app served — follow the `e2e/README` (or `playwright.config.ts` webServer) the same way the existing specs run.

- [ ] **Step 3: Commit**

```bash
git add e2e/tests/topology-editor.spec.ts
git commit -m "test(e2e): drag-persist + prior-preview toggle for the topology editor"
```

---

## Self-Review (Increment 1)

- **Spec coverage (Increment 1 slice):** A1 drag/selection → Tasks 4, 8. A2/A3/A5 spacing → Task 7. A4 anti-collision/naming → Tasks 5, 6. B1 shared helper → Task 2. B2 prior-mean preview + toggle ownership → Tasks 3, 9. Test infra (spec Q6) → Task 1. E2E + unit per spec §6 → Tasks 1-10.
- **Deferred (by design, see roadmap below):** P-1 edgeTypes, P-2 `_layout` durability, P-3 `setPositions`, B3 bidirectional, C1 self-loops, D1 Tidy, D2/D3/C2, E/E4. The transitional A2 grid widening (Task 7) holds until D1's auto-layout replaces it.
- **Type consistency:** helper names used across tasks — `probEdgeStyle` (T2→T9), `priorMeanPreview` (T3→T9), `reconcileNodes` (T4→T8), `nextFreePosition`/`lowestFreeStateName` (T5→T6), `useEditorPrefs.showPriorPreview` (T9). All match.
- **No placeholders:** every code step shows complete code; every run step shows the command + expected outcome.

---

## Increment roadmap (to be detailed in follow-on `writing-plans` passes)

Each increment is independently shippable/testable. Detail them **after** Increment 1 lands (the files will have changed; planning later code now would drift).

- **Increment 2 — P0 structure & layout (spec §3.0 P-1/P-2/P-3, §3.2 B3, §3.3 C1, §3.4 D1).**
  Add the `edgeTypes` registry (`selfLoop` + `curved`), the `setPositions` atomic store action (one-undo Tidy), the `_layout` round-trip on the share/persist path + auto-layout-on-load (replacing the transitional grid), then self-loops (custom arc edge + `↺` button) and the Tidy split-button (left-right + circular, zero-dep; layered deferred), plus B3 bidirectional curved edges. New pure modules: `src/lib/autoLayout.ts` (+ tests), custom edge components under `components/topology/edges/`.
- **Increment 3 — P1 navigation & validation (spec §3.4 D2/D3, §3.3 C2).**
  Minimap + snap-to-grid; empty-canvas onboarding presets (reusing `allowedTransitionsForShape`); the structural linter (`src/lib/topologyLint.ts` + tests, start-set per `startprob` mode) with per-node badges.
- **Increment 4 — P2 comfort & accessibility (spec §3.5 E1/E2, E4).**
  Keyboard shortcuts (focus-guarded), emission-type color coding + legend + minimap sync, then accessibility as its own slice measured against `e2e/tests/accessibility.spec.ts` (axe-core). **E3 mask grid is out of scope** (parked, spec §3.5/§4).

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-02-topology-editor-ux-overhaul.md`. Two execution options:

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — execute tasks in this session with checkpoints for review.

Which approach?
