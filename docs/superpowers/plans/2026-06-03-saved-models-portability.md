# Saved-Models Portability — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make each saved topology a portable artifact — export it as a YAML file, share it via URL, import a YAML file into the library — plus whole-library JSON backup/restore, reusing the existing `topologyToYAML`/`yamlToTopology`/`buildShareUrl` primitives. No backend change.

**Architecture:** A pure `modelLibraryIO` module (serialize/parse/merge) is unit-tested in isolation. `topologyToYAML`/`buildShareUrl` are widened from `TopologyState` to its data subset `TopologyData` so a saved entry's `.data` can be exported. The select-based saved switcher is replaced by a toggled **"My models"** panel with per-row actions and library import/export. The whole-library JSON is shaped to be forward-compatible with the future A1 multi-tab docs-map.

**Tech Stack:** React 18 + TS + Vite 5, zustand 4, vitest, Playwright (`e2e/`).

**Spec:** [`docs/superpowers/specs/2026-06-03-saved-models-portability-design.md`](../specs/2026-06-03-saved-models-portability-design.md).

**Preconditions (not tasks):**
- Work in the worktree root `C:\Users\rdenis\VScode\Tools\hmm_studio-inc3` on branch `feat/editor-increment-3` (off `main`). Frontend commands from `src/hmm_studio/frontend`.
- Commit identity = `roblastar@live.fr`; append `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Do NOT use gitnexus tools; read code directly. `node_modules` is NOT installed in this fresh worktree — run `npm install` in `src/hmm_studio/frontend` before the first `npm` command (or the first task does it).
- Browser-visual steps: substitute with `npm run lint` + `npm run build` + reasoning; flag human visual QA.
- **User-confirmed defaults:** library-merge = keep-existing + an "overwrite" option; UI = a "My models" panel.

**Reused contracts (from Increment 2):**
- `savedTopologiesStore` — `{ saved: Record<name, SavedTopology>, save(entry), remove(name) }`, `SavedTopology = { name, data: TopologyData, savedAt }`, localStorage key `hmm-studio-saved-topologies`.
- `topologyToYAML` / `yamlToTopology` (`lib/yaml.ts`), `buildShareUrl` (`lib/share.ts`), `TopologyData` (`store/topologyStore.ts`).

---

## Task 0: Install deps (one-off)

- [ ] **Step 1:** From `src/hmm_studio/frontend`, run `npm install`. Expected: success, `node_modules` present. Then `npm test` (should be 36 passed — Increment 2's suite) and `npm run build` (green) to confirm the baseline.

---

## Task 1: Widen `topologyToYAML` + `buildShareUrl` to accept `TopologyData`

**Why:** A saved entry's `.data` is a `TopologyData` (the data subset), but `topologyToYAML`/`buildShareUrl` currently require the full `TopologyState`. Both only READ data fields, so narrowing the param to `TopologyData` is safe and lets us export/share a saved model. `TopologyState` callers still pass (structural superset).

**Files:** Modify `src/hmm_studio/frontend/src/lib/yaml.ts`, `src/hmm_studio/frontend/src/lib/share.ts`.

- [ ] **Step 1:** In `lib/yaml.ts`, change the import + signature of `topologyToYAML`:
  - Ensure `TopologyData` is imported: `import type { CovarianceType, EmissionType, TopologyState, TopologyData } from "../store/topologyStore";` (add `TopologyData`).
  - Change `export function topologyToYAML(state: TopologyState): string {` → `export function topologyToYAML(state: TopologyData): string {`.
  - Nothing else changes (the body only reads `state.name/states/transitions/emission/startprob/init/fit/transmat_prior_alpha`, all in `TopologyData`).

- [ ] **Step 2:** In `lib/share.ts`, change `buildShareUrl`'s param type:
  - `import type { TopologyState, TopologyData } from "../store/topologyStore";` (add `TopologyData`; keep `TopologyState` if still used by `TopologyPartial`).
  - `export function buildShareUrl(state: TopologyState): string {` → `export function buildShareUrl(state: TopologyData): string {`.

- [ ] **Step 3:** Verify `npm run lint` (0) and `npm run build` (0). Existing callers (`FitPage`, `TopologyPage`, `Toolbar`) pass the full store state — still valid (superset). `npm test` (36) green.

- [ ] **Step 4: Commit.**

```bash
git add src/hmm_studio/frontend/src/lib/yaml.ts src/hmm_studio/frontend/src/lib/share.ts
git commit -m "refactor(topology): topologyToYAML/buildShareUrl accept TopologyData (enable saved-model export)"
```

---

## Task 2: Pure `modelLibraryIO` — serialize / parse / merge

**Files:** Create `src/hmm_studio/frontend/src/lib/modelLibraryIO.ts` + `.test.ts`.

- [ ] **Step 1: Write the failing test.** Create `src/hmm_studio/frontend/src/lib/modelLibraryIO.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { serializeLibrary, parseLibrary, mergeModels } from "./modelLibraryIO";
import type { SavedTopology } from "../store/savedTopologiesStore";

const entry = (name: string): SavedTopology => ({
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

describe("modelLibraryIO", () => {
  it("serialize → parse round-trips the models", () => {
    const saved = { alpha: entry("alpha"), beta: entry("beta") };
    const json = serializeLibrary(saved);
    const parsed = parseLibrary(json);
    expect(parsed.error).toBeNull();
    expect(Object.keys(parsed.models!).sort()).toEqual(["alpha", "beta"]);
    expect(parsed.models!.alpha.data.name).toBe("alpha");
  });

  it("serialized payload carries schema_version + kind", () => {
    const obj = JSON.parse(serializeLibrary({ a: entry("a") }));
    expect(obj.schema_version).toBe(1);
    expect(obj.kind).toBe("hmm-studio-model-library");
  });

  it("parse rejects a wrong-kind payload", () => {
    expect(parseLibrary(JSON.stringify({ kind: "something-else", models: {} })).error).toMatch(/kind/i);
  });

  it("parse rejects malformed JSON", () => {
    expect(parseLibrary("{not json").error).toBeTruthy();
  });

  it("mergeModels keep-existing: incoming does not overwrite a same name", () => {
    const existing = { a: entry("a") };
    const incoming = { a: { ...entry("a"), savedAt: 999 }, b: entry("b") };
    const merged = mergeModels(existing, incoming, "keep-existing");
    expect(merged.a.savedAt).toBe(0); // kept
    expect(merged.b.name).toBe("b"); // added
  });

  it("mergeModels overwrite: incoming replaces a same name", () => {
    const existing = { a: entry("a") };
    const incoming = { a: { ...entry("a"), savedAt: 999 } };
    const merged = mergeModels(existing, incoming, "overwrite");
    expect(merged.a.savedAt).toBe(999);
  });
});
```

- [ ] **Step 2:** Run `npm test -- modelLibraryIO` → FAIL (module missing).

- [ ] **Step 3: Implement.** Create `src/hmm_studio/frontend/src/lib/modelLibraryIO.ts`:

```ts
import type { SavedTopology } from "../store/savedTopologiesStore";

const KIND = "hmm-studio-model-library";
const SCHEMA_VERSION = 1;

type Library = Record<string, SavedTopology>;
export type MergeMode = "keep-existing" | "overwrite";

/** Serialize the saved-models library to a portable JSON string. The envelope
 *  (schema_version + kind + models map) is forward-compatible with the future
 *  multi-tab docs-map (the `models` map IS that map). */
export function serializeLibrary(saved: Library): string {
  return JSON.stringify({ schema_version: SCHEMA_VERSION, kind: KIND, models: saved }, null, 2);
}

/** Parse + validate a library JSON. Returns `{ models }` on success or
 *  `{ error }` on malformed/wrong-kind input. Pure (no store access). */
export function parseLibrary(text: string): { models: Library | null; error: string | null } {
  let obj: unknown;
  try {
    obj = JSON.parse(text);
  } catch {
    return { models: null, error: "Not valid JSON." };
  }
  const o = obj as { kind?: unknown; models?: unknown };
  if (o.kind !== KIND) {
    return { models: null, error: `Wrong kind: expected "${KIND}".` };
  }
  if (!o.models || typeof o.models !== "object") {
    return { models: null, error: "Missing or invalid `models`." };
  }
  return { models: o.models as Library, error: null };
}

/** Merge an incoming library into the existing one. keep-existing (default)
 *  never overwrites a name already present; overwrite replaces same names. */
export function mergeModels(existing: Library, incoming: Library, mode: MergeMode): Library {
  if (mode === "overwrite") return { ...existing, ...incoming };
  return { ...incoming, ...existing }; // existing wins on key collision
}
```

- [ ] **Step 4:** Run `npm test -- modelLibraryIO` → PASS (6). **Lint** (0). **Commit.**

```bash
git add src/hmm_studio/frontend/src/lib/modelLibraryIO.ts src/hmm_studio/frontend/src/lib/modelLibraryIO.test.ts
git commit -m "feat(topology): pure model-library serialize/parse/merge (export-import core)"
```

---

## Task 3: `setSaved` store action + "My models" panel skeleton (Load/Delete)

**Why:** Replace the two `<select>` switchers with a toggled panel listing saved models (per-row Load/Delete to start). Add a `setSaved` action for whole-library import (Task 5).

**Files:** Modify `src/hmm_studio/frontend/src/store/savedTopologiesStore.ts`; Create `src/hmm_studio/frontend/src/components/topology/SavedModelsPanel.tsx`; Modify `src/hmm_studio/frontend/src/components/topology/Toolbar.tsx`.

- [ ] **Step 1: Add `setSaved` to the store.** In `savedTopologiesStore.ts`:
  - In `SavedTopologiesState`, after `remove`, add: `setSaved: (saved: Record<string, SavedTopology>) => void;`
  - In the store object, add: `setSaved: (saved) => set({ saved }),`

- [ ] **Step 2: Create the panel.** Create `src/hmm_studio/frontend/src/components/topology/SavedModelsPanel.tsx`:

```tsx
import { useSavedTopologies } from "../../store/savedTopologiesStore";

/** A toggled "My models" panel. This skeleton renders the list with Load/Delete
 *  per row; Export/Share (Task 4) and Import/Backup (Task 5) are added next. */
export function SavedModelsPanel({ onLoad, onClose }: { onLoad: (name: string) => void; onClose: () => void }) {
  const saved = useSavedTopologies((s) => s.saved);
  const removeModel = useSavedTopologies((s) => s.remove);
  const names = Object.keys(saved);

  return (
    <div className="absolute z-20 mt-1 w-80 max-h-80 overflow-auto rounded border border-slate-300 bg-white shadow-lg p-2 text-sm">
      <div className="flex items-center justify-between mb-2">
        <span className="font-medium text-slate-700">My models ({names.length})</span>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-700" title="Close">✕</button>
      </div>
      {names.length === 0 && <p className="text-xs text-slate-400 px-1 py-2">No saved models yet.</p>}
      <ul className="space-y-1">
        {names.map((n) => (
          <li key={n} className="flex items-center gap-1 px-1 py-0.5 rounded hover:bg-slate-50">
            <span className="flex-1 truncate" title={n}>{n}</span>
            <button onClick={() => onLoad(n)} className="px-1.5 py-0.5 rounded border border-slate-200 hover:bg-slate-100" title="Load into editor">Load</button>
            <button
              onClick={() => { if (window.confirm(`Delete saved model "${n}"?`)) removeModel(n); }}
              className="px-1.5 py-0.5 rounded border border-slate-200 text-red-600 hover:bg-red-50"
              title="Delete"
            >🗑</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 3: Wire into Toolbar.** In `Toolbar.tsx`:
  - Add `import { SavedModelsPanel } from "./SavedModelsPanel";`
  - Add panel state: `const [showModels, setShowModels] = useState(false);` (reuse the existing `useState` import).
  - Replace the two `<select>` blocks (the "📂 Load saved…" and "🗑 Delete…" selects, current lines ~181-210) with a single toggle button + the panel (keep the "💾 Save model" button just before it):
    ```tsx
          <div className="relative inline-block">
            <button onClick={() => setShowModels((v) => !v)} className={btn}>
              📂 My models ({Object.keys(saved).length})
            </button>
            {showModels && (
              <SavedModelsPanel
                onLoad={(n) => { handleLoadSaved(n); setShowModels(false); }}
                onClose={() => setShowModels(false)}
              />
            )}
          </div>
    ```
  - Keep `handleLoadSaved` and `handleSaveCurrent` as they are. The `removeModel` read in Toolbar is now unused (moved into the panel) — remove the `const removeModel = ...` line if lint flags it unused.

- [ ] **Step 4:** Verify `npm run lint` (0), `npm run build` (0), `npm test` (36) green.

- [ ] **Step 5: (visual — substitute)** Reason: the toggle button shows the saved count; clicking opens the panel; Load reuses `handleLoadSaved` (with the clobber guard) and closes; Delete confirms + `remove`. Note human QA on open/close + load/delete.

- [ ] **Step 6: Commit.**

```bash
git add src/hmm_studio/frontend/src/store/savedTopologiesStore.ts src/hmm_studio/frontend/src/components/topology/SavedModelsPanel.tsx src/hmm_studio/frontend/src/components/topology/Toolbar.tsx
git commit -m "feat(topology): 'My models' panel replaces the select switcher (+ setSaved)"
```

---

## Task 4: Per-model Export YAML + Share

**Files:** Modify `src/hmm_studio/frontend/src/components/topology/SavedModelsPanel.tsx`.

- [ ] **Step 1: Add Export + Share per row.** In `SavedModelsPanel.tsx`, add imports:

```ts
import { topologyToYAML } from "../../lib/yaml";
import { buildShareUrl } from "../../lib/share";
```

Add handlers inside the component:

```ts
  function exportModel(name: string) {
    const entry = saved[name];
    if (!entry) return;
    const blob = new Blob([topologyToYAML(entry.data)], { type: "application/x-yaml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${name || "model"}.yaml`;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function shareModel(name: string) {
    const entry = saved[name];
    if (!entry) return;
    const url = buildShareUrl(entry.data);
    try {
      await navigator.clipboard.writeText(url);
      // eslint-disable-next-line no-alert
      alert("Share link copied to clipboard.");
    } catch {
      // eslint-disable-next-line no-alert
      alert("Copy failed — URL:\n" + url);
    }
  }
```

In each `<li>`, add the two buttons (between Load and Delete):

```tsx
            <button onClick={() => exportModel(n)} className="px-1.5 py-0.5 rounded border border-slate-200 hover:bg-slate-100" title="Download as .yaml">⬇ YAML</button>
            <button onClick={() => shareModel(n)} className="px-1.5 py-0.5 rounded border border-slate-200 hover:bg-slate-100" title="Copy a share URL">⎘</button>
```

- [ ] **Step 2:** Verify `npm run lint` (0), `npm run build` (0).

- [ ] **Step 3: (visual — substitute)** Reason: Export downloads `<name>.yaml` via the now-`TopologyData`-typed `topologyToYAML(entry.data)` (Task 1); Share copies a `?topology=` URL via `buildShareUrl(entry.data)`. Both reuse the existing primitives — byte-equivalent to the current-model Export/Share, just on a saved entry. Note: large models may exceed URL length — acceptable (export the file instead).

- [ ] **Step 4: Commit.**

```bash
git add src/hmm_studio/frontend/src/components/topology/SavedModelsPanel.tsx
git commit -m "feat(topology): export-YAML + share-URL per saved model"
```

---

## Task 5: Import a model + whole-library backup/restore

**Files:** Modify `src/hmm_studio/frontend/src/components/topology/SavedModelsPanel.tsx`.

- [ ] **Step 1: Add library actions.** In `SavedModelsPanel.tsx`, add imports:

```ts
import { useRef } from "react";
import { yamlToTopology } from "../../lib/yaml";
import { serializeLibrary, parseLibrary, mergeModels } from "../../lib/modelLibraryIO";
```

Read the store setters/save + a file-input ref:

```ts
  const saveModel = useSavedTopologies((s) => s.save);
  const setSaved = useSavedTopologies((s) => s.setSaved);
  const yamlInputRef = useRef<HTMLInputElement | null>(null);
  const jsonInputRef = useRef<HTMLInputElement | null>(null);
```

Add handlers:

```ts
  function importModelFile(file: File) {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const partial = yamlToTopology(String(reader.result));
        const proposed = (partial.name as string) || "imported";
        const name = window.prompt("Save imported model as:", proposed);
        if (!name) return;
        if (saved[name] && !window.confirm(`"${name}" exists — overwrite?`)) return;
        saveModel({
          name,
          data: {
            name,
            states: partial.states ?? [],
            transitions: partial.transitions ?? [],
            emission: partial.emission!,
            startprob: partial.startprob ?? "uniform",
            init: partial.init!,
            fit: partial.fit!,
            transmat_prior_alpha: partial.transmat_prior_alpha ?? null,
          },
          savedAt: Date.now(),
        });
      } catch (e) {
        // eslint-disable-next-line no-alert
        alert(`Import failed: ${e instanceof Error ? e.message : "?"}`);
      }
    };
    reader.readAsText(file);
  }

  function exportLibrary() {
    const blob = new Blob([serializeLibrary(saved)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "hmm-studio-models.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  function importLibraryFile(file: File) {
    const reader = new FileReader();
    reader.onload = () => {
      const { models, error } = parseLibrary(String(reader.result));
      if (error || !models) {
        // eslint-disable-next-line no-alert
        alert(`Import failed: ${error ?? "invalid library"}`);
        return;
      }
      const overwrite = window.confirm("Overwrite models with the same name? (Cancel = keep existing)");
      setSaved(mergeModels(saved, models, overwrite ? "overwrite" : "keep-existing"));
    };
    reader.readAsText(file);
  }
```

Add a library action bar at the bottom of the panel (before the closing `</div>`), plus two hidden file inputs:

```tsx
      <div className="flex gap-1 mt-2 pt-2 border-t border-slate-200">
        <button onClick={() => yamlInputRef.current?.click()} className="px-1.5 py-0.5 rounded border border-slate-200 hover:bg-slate-100 text-xs" title="Import a .yaml model into the library">↑ Import model</button>
        <button onClick={exportLibrary} disabled={names.length === 0} className="px-1.5 py-0.5 rounded border border-slate-200 hover:bg-slate-100 text-xs disabled:opacity-40" title="Download the whole library as JSON">⬇ Export all</button>
        <button onClick={() => jsonInputRef.current?.click()} className="px-1.5 py-0.5 rounded border border-slate-200 hover:bg-slate-100 text-xs" title="Import a library JSON (merge)">↑ Import library</button>
      </div>
      <input ref={yamlInputRef} type="file" accept=".yaml,.yml" className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) importModelFile(f); e.target.value = ""; }} />
      <input ref={jsonInputRef} type="file" accept=".json" className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) importLibraryFile(f); e.target.value = ""; }} />
```

- [ ] **Step 2:** Verify `npm run lint` (0), `npm run build` (0), `npm test` (still 42 = 36 + 6 modelLibraryIO) green.

- [ ] **Step 3: (visual — substitute)** Reason: Import model parses a `.yaml` → name prompt (overwrite-guarded) → `save`. Export all downloads `hmm-studio-models.json` (schema_version + kind + models). Import library parses + `mergeModels` (overwrite vs keep-existing per the confirm) → `setSaved`. All client-side. Note human QA: round-trip a library between two browser profiles.

- [ ] **Step 4: Commit.**

```bash
git add src/hmm_studio/frontend/src/components/topology/SavedModelsPanel.tsx
git commit -m "feat(topology): import model + library backup/restore (JSON merge)"
```

---

## Task 6: E2E coverage

**Files:** Modify `e2e/tests/topology-editor.spec.ts`.

- [ ] **Step 1: Append a describe.** Add tests (resilient, short waits; server may be down — that's fine):

```ts
test.describe("Saved-models portability", () => {
  test("save a model then export it as YAML", async ({ page }) => {
    await page.goto("/topology");
    await page.waitForTimeout(400);
    await page.getByRole("button", { name: /\+ state/i }).click();
    await page.waitForTimeout(150);
    page.on("dialog", (d) => d.accept("e2e-export"));
    await page.getByRole("button", { name: /Save model/i }).click();
    await page.waitForTimeout(150);
    await page.getByRole("button", { name: /My models/i }).click();
    await page.waitForTimeout(150);
    const dl = page.waitForEvent("download");
    await page.getByRole("button", { name: /YAML/i }).first().click();
    expect((await dl).suggestedFilename()).toMatch(/\.yaml$/);
  });

  test("export-all downloads a library JSON", async ({ page }) => {
    await page.goto("/topology");
    await page.waitForTimeout(400);
    await page.getByRole("button", { name: /\+ state/i }).click();
    page.on("dialog", (d) => d.accept("e2e-lib"));
    await page.getByRole("button", { name: /Save model/i }).click();
    await page.waitForTimeout(150);
    await page.getByRole("button", { name: /My models/i }).click();
    await page.waitForTimeout(150);
    const dl = page.waitForEvent("download");
    await page.getByRole("button", { name: /Export all/i }).click();
    expect((await dl).suggestedFilename()).toMatch(/\.json$/);
  });
});
```

- [ ] **Step 2: Validate** with `npx playwright test --list` from `e2e/` (specs discovered). A run failing on `net::ERR_CONNECTION_REFUSED` (no server) is acceptable. **Step 3: Commit.**

```bash
git add e2e/tests/topology-editor.spec.ts
git commit -m "test(e2e): saved-model export YAML + library export-all"
```

---

## Self-Review (run after writing all tasks — fix inline)

- **Spec coverage:** §3.2 per-model export/share → Tasks 1, 4. §3.3 import model → Task 5. §3.4 library backup → Tasks 2, 5. §3.1 "My models" panel → Task 3. §3.5 pure helpers → Task 2.
- **Contracts:** `topologyToYAML`/`buildShareUrl` accept `TopologyData` (T1) used by T4/T5; `serializeLibrary`/`parseLibrary`/`mergeModels` (T2) used by T5; `setSaved` (T3) used by T5; `SavedTopology` shape reused. Names consistent.
- **Build-green per task:** T1 widens types (callers still pass); T3 replaces the selects + keeps Save/Load; each later task is additive.
- **No backend change**, no model pollution (saved library is already a separate store), YAML is the interchange format the backend already reads.
- **Defaults honored:** merge keep-existing default + overwrite option (T2/T5); "My models" panel (T3).

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-03-saved-models-portability.md`. Two execution options:

**1. Subagent-Driven (recommended)** — fresh subagent per task + two-stage review, in this session.
**2. Inline Execution** — execute tasks here with checkpoints.

Which approach?
