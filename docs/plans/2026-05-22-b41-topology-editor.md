# B.4.1 Topology editor (React Flow MVP) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development.

**Goal:** Build a visual topology editor in the React frontend using React Flow, with live validation, undo/redo, and YAML import/export. Consumes the existing `hmm_core` API (single global EmissionSpec, `allowed_transitions` as a list of pairs).

**Scope (this plan):** B.4.1 = the visual editor on top of the CURRENT hmm_core API.

**Out of scope** (future plans):
- **A.8** : `hmm_core` extension for per-state `EmissionSpec`.
- **A.9** : `hmm_core` extension for Dirichlet priors on transitions.
- **B.4.2** : Per-state emission UI (depends on A.8).
- **B.4.3** : Edge weight overrides UI (depends on A.9).

**Architecture:** React Flow for the canvas, Zustand + zundo for state + undo, js-yaml for YAML serialization, debounced fetch to `/api/topology/validate`. Lives in `src/hmm_studio/frontend/src/components/topology/`.

**Tech Stack additions:** `reactflow`, `zustand`, `zundo`, `js-yaml`, `@types/js-yaml`. All pinned to recent stable.

**Working directory:** `C:\Users\rdenis\VScode\Tools\hmm_studio\src\hmm_studio\frontend\`.

---

## Task B.4.1.1: Dependencies + topology store

**Files:**
- Modify: `src/hmm_studio/frontend/package.json` (add deps)
- Create: `src/hmm_studio/frontend/src/store/topologyStore.ts`

- [ ] **Step 1: Add deps**

In `package.json`, add to `dependencies`:

```json
"reactflow": "^11.11.4",
"zustand": "^4.5.5",
"zundo": "^2.2.0",
"js-yaml": "^4.1.0"
```

And to `devDependencies`:

```json
"@types/js-yaml": "^4.0.9"
```

Run `npm install` in `src/hmm_studio/frontend/`.

- [ ] **Step 2: Create `src/store/topologyStore.ts`**

This is the single source of truth for the editor. It holds the current topology graph (nodes + edges), plus the global emission/init/fit settings. Wrapped in `temporal` middleware from zundo for undo/redo.

Content:

```ts
import { create } from "zustand";
import { temporal } from "zundo";
import type { TemporalState } from "zundo";

export type EmissionType = "gaussian" | "gmm" | "multinomial" | "poisson";
export type CovarianceType = "full" | "diag" | "tied" | "spherical";

export interface EmissionSpec {
  type: EmissionType;
  n_features: number | null;
  covariance_type: CovarianceType | null;
  n_mix: number | null;
  n_symbols: number | null;
}

export interface InitSpec {
  strategy: "uniform" | "random" | "kmeans" | "data_frequencies";
  seed: number;
}

export interface FitSpec {
  algorithm: "baum_welch";
  n_iter: number;
  tol: number;
}

export interface StateNode {
  id: string;
  name: string;
  position: { x: number; y: number };
}

export interface TransitionEdge {
  id: string;
  source: string;
  target: string;
}

export interface TopologyState {
  // Metadata
  name: string;
  // Graph
  states: StateNode[];
  transitions: TransitionEdge[];
  // Global params
  emission: EmissionSpec;
  startprob: "uniform" | "first_state" | number[];
  init: InitSpec;
  fit: FitSpec;

  // Actions (mutate the state via Zustand setters; zundo will track history)
  setName: (name: string) => void;
  addState: (position: { x: number; y: number }) => void;
  renameState: (id: string, name: string) => void;
  removeState: (id: string) => void;
  moveState: (id: string, position: { x: number; y: number }) => void;
  addTransition: (source: string, target: string) => void;
  removeTransition: (id: string) => void;
  setEmission: (emission: EmissionSpec) => void;
  setStartprob: (sp: "uniform" | "first_state" | number[]) => void;
  setInit: (init: InitSpec) => void;
  setFit: (fit: FitSpec) => void;
  loadTopology: (raw: Partial<Omit<TopologyState, "loadTopology">>) => void;
  reset: () => void;
}

const DEFAULT_STATE: Omit<
  TopologyState,
  | "setName"
  | "addState"
  | "renameState"
  | "removeState"
  | "moveState"
  | "addTransition"
  | "removeTransition"
  | "setEmission"
  | "setStartprob"
  | "setInit"
  | "setFit"
  | "loadTopology"
  | "reset"
> = {
  name: "untitled",
  states: [],
  transitions: [],
  emission: {
    type: "gaussian",
    n_features: 1,
    covariance_type: "full",
    n_mix: null,
    n_symbols: null,
  },
  startprob: "uniform",
  init: { strategy: "kmeans", seed: 42 },
  fit: { algorithm: "baum_welch", n_iter: 200, tol: 1e-4 },
};

function _uid(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 9)}`;
}

export const useTopologyStore = create<TopologyState>()(
  temporal(
    (set) => ({
      ...DEFAULT_STATE,
      setName: (name) => set({ name }),
      addState: (position) =>
        set((s) => {
          const id = _uid("s");
          const newState: StateNode = {
            id,
            name: `s${s.states.length}`,
            position,
          };
          return { states: [...s.states, newState] };
        }),
      renameState: (id, name) =>
        set((s) => ({
          states: s.states.map((n) => (n.id === id ? { ...n, name } : n)),
        })),
      removeState: (id) =>
        set((s) => ({
          states: s.states.filter((n) => n.id !== id),
          transitions: s.transitions.filter(
            (e) => e.source !== id && e.target !== id,
          ),
        })),
      moveState: (id, position) =>
        set((s) => ({
          states: s.states.map((n) =>
            n.id === id ? { ...n, position } : n,
          ),
        })),
      addTransition: (source, target) =>
        set((s) => {
          // Prevent duplicate edges
          if (s.transitions.some((e) => e.source === source && e.target === target)) {
            return {};
          }
          return {
            transitions: [
              ...s.transitions,
              { id: _uid("e"), source, target },
            ],
          };
        }),
      removeTransition: (id) =>
        set((s) => ({ transitions: s.transitions.filter((e) => e.id !== id) })),
      setEmission: (emission) => set({ emission }),
      setStartprob: (startprob) => set({ startprob }),
      setInit: (init) => set({ init }),
      setFit: (fit) => set({ fit }),
      loadTopology: (raw) => set({ ...DEFAULT_STATE, ...raw }),
      reset: () => set(DEFAULT_STATE),
    }),
    {
      // zundo options: track only the data, not the action functions
      partialize: (state) => {
        const {
          setName,
          addState,
          renameState,
          removeState,
          moveState,
          addTransition,
          removeTransition,
          setEmission,
          setStartprob,
          setInit,
          setFit,
          loadTopology,
          reset,
          ...data
        } = state;
        return data;
      },
      limit: 50, // keep 50 history steps
    },
  ),
);

export const useTopologyTemporal = <T,>(
  selector: (state: TemporalState<TopologyState>) => T,
): T => useTopologyStore.temporal(selector);
```

- [ ] **Step 3: Verify build**

```bash
cd src/hmm_studio/frontend
npm run build
```
Expected: TS compiles, no errors.

- [ ] **Step 4: Commit**

```bash
git add src/hmm_studio/frontend/package.json src/hmm_studio/frontend/package-lock.json src/hmm_studio/frontend/src/store/
git commit -m "feat(studio): B.4.1.1 topology store with undo/redo (zustand + zundo)"
```

---

## Task B.4.1.2: Custom State node + edge components

**Files:**
- Create: `src/hmm_studio/frontend/src/components/topology/StateNode.tsx`
- Create: `src/hmm_studio/frontend/src/components/topology/TransitionEdge.tsx`
- Create: `src/hmm_studio/frontend/src/components/topology/nodeTypes.ts`

- [ ] **Step 1: `StateNode.tsx`**

```tsx
import { memo } from "react";
import { Handle, Position, NodeProps } from "reactflow";
import { useTopologyStore } from "../../store/topologyStore";

interface StateNodeData {
  label: string;
}

function StateNodeImpl({ id, data, selected }: NodeProps<StateNodeData>) {
  const renameState = useTopologyStore((s) => s.renameState);

  return (
    <div
      className={
        "px-4 py-2 rounded-full border-2 bg-white shadow-sm min-w-[80px] text-center " +
        (selected
          ? "border-brand-600 ring-2 ring-brand-500/30"
          : "border-slate-300")
      }
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!bg-brand-500 !w-2 !h-2"
      />
      <input
        value={data.label}
        onChange={(e) => renameState(id, e.target.value)}
        onClick={(e) => e.stopPropagation()}
        className="w-full bg-transparent text-center text-sm font-medium text-slate-900 outline-none"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="!bg-brand-500 !w-2 !h-2"
      />
    </div>
  );
}

export const StateNode = memo(StateNodeImpl);
```

- [ ] **Step 2: `TransitionEdge.tsx`** (optional polish — use default bezier edge for MVP)

Skip a custom edge component. Use the default React Flow `bezier` edge type — it's fine.

- [ ] **Step 3: `nodeTypes.ts`**

```ts
import { NodeTypes } from "reactflow";
import { StateNode } from "./StateNode";

export const nodeTypes: NodeTypes = {
  state: StateNode,
};
```

- [ ] **Step 4: Build + commit**

```bash
cd src/hmm_studio/frontend
npm run build
```

```bash
git add src/hmm_studio/frontend/src/components/topology/
git commit -m "feat(studio): B.4.1.2 StateNode component with inline rename"
```

---

## Task B.4.1.3: Topology page (canvas + side panel + toolbar)

**Files:**
- Modify: `src/hmm_studio/frontend/src/pages/TopologyPage.tsx` (replace placeholder)
- Create: `src/hmm_studio/frontend/src/components/topology/Toolbar.tsx`
- Create: `src/hmm_studio/frontend/src/components/topology/SidePanel.tsx`
- Create: `src/hmm_studio/frontend/src/components/topology/EditorCanvas.tsx`

- [ ] **Step 1: `Toolbar.tsx`**

```tsx
import { useTopologyStore, useTopologyTemporal } from "../../store/topologyStore";

interface ToolbarProps {
  onValidate: () => void;
  onExport: () => void;
  onImport: () => void;
}

export function Toolbar({ onValidate, onExport, onImport }: ToolbarProps) {
  const addState = useTopologyStore((s) => s.addState);
  const undo = useTopologyTemporal((s) => s.undo);
  const redo = useTopologyTemporal((s) => s.redo);
  const canUndo = useTopologyTemporal((s) => s.pastStates.length > 0);
  const canRedo = useTopologyTemporal((s) => s.futureStates.length > 0);

  const btn =
    "px-3 py-1.5 rounded text-sm border border-slate-300 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed";

  return (
    <div className="flex gap-2 items-center mb-2">
      <button
        onClick={() =>
          addState({ x: 100 + Math.random() * 300, y: 100 + Math.random() * 200 })
        }
        className={btn}
      >
        + state
      </button>
      <div className="w-px h-6 bg-slate-300" />
      <button onClick={() => undo()} disabled={!canUndo} className={btn}>
        ↶ Undo
      </button>
      <button onClick={() => redo()} disabled={!canRedo} className={btn}>
        ↷ Redo
      </button>
      <div className="w-px h-6 bg-slate-300" />
      <button onClick={onImport} className={btn}>
        ↑ Import YAML
      </button>
      <button onClick={onExport} className={btn}>
        ↓ Export YAML
      </button>
      <div className="w-px h-6 bg-slate-300" />
      <button onClick={onValidate} className={btn}>
        ✓ Re-validate
      </button>
    </div>
  );
}
```

- [ ] **Step 2: `SidePanel.tsx`** — emission/init/fit settings

```tsx
import { useTopologyStore } from "../../store/topologyStore";
import type { EmissionType, CovarianceType } from "../../store/topologyStore";

interface SidePanelProps {
  validationError: string | null;
  validationSummary: string | null;
}

export function SidePanel({ validationError, validationSummary }: SidePanelProps) {
  const name = useTopologyStore((s) => s.name);
  const setName = useTopologyStore((s) => s.setName);
  const emission = useTopologyStore((s) => s.emission);
  const setEmission = useTopologyStore((s) => s.setEmission);
  const init = useTopologyStore((s) => s.init);
  const setInit = useTopologyStore((s) => s.setInit);
  const fit = useTopologyStore((s) => s.fit);
  const setFit = useTopologyStore((s) => s.setFit);

  const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
    <div className="mb-4">
      <h3 className="text-xs font-semibold uppercase text-slate-500 mb-2">
        {title}
      </h3>
      <div className="space-y-2">{children}</div>
    </div>
  );

  const Row = ({ label, children }: { label: string; children: React.ReactNode }) => (
    <label className="flex items-center justify-between gap-2 text-sm">
      <span className="text-slate-700">{label}</span>
      {children}
    </label>
  );

  const inputCls =
    "border border-slate-300 rounded px-2 py-1 text-sm w-32 focus:outline-none focus:ring-2 focus:ring-brand-500/40";

  return (
    <div className="w-72 border-l border-slate-200 bg-white p-4 overflow-y-auto">
      <Section title="Model">
        <Row label="Name">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className={inputCls}
          />
        </Row>
      </Section>

      <Section title="Emission">
        <Row label="Type">
          <select
            value={emission.type}
            onChange={(e) =>
              setEmission({
                ...emission,
                type: e.target.value as EmissionType,
              })
            }
            className={inputCls}
          >
            <option value="gaussian">gaussian</option>
            <option value="gmm">gmm</option>
            <option value="multinomial">multinomial</option>
            <option value="poisson">poisson</option>
          </select>
        </Row>
        {(emission.type === "gaussian" || emission.type === "gmm") && (
          <>
            <Row label="n_features">
              <input
                type="number"
                min={1}
                value={emission.n_features ?? 1}
                onChange={(e) =>
                  setEmission({
                    ...emission,
                    n_features: parseInt(e.target.value, 10),
                  })
                }
                className={inputCls}
              />
            </Row>
            <Row label="covariance">
              <select
                value={emission.covariance_type ?? "full"}
                onChange={(e) =>
                  setEmission({
                    ...emission,
                    covariance_type: e.target.value as CovarianceType,
                  })
                }
                className={inputCls}
              >
                <option value="full">full</option>
                <option value="diag">diag</option>
                <option value="tied">tied</option>
                <option value="spherical">spherical</option>
              </select>
            </Row>
          </>
        )}
        {emission.type === "gmm" && (
          <Row label="n_mix">
            <input
              type="number"
              min={1}
              value={emission.n_mix ?? 2}
              onChange={(e) =>
                setEmission({ ...emission, n_mix: parseInt(e.target.value, 10) })
              }
              className={inputCls}
            />
          </Row>
        )}
        {emission.type === "multinomial" && (
          <Row label="n_symbols">
            <input
              type="number"
              min={2}
              value={emission.n_symbols ?? 2}
              onChange={(e) =>
                setEmission({
                  ...emission,
                  n_symbols: parseInt(e.target.value, 10),
                })
              }
              className={inputCls}
            />
          </Row>
        )}
        {emission.type === "poisson" && (
          <Row label="n_features">
            <input
              type="number"
              min={1}
              value={emission.n_features ?? 1}
              onChange={(e) =>
                setEmission({
                  ...emission,
                  n_features: parseInt(e.target.value, 10),
                })
              }
              className={inputCls}
            />
          </Row>
        )}
      </Section>

      <Section title="Init">
        <Row label="Strategy">
          <select
            value={init.strategy}
            onChange={(e) =>
              setInit({ ...init, strategy: e.target.value as InitSpec["strategy"] })
            }
            className={inputCls}
          >
            <option value="uniform">uniform</option>
            <option value="random">random</option>
            <option value="kmeans">kmeans</option>
            <option value="data_frequencies">data_frequencies</option>
          </select>
        </Row>
        <Row label="Seed">
          <input
            type="number"
            value={init.seed}
            onChange={(e) => setInit({ ...init, seed: parseInt(e.target.value, 10) })}
            className={inputCls}
          />
        </Row>
      </Section>

      <Section title="Fit">
        <Row label="n_iter">
          <input
            type="number"
            min={1}
            value={fit.n_iter}
            onChange={(e) => setFit({ ...fit, n_iter: parseInt(e.target.value, 10) })}
            className={inputCls}
          />
        </Row>
        <Row label="tol">
          <input
            type="number"
            step={1e-5}
            value={fit.tol}
            onChange={(e) => setFit({ ...fit, tol: parseFloat(e.target.value) })}
            className={inputCls}
          />
        </Row>
      </Section>

      <Section title="Validation">
        {validationError ? (
          <p className="text-xs text-red-700 bg-red-50 border border-red-200 rounded px-2 py-1">
            {validationError}
          </p>
        ) : validationSummary ? (
          <p className="text-xs text-green-700 bg-green-50 border border-green-200 rounded px-2 py-1">
            {validationSummary}
          </p>
        ) : (
          <p className="text-xs text-slate-500">…</p>
        )}
      </Section>
    </div>
  );
}

// Local re-import to satisfy TypeScript in inline annotation above.
import type { InitSpec } from "../../store/topologyStore";
```

- [ ] **Step 3: `EditorCanvas.tsx`**

```tsx
import { useCallback } from "react";
import ReactFlow, {
  Background,
  Controls,
  Connection,
  Edge,
  Node,
  NodeChange,
  applyNodeChanges,
  EdgeChange,
  applyEdgeChanges,
} from "reactflow";
import "reactflow/dist/style.css";
import { nodeTypes } from "./nodeTypes";
import { useTopologyStore } from "../../store/topologyStore";

export function EditorCanvas() {
  const states = useTopologyStore((s) => s.states);
  const transitions = useTopologyStore((s) => s.transitions);
  const moveState = useTopologyStore((s) => s.moveState);
  const removeState = useTopologyStore((s) => s.removeState);
  const addTransition = useTopologyStore((s) => s.addTransition);
  const removeTransition = useTopologyStore((s) => s.removeTransition);

  const nodes: Node[] = states.map((s) => ({
    id: s.id,
    type: "state",
    position: s.position,
    data: { label: s.name },
  }));

  const edges: Edge[] = transitions.map((t) => ({
    id: t.id,
    source: t.source,
    target: t.target,
    type: "default",
    style: { strokeWidth: 2 },
  }));

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      changes.forEach((change) => {
        if (change.type === "position" && change.position && change.dragging === false) {
          moveState(change.id, change.position);
        }
        if (change.type === "remove") {
          removeState(change.id);
        }
      });
    },
    [moveState, removeState],
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      changes.forEach((change) => {
        if (change.type === "remove") removeTransition(change.id);
      });
    },
    [removeTransition],
  );

  const onConnect = useCallback(
    (conn: Connection) => {
      if (conn.source && conn.target) addTransition(conn.source, conn.target);
    },
    [addTransition],
  );

  return (
    <div className="flex-1 border border-slate-200 rounded">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        fitView
        deleteKeyCode={["Backspace", "Delete"]}
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
```

- [ ] **Step 4: Rewrite `pages/TopologyPage.tsx`** (this stitches it all together; live validation + import/export are in B.4.1.4)

```tsx
import { useState } from "react";
import { EditorCanvas } from "../components/topology/EditorCanvas";
import { Toolbar } from "../components/topology/Toolbar";
import { SidePanel } from "../components/topology/SidePanel";

export default function TopologyPage() {
  const [validationError] = useState<string | null>(null);
  const [validationSummary] = useState<string | null>(null);

  return (
    <div className="flex h-[calc(100vh-4rem)] -mx-8 -my-8">
      <div className="flex-1 flex flex-col p-4 min-w-0">
        <Toolbar
          onValidate={() => {/* B.4.1.4 */}}
          onExport={() => {/* B.4.1.4 */}}
          onImport={() => {/* B.4.1.4 */}}
        />
        <EditorCanvas />
      </div>
      <SidePanel
        validationError={validationError}
        validationSummary={validationSummary}
      />
    </div>
  );
}
```

- [ ] **Step 5: Build + commit**

```bash
cd src/hmm_studio/frontend && npm run build
```

```bash
git add src/hmm_studio/frontend/src/components/topology/ src/hmm_studio/frontend/src/pages/TopologyPage.tsx
git commit -m "feat(studio): B.4.1.3 topology editor page (canvas + toolbar + side panel)"
```

---

## Task B.4.1.4: Live validation + YAML import/export

**Files:**
- Create: `src/hmm_studio/frontend/src/lib/yaml.ts`
- Modify: `src/hmm_studio/frontend/src/pages/TopologyPage.tsx` (wire up real handlers)

- [ ] **Step 1: `lib/yaml.ts`** — serialize the store state into the hmm-core YAML format and back

```ts
import yaml from "js-yaml";
import type { TopologyState } from "../store/topologyStore";

interface TopologyYAML {
  name: string;
  n_states: number;
  state_names: string[];
  emission: {
    type: string;
    n_features?: number | null;
    covariance_type?: string | null;
    n_mix?: number | null;
    n_symbols?: number | null;
  };
  allowed_transitions?: string[][];
  startprob: string | number[];
  init: { strategy: string; seed: number };
  fit: { algorithm: string; n_iter: number; tol: number };
}

export function topologyToYAML(state: TopologyState): string {
  const obj: TopologyYAML = {
    name: state.name,
    n_states: state.states.length,
    state_names: state.states.map((s) => s.name),
    emission: {
      type: state.emission.type,
      n_features: state.emission.n_features ?? undefined,
      covariance_type: state.emission.covariance_type ?? undefined,
      n_mix: state.emission.n_mix ?? undefined,
      n_symbols: state.emission.n_symbols ?? undefined,
    },
    allowed_transitions: state.transitions.map((t) => {
      const srcName = state.states.find((s) => s.id === t.source)?.name ?? t.source;
      const tgtName = state.states.find((s) => s.id === t.target)?.name ?? t.target;
      return [srcName, tgtName];
    }),
    startprob: state.startprob,
    init: state.init,
    fit: state.fit,
  };
  // Strip undefined keys for cleaner YAML output
  obj.emission = Object.fromEntries(
    Object.entries(obj.emission).filter(([, v]) => v !== undefined),
  ) as TopologyYAML["emission"];
  if (!obj.allowed_transitions || obj.allowed_transitions.length === 0) {
    delete obj.allowed_transitions;
  }
  return yaml.dump(obj, { lineWidth: 100 });
}

export function yamlToTopology(text: string): Partial<TopologyState> {
  const obj = yaml.load(text) as TopologyYAML;
  // Rebuild states with synthetic positions
  const states = (obj.state_names || []).map((name, i) => ({
    id: `s-${i}-${Math.random().toString(36).slice(2, 6)}`,
    name,
    position: { x: 80 + (i % 4) * 180, y: 80 + Math.floor(i / 4) * 140 },
  }));
  const nameToId = new Map(states.map((s) => [s.name, s.id]));
  const transitions = (obj.allowed_transitions || []).map((pair, i) => ({
    id: `e-${i}-${Math.random().toString(36).slice(2, 6)}`,
    source: nameToId.get(pair[0]) ?? pair[0],
    target: nameToId.get(pair[1]) ?? pair[1],
  }));
  return {
    name: obj.name ?? "untitled",
    states,
    transitions,
    emission: {
      type: (obj.emission?.type ?? "gaussian") as TopologyState["emission"]["type"],
      n_features: obj.emission?.n_features ?? null,
      covariance_type:
        (obj.emission?.covariance_type ?? null) as TopologyState["emission"]["covariance_type"],
      n_mix: obj.emission?.n_mix ?? null,
      n_symbols: obj.emission?.n_symbols ?? null,
    },
    startprob:
      typeof obj.startprob === "string"
        ? (obj.startprob as "uniform" | "first_state")
        : (obj.startprob as number[]),
    init: {
      strategy: (obj.init?.strategy ?? "kmeans") as TopologyState["init"]["strategy"],
      seed: obj.init?.seed ?? 42,
    },
    fit: {
      algorithm: "baum_welch",
      n_iter: obj.fit?.n_iter ?? 200,
      tol: obj.fit?.tol ?? 1e-4,
    },
  };
}
```

- [ ] **Step 2: Create a debounce hook + validation hook**

Create `src/hmm_studio/frontend/src/hooks/useDebouncedValidation.ts`:

```ts
import { useEffect, useState } from "react";
import { useTopologyStore } from "../store/topologyStore";
import { topologyToYAML } from "../lib/yaml";
import { validateTopology } from "../api/client";

interface ValidationResult {
  error: string | null;
  summary: string | null;
}

const EMPTY_RESULT: ValidationResult = { error: null, summary: null };

export function useDebouncedValidation(delayMs = 400): ValidationResult {
  const states = useTopologyStore((s) => s.states);
  const transitions = useTopologyStore((s) => s.transitions);
  const emission = useTopologyStore((s) => s.emission);
  const name = useTopologyStore((s) => s.name);
  const init = useTopologyStore((s) => s.init);
  const fit = useTopologyStore((s) => s.fit);
  const startprob = useTopologyStore((s) => s.startprob);

  const [result, setResult] = useState<ValidationResult>(EMPTY_RESULT);

  useEffect(() => {
    if (states.length === 0) {
      setResult({ error: "no states yet — add at least one", summary: null });
      return;
    }
    const handle = setTimeout(async () => {
      const yamlText = topologyToYAML(useTopologyStore.getState());
      try {
        const r = await validateTopology(yamlText);
        if (r.valid) {
          setResult({ error: null, summary: r.summary });
        } else {
          setResult({ error: r.error ?? "invalid", summary: null });
        }
      } catch (e) {
        setResult({
          error: e instanceof Error ? e.message : "network error",
          summary: null,
        });
      }
    }, delayMs);
    return () => clearTimeout(handle);
    // Re-run validation whenever anything that affects the YAML changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [states, transitions, emission, name, init, fit, startprob, delayMs]);

  return result;
}
```

- [ ] **Step 3: Wire up TopologyPage**

Replace `src/hmm_studio/frontend/src/pages/TopologyPage.tsx` with:

```tsx
import { useRef } from "react";
import { EditorCanvas } from "../components/topology/EditorCanvas";
import { Toolbar } from "../components/topology/Toolbar";
import { SidePanel } from "../components/topology/SidePanel";
import { useTopologyStore } from "../store/topologyStore";
import { topologyToYAML, yamlToTopology } from "../lib/yaml";
import { useDebouncedValidation } from "../hooks/useDebouncedValidation";

export default function TopologyPage() {
  const validation = useDebouncedValidation();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  function handleExport() {
    const state = useTopologyStore.getState();
    const yamlText = topologyToYAML(state);
    const blob = new Blob([yamlText], { type: "application/x-yaml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${state.name || "topology"}.yaml`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function handleImportClick() {
    fileInputRef.current?.click();
  }

  function handleImportFile(file: File) {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const text = String(reader.result);
        const partial = yamlToTopology(text);
        useTopologyStore.getState().loadTopology(partial);
      } catch (e) {
        alert(`Failed to import YAML: ${e instanceof Error ? e.message : "?"}`);
      }
    };
    reader.readAsText(file);
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] -mx-8 -my-8">
      <div className="flex-1 flex flex-col p-4 min-w-0">
        <Toolbar
          onValidate={() => {
            // Force a fresh validation by touching the store; trivially we
            // can just re-trigger the hook via a state push, but the
            // debounced hook already runs on each change — so this is a no-op.
          }}
          onExport={handleExport}
          onImport={handleImportClick}
        />
        <input
          ref={fileInputRef}
          type="file"
          accept=".yaml,.yml"
          style={{ display: "none" }}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleImportFile(f);
            e.target.value = "";
          }}
        />
        <EditorCanvas />
      </div>
      <SidePanel
        validationError={validation.error}
        validationSummary={validation.summary}
      />
    </div>
  );
}
```

- [ ] **Step 4: Build + commit**

```bash
cd src/hmm_studio/frontend && npm run build
```

```bash
git add src/hmm_studio/frontend/src/lib/yaml.ts src/hmm_studio/frontend/src/hooks/useDebouncedValidation.ts src/hmm_studio/frontend/src/pages/TopologyPage.tsx
git commit -m "feat(studio): B.4.1.4 live validation + YAML import/export"
```

---

## Task B.4.1.5: Polish + smoke test + README update

- [ ] **Step 1: Rebuild + copy frontend into server static**

```bash
python scripts/build_frontend.py
```

- [ ] **Step 2: Manual smoke test**

```bash
hmm-studio serve --port 8765
```

In a browser, open `http://127.0.0.1:8765/topology`:
- The page renders the React Flow canvas + side panel.
- Click "+ state" 3 times → 3 nodes appear.
- Rename nodes by clicking on their text and typing.
- Drag from a node's right handle to another node's left handle → an edge is created.
- The "Validation" section in the side panel should show ✓ green when valid.
- Click "Export YAML" → a file downloads.
- Click "Import YAML" → file picker opens.
- Click "Undo" → the last action reverts.

Stop the server.

- [ ] **Step 3: Update README to mention B.4.1**

In `README.md`, under the Web UI section, replace the "Frontend (B.3+) is not yet implemented" line with:

```markdown
The visual topology editor (B.4.1) is shipped: open `/topology` after
running `hmm-studio serve` to dessine your model graphically. Data upload
(B.5) and results view (B.6) are next.
```

- [ ] **Step 4: Python tests still pass**

```bash
pytest -q --tb=no
```
Expected: 120 passed, no regression.

- [ ] **Step 5: Commit**

```bash
git add README.md src/hmm_studio/server/static/index.html src/hmm_studio/server/static/assets/
# Actually static is gitignored — only README changes
git add README.md
git commit -m "docs: B.4.1 topology editor shipped"
```

---

## Done criteria

After all 5 tasks:
- The `/topology` route in `hmm-studio serve` renders a working React Flow editor.
- Users can add/rename/delete states, draw transitions, undo/redo (50 steps), export to YAML, import from YAML.
- Live validation against `/api/topology/validate` shows error or success in the side panel.
- The exported YAML is byte-compatible with `hmm-fit run <yaml> <data.csv>`.
- 120 Python tests still pass.

## Out of scope (deferred)

- **A.8** : per-state EmissionSpec (extend hmm_core.Topology).
- **A.9** : Dirichlet priors on transitions (extend hmm_core.Topology).
- **B.4.2** : Per-state emission UI (depends on A.8).
- **B.4.3** : Edge weight override UI (depends on A.9).
- **B.4.x** : Snap-to-grid, multi-select, copy-paste, contextual menu — future polish.
