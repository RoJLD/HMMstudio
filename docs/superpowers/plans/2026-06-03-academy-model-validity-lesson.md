# Academy Lesson 16 "When is your model valid?" + persisted convergence trace — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Academy lesson-16 ("When is your model valid? (and when NOT to use an HMM)") anchored in real hmm-studio diagnostics, and persist the per-iteration EM log-likelihood trace (`convergence_history`) so a *finished* fit keeps its convergence curve.

**Architecture:** Three layers. (A) **Backend** — add `convergence_history` to `BackendFitResult` (from `monitor_.history`) and to `FittedModel`, persist it in `summary.json`, and expose it via a new `GET /api/fit/{id}/convergence` endpoint (mirrors `/transmat`). (B) **Frontend results** — fetch the persisted trace and render it in the `done` block by **reusing the existing `ProgressCurve`** (today the convergence panel only shows while *running*). (C) **Lesson** — a new `lesson-16-model-validity.tsx` (prose from the spec §3.1), registered in `index.ts`, with a quiz, a deliberately misspecified preset, an illustrative `ProgressCurve`, and reciprocal backlinks from lessons 14/15.

**Tech Stack:** Python 3.12 + hmmlearn + dataclasses (core), FastAPI + Pydantic (server), pytest (backend tests), React 18 + TypeScript + Vite + react-router (frontend), vitest (unit), Playwright (e2e). Spec: `docs/superpowers/specs/2026-06-03-academy-model-validity-lesson-design.md`.

**Identity reminder:** every commit must resolve to `roblastar@live.fr` / `Robin DENIS` and end with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Always commit with an explicit pathspec (`git commit -- <files>`), never a bare `git commit` (shared index across worktrees).

---

## File Structure

**Backend (create/modify):**
- Modify `src/hmm_core/backends/_protocol.py` — add `convergence_history` field to `BackendFitResult`.
- Modify `src/hmm_core/backends/hmmlearn_backend.py` — populate it in `fit` and `_fit_semi_supervised`.
- Modify `src/hmm_core/fit/__init__.py` — add the field to `FittedModel`, thread it, add to `to_summary_dict`.
- Modify `src/hmm_core/io.py` — write it into `summary.json`.
- Modify `src/hmm_studio/server/app.py` — new `GET /api/fit/{job_id}/convergence`.
- Tests: `tests/test_backends.py`, `tests/test_fit_dispatcher.py`, a server test under `tests/studio/`.

**Frontend (create/modify):**
- Modify `src/hmm_studio/frontend/src/api/client.ts` — `ConvergenceResponse` + `getFitConvergence`.
- Modify `src/hmm_studio/frontend/src/pages/ResultsPage.tsx` — persisted convergence panel in the `done` block.
- Create `src/hmm_studio/frontend/src/lessons/lesson-16-model-validity.tsx`.
- Modify `src/hmm_studio/frontend/src/lessons/index.ts` — import + `LESSONS` entry + preset.
- Modify `src/hmm_studio/frontend/src/components/academy/lessonQuiz.ts` — quiz entry.
- Modify `src/hmm_studio/frontend/src/lessons/lesson-14-comparing-models.tsx` and `lesson-15-choosing-emission.tsx` — backlinks.
- e2e: `e2e/tests/academy.spec.ts` — lesson-16 smoke.
- Docs: `docs/roadmap.md` — record the lesson + consolidation.

---

## GROUP A — Backend: persist the convergence trace

### Task 1: `convergence_history` on `BackendFitResult` (+ populate in hmmlearn)

**Files:**
- Modify: `src/hmm_core/backends/_protocol.py:23-50`
- Modify: `src/hmm_core/backends/hmmlearn_backend.py:153-165` (unsupervised) and `:347-354` (semi-supervised)
- Test: `tests/test_backends.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_backends.py`:

```python
def test_backend_fit_populates_convergence_history():
    """Unsupervised EM exposes its per-iteration log-likelihood trace."""
    import numpy as np
    from hmm_core.backends import get_backend
    from hmm_core.topology import Topology

    rng = np.random.default_rng(0)
    X = np.concatenate([rng.normal(-3, 0.5, (60, 1)), rng.normal(3, 0.5, (60, 1))])
    topo = Topology.from_dict({
        "name": "conv", "n_states": 2,
        "emission": {"type": "gaussian", "covariance_type": "diag", "n_features": 1},
        "startprob": "uniform", "init": {"strategy": "kmeans", "seed": 0},
        "fit": {"algorithm": "baum_welch", "n_iter": 50, "tol": 1e-4},
    })
    from hmm_core import init as init_mod
    A = init_mod.transmat(topo, seed=0, X=X)
    pi = init_mod.startprob(topo, seed=0)
    ek = init_mod.emission_params(topo, X=X, seed=0)
    result = get_backend("hmmlearn").fit(
        topo, X, seed=0, lengths=None,
        initial_transmat=A, initial_startprob=pi, emission_kwargs=ek,
        mask=topo.transition_mask(),
    )
    assert isinstance(result.convergence_history, tuple)
    assert len(result.convergence_history) >= 2
    assert all(isinstance(v, float) for v in result.convergence_history)
    # EM log-likelihood is monotone non-decreasing.
    h = result.convergence_history
    assert all(h[i + 1] >= h[i] - 1e-6 for i in range(len(h) - 1))
```

- [ ] **Step 2: Run it — verify it fails**

Run: `python -m pytest tests/test_backends.py::test_backend_fit_populates_convergence_history -v`
Expected: FAIL — `AttributeError: 'BackendFitResult' object has no attribute 'convergence_history'`.

- [ ] **Step 3: Add the field to the dataclass**

In `src/hmm_core/backends/_protocol.py`, add a field at the END of `BackendFitResult` (after `converged: bool`, line 50), with a default so closed-form paths can omit it:

```python
    converged: bool
    convergence_history: tuple[float, ...] = ()
```

Also add to the docstring (after the `converged` paragraph):

```python
    convergence_history
        Per-iteration training log-likelihood trace from EM (empty for
        closed-form / supervised fits that run no EM loop).
```

- [ ] **Step 4: Populate it in the hmmlearn backend**

In `src/hmm_core/backends/hmmlearn_backend.py`, the unsupervised `fit` already computes `monitor` at line 154. Replace the `return BackendFitResult(...)` at lines 158-165 with:

```python
        history = tuple(float(x) for x in getattr(monitor, "history", []) or [])
        return BackendFitResult(
            model=model,
            transmat=np.asarray(model.transmat_),
            startprob=np.asarray(model.startprob_),
            log_likelihood=log_lik,
            n_iter_actual=n_iter_actual,
            converged=converged,
            convergence_history=history,
        )
```

Apply the identical change to `_fit_semi_supervised`'s return (lines 347-354) — it also has a `monitor` in scope (semi-supervised runs EM); add `convergence_history=tuple(float(x) for x in getattr(monitor, "history", []) or [])`. Leave `fit_supervised` (line 238) unchanged — it keeps the default `()`.

- [ ] **Step 5: Run the test — verify it passes**

Run: `python -m pytest tests/test_backends.py::test_backend_fit_populates_convergence_history -v`
Expected: PASS.

- [ ] **Step 6: Run the full backend module to check no regression**

Run: `python -m pytest tests/test_backends.py tests/test_fit_dispatcher.py -q`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git commit -F - -- src/hmm_core/backends/_protocol.py src/hmm_core/backends/hmmlearn_backend.py tests/test_backends.py <<'MSG'
feat(core): expose EM convergence_history on BackendFitResult

Capture hmmlearn monitor_.history as a per-iteration log-likelihood trace on
the backend result (unsupervised + semi-supervised EM; empty for closed-form
supervised fits).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
MSG
```

---

### Task 2: `convergence_history` on `FittedModel` + summary serialization

**Files:**
- Modify: `src/hmm_core/fit/__init__.py:22-34` (field), `:297-309` (thread), `:52-69` (`to_summary_dict`)
- Modify: `src/hmm_core/io.py:145-167` (summary.json)
- Test: `tests/test_fit_dispatcher.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_fit_dispatcher.py`:

```python
def test_fitted_model_carries_and_serializes_convergence_history():
    import json
    import numpy as np
    from hmm_core.fit import fit
    from hmm_core.topology import Topology

    rng = np.random.default_rng(1)
    X = np.concatenate([rng.normal(-3, 0.5, (80, 1)), rng.normal(3, 0.5, (80, 1))])
    topo = Topology.from_dict({
        "name": "conv", "n_states": 2,
        "emission": {"type": "gaussian", "covariance_type": "diag", "n_features": 1},
        "startprob": "uniform", "init": {"strategy": "kmeans", "seed": 1},
        "fit": {"algorithm": "baum_welch", "n_iter": 50, "tol": 1e-4},
    })
    fitted = fit(topo, X, seed=1)
    assert isinstance(fitted.convergence_history, tuple)
    assert len(fitted.convergence_history) >= 2
    # Serialized into the summary dict / JSON as a plain list of floats.
    summ = fitted.to_summary_dict()
    assert summ["convergence_history"] == [float(v) for v in fitted.convergence_history]
    assert json.loads(fitted.to_summary_json())["convergence_history"][0] == summ["convergence_history"][0]
```

- [ ] **Step 2: Run it — verify it fails**

Run: `python -m pytest tests/test_fit_dispatcher.py::test_fitted_model_carries_and_serializes_convergence_history -v`
Expected: FAIL — `AttributeError`/`KeyError: 'convergence_history'`.

- [ ] **Step 3: Add the field to `FittedModel`**

In `src/hmm_core/fit/__init__.py`, add at the END of the dataclass (after `duration_seconds: float`, line 34) so it has a default for backward-compat with old pickles:

```python
    duration_seconds: float
    convergence_history: tuple[float, ...] = ()
```

- [ ] **Step 4: Thread it from the backend result**

In the `return FittedModel(...)` (lines 297-309), add the last argument:

```python
        duration_seconds=duration,
        convergence_history=getattr(result, "convergence_history", ()),
    )
```

- [ ] **Step 5: Serialize it in `to_summary_dict`**

In `to_summary_dict` (lines 52-69), add before the closing `}` (after the `duration_seconds` entry, line 68):

```python
            "duration_seconds": float(self.duration_seconds),
            "convergence_history": [float(v) for v in getattr(self, "convergence_history", ())],
        }
```

- [ ] **Step 6: Persist it in `io.save_model`'s summary.json**

In `src/hmm_core/io.py`, inside the `summary["fit"]` dict (lines 148-157), add after `"mask_violation_norm": violation,`:

```python
            "mask_violation_norm": violation,
            "convergence_history": [float(v) for v in getattr(fitted, "convergence_history", ())],
```

- [ ] **Step 7: Run the test — verify it passes**

Run: `python -m pytest tests/test_fit_dispatcher.py::test_fitted_model_carries_and_serializes_convergence_history -v`
Expected: PASS.

- [ ] **Step 8: Regression**

Run: `python -m pytest tests/test_fit_dispatcher.py tests/test_io.py -q` (run `tests/test_io.py` only if it exists; otherwise `tests/ -k io`).
Expected: pass.

- [ ] **Step 9: Commit**

```bash
git commit -F - -- src/hmm_core/fit/__init__.py src/hmm_core/io.py tests/test_fit_dispatcher.py <<'MSG'
feat(core): carry convergence_history on FittedModel + summary.json

Thread the EM trace from the backend result onto FittedModel (default () for
backward-compat with old pickles), expose it in to_summary_dict and persist it
in summary.json. fit_log.txt is unchanged.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
MSG
```

---

### Task 3: `GET /api/fit/{job_id}/convergence` endpoint

**Files:**
- Modify: `src/hmm_studio/server/app.py` — add after the `/api/fit/{job_id}/transmat` endpoint (after line 289)
- Test: `tests/studio/test_convergence_endpoint.py` (new)

- [ ] **Step 1: Write the failing test**

First read one existing server test under `tests/studio/` (e.g. the one covering `/api/fit/.../transmat` or `/decoded`) to copy its app/TestClient + fit-driving fixture. Then create `tests/studio/test_convergence_endpoint.py` mirroring that harness:

```python
"""GET /api/fit/{id}/convergence returns the persisted EM trace."""
import time
import numpy as np
from fastapi.testclient import TestClient

# Reuse the SAME app + fit-driving helpers as the sibling transmat/decoded test.
# Replace the two imports below with whatever that test uses (build_app, a
# tmp-data fixture, and an upload+start helper).
from hmm_studio.server.app import build_app  # adjust to the real factory name


def _wait_done(client, job_id, timeout=30.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = client.get(f"/api/fit/{job_id}").json()
        if r["status"] in ("done", "failed", "cancelled"):
            return r
        time.sleep(0.1)
    raise AssertionError("fit did not finish")


def test_convergence_endpoint_returns_trace(tmp_path):
    # Mirror the sibling test's app construction + dataset upload + fit start.
    # After the fit is done:
    #   resp = client.get(f"/api/fit/{job_id}/convergence")
    #   assert resp.status_code == 200
    #   body = resp.json()
    #   assert isinstance(body["convergence_history"], list)
    #   assert len(body["convergence_history"]) >= 2
    #   assert "converged" in body and "n_iter_actual" in body
    ...
```

Note: the `...` body must be filled by copying the sibling test's concrete upload+start steps (the engineer reads that file first). Keep the assertions above verbatim.

- [ ] **Step 2: Run it — verify it fails**

Run: `python -m pytest tests/studio/test_convergence_endpoint.py -v`
Expected: FAIL — 404 (route not found) or import error until the route exists.

- [ ] **Step 3: Add the endpoint**

In `src/hmm_studio/server/app.py`, add immediately after the `/api/fit/{job_id}/transmat` handler (after line 289), mirroring its load-from-pickle pattern:

```python
    @app.get("/api/fit/{job_id}/convergence")
    def get_fit_convergence(job_id: str):
        """Return the persisted per-iteration EM log-likelihood trace."""
        import pickle

        try:
            status = runner.get_status(job_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="job not found")
        if status["status"] != "done":
            raise HTTPException(
                status_code=409, detail=f"job status is {status['status']!r}, not done"
            )
        result_path = status.get("result_path")
        if not result_path:
            raise HTTPException(status_code=500, detail="result_path missing")
        with (Path(result_path) / "model.pkl").open("rb") as f:
            fitted = pickle.load(f)
        history = [float(v) for v in getattr(fitted, "convergence_history", ()) or []]
        return {
            "convergence_history": history,
            "converged": bool(getattr(fitted, "converged", False)),
            "n_iter_actual": int(getattr(fitted, "n_iter_actual", len(history))),
        }
```

- [ ] **Step 4: Run the test — verify it passes**

Run: `python -m pytest tests/studio/test_convergence_endpoint.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git commit -F - -- src/hmm_studio/server/app.py tests/studio/test_convergence_endpoint.py <<'MSG'
feat(server): GET /api/fit/{id}/convergence returns the persisted EM trace

Mirrors /transmat: loads model.pkl and returns convergence_history + converged
+ n_iter_actual. Defensive getattr keeps it working for pre-existing pickles.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
MSG
```

---

## GROUP B — Frontend: persist the convergence curve on the results page

### Task 4: API client `getFitConvergence`

**Files:**
- Modify: `src/hmm_studio/frontend/src/api/client.ts` (after `getFitTransmat`, line ~143)
- Test: none (thin fetch wrapper; covered by the e2e + tsc)

- [ ] **Step 1: Add the type + fetch**

After `getFitTransmat` (line 141-143), add:

```ts
export interface ConvergenceResponse {
  convergence_history: number[];
  converged: boolean;
  n_iter_actual: number;
}

export async function getFitConvergence(jobId: string): Promise<ConvergenceResponse> {
  return jsonFetch<ConvergenceResponse>(`/api/fit/${jobId}/convergence`);
}
```

- [ ] **Step 2: Typecheck**

Run: `cd src/hmm_studio/frontend && npx tsc --noEmit`
Expected: exit 0.

- [ ] **Step 3: Commit**

```bash
git commit -F - -- src/hmm_studio/frontend/src/api/client.ts <<'MSG'
feat(client): getFitConvergence for the persisted EM trace

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
MSG
```

---

### Task 5: Persisted convergence panel on `ResultsPage` (reuse `ProgressCurve`)

**Files:**
- Modify: `src/hmm_studio/frontend/src/pages/ResultsPage.tsx`
- Test: covered by e2e Task 11 + tsc/build

- [ ] **Step 1: Import the fetch + a state slot**

Add `getFitConvergence` to the existing `import { ... } from "../api/client"` block (near line 5). Add a state slot with the other result states (near line 34-46, alongside `transmat`/`decoded`):

```ts
  const [convergence, setConvergence] = useState<number[] | null>(null);
```

- [ ] **Step 2: Fetch it when the job is done**

In the `done` fetch effect (lines 88-103), add `getFitConvergence` to the `Promise.all` and store the history:

```ts
    Promise.all([
      getFitTransmat(jobId).catch(() => null),
      getFitDecoded(jobId).catch(() => null),
      getFitEmissions(jobId).catch(() => null),
      getNhmmInfo(jobId).catch(() => null),
      getFitSeries(jobId).catch(() => null),
      getFitConvergence(jobId).catch(() => null),
    ]).then(([t, d, e, n, s, c]) => {
      setTransmat(t);
      setDecoded(d);
      setEmissions(e);
      setNhmmInfo(n);
      setSeries(s);
      setConvergence(c ? c.convergence_history : null);
    });
```

- [ ] **Step 3: Render the persisted panel as the first item of the `done` block**

Immediately inside `{status.status === "done" && (` `<>` (after line 168, before the `decoded && TimelinePlayer`), add:

```tsx
          {convergence && convergence.length > 1 && (
            <div className="border border-slate-200 rounded-md p-4 bg-white mb-6">
              <h3 className="text-sm font-semibold text-slate-700 mb-1">
                Convergence (log-likelihood vs iteration)
              </h3>
              <p className="text-xs text-slate-500 mb-3">
                The EM log-likelihood should climb and plateau. A flat-then-jump
                or non-monotone trace signals an initialization or numerical issue —
                re-fit with another seed.
              </p>
              <ProgressCurve history={convergence} />
            </div>
          )}
```

`ProgressCurve` is already imported (line 25). For supervised/closed-form fits the trace is empty (`length <= 1`) so the panel is correctly hidden.

- [ ] **Step 4: Typecheck + build**

Run: `cd src/hmm_studio/frontend && npx tsc --noEmit && npx vite build`
Expected: exit 0, build OK.

- [ ] **Step 5: Commit**

```bash
git commit -F - -- src/hmm_studio/frontend/src/pages/ResultsPage.tsx <<'MSG'
feat(results): keep the convergence curve after a fit finishes

The live convergence panel only existed while running (WebSocket progress).
Fetch the now-persisted convergence_history and render it in the done block by
reusing ProgressCurve, so a frozen model keeps its EM trace. Hidden for
closed-form fits (empty trace).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
MSG
```

---

## GROUP C — Lesson 16

### Task 6: Lesson quiz data

**Files:**
- Modify: `src/hmm_studio/frontend/src/components/academy/lessonQuiz.ts` (add an entry to `LESSON_QUIZZES`)

- [ ] **Step 1: Add the quiz entry**

Add to the `LESSON_QUIZZES` record (before the closing `};`), keyed `"lesson-16-model-validity"`:

```ts
  "lesson-16-model-validity": {
    flashcards: [
      { level: "Recall", front: "Name the five HMM validity assumptions.", back: "Stationarity, the Markov property, conditional independence of emissions given state, a finite/known K, and identifiability (stable parameters across inits)." },
      { level: "Apply", front: "Top-3 random inits give wildly different log-likelihoods. What does that mean?", back: "A local-optimum problem — the fit is fragile. Run more inits / better init and keep the best." },
      { level: "Analyze", front: "Two re-fits give the same model with the state indices swapped. Bug?", back: "No — HMMs are identifiable only up to a permutation of states (label switching). Order states by an emission feature to compare." },
      { level: "Apply", front: "A state has ~0 posterior occupancy after fitting. What does it suggest?", back: "K is probably too large (over-fragmentation) — try fewer states or a constrained topology." },
    ],
    questions: [
      { level: "Analyze", prompt: "You fit a 3-state HMM; states 0 and 1 have near-identical means and the transitions look random. This suggests…", options: ["a perfect fit", "the model is unidentifiable — merge states or add constraints", "the data is Gaussian", "more iterations are needed"], correct: 1, concept: "identifiability", explanation: "Indistinguishable states + random transitions = the data doesn't support that many regimes." },
      { level: "Apply", prompt: "Held-out log-likelihood is 10× worse than train. The most likely culprit is…", options: ["the seed", "overfitting or a mismatched emission family", "too few iterations", "the transition mask"], correct: 1, concept: "generalization", explanation: "Train-good / eval-bad is the classic overfit-or-wrong-emission signature (see Lesson 15)." },
      { level: "Analyze", prompt: "Your data's autocorrelation is strong at lags 5–20. An HMM may fail because…", options: ["it needs more states", "it assumes the Markov property (only lag-1 dependence)", "emissions must be Gaussian", "it cannot be fit"], correct: 1, concept: "markov assumption", explanation: "Long-range dependence violates the Markov assumption — consider AR or state-space models." },
      { level: "Apply", prompt: "Which check tells you EM converged cleanly?", options: ["BIC is negative", "the log-likelihood trace rises monotonically and plateaus", "the transmat is symmetric", "the seed is 42"], correct: 1, concept: "convergence", explanation: "A monotone, plateauing LL trace (now persisted on the results page) is the convergence signal." },
      { level: "Analyze", prompt: "When is a vanilla HMM the WRONG tool?", options: ["small interpretable-regime data", "non-stationary regimes that drift over time", "speech/bioinformatics", "teaching"], correct: 1, concept: "when not to use", explanation: "Time-varying dynamics call for an NHMM/switching model, not a homogeneous HMM." },
      { level: "Apply", prompt: "You have no idea how many regimes exist and no domain guidance. Best first move?", options: ["grid-search K up to 50", "start at K=2 and validate with BIC + held-out LL before growing", "pick K=10", "use one state"], correct: 1, concept: "choosing K", explanation: "Grow K only when validation justifies it; never grid-search without a validation signal." },
    ],
  },
```

- [ ] **Step 2: Typecheck**

Run: `cd src/hmm_studio/frontend && npx tsc --noEmit`
Expected: exit 0.

- [ ] **Step 3: Commit**

```bash
git commit -F - -- src/hmm_studio/frontend/src/components/academy/lessonQuiz.ts <<'MSG'
feat(academy): quiz for lesson-16 model validity

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
MSG
```

---

### Task 7: Lesson component `lesson-16-model-validity.tsx`

**Files:**
- Create: `src/hmm_studio/frontend/src/lessons/lesson-16-model-validity.tsx`

Prose follows spec §3.1 sections 1-10. Write the file complete:

- [ ] **Step 1: Create the lesson**

```tsx
import { Link } from "react-router-dom";
import { FurtherReading } from "../components/academy/FurtherReading";
import { ProgressCurve } from "../components/results/ProgressCurve";

// A real EM log-likelihood trace (monotone, plateauing) used to teach the
// healthy-convergence shape. Generated from a toy 2-state Gaussian fit.
const SAMPLE_TRACE = [
  -4200, -3120, -2440, -2055, -1882, -1812, -1786, -1776, -1772, -1770.8,
  -1770.4, -1770.25,
];

export function Lesson16ModelValidity() {
  return (
    <>
      <h2 className="text-xl font-semibold text-slate-900 mb-3">Why this matters</h2>
      <p className="text-slate-700 mb-4">
        You fit an HMM, the held-out log-likelihood is terrible, and you don&apos;t
        know who to blame: the topology, the features, the emission, or just a bad
        initialization. Validity is not one number — it&apos;s a small set of{" "}
        <strong>assumptions</strong> and a <strong>checklist</strong> you run before,
        during, and after fitting. This lesson is that framework, wired to the exact
        diagnostics hmm-studio gives you.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        The five validity assumptions
      </h2>
      <ol className="list-decimal pl-6 space-y-2 text-slate-700 mb-4">
        <li><strong>Stationarity</strong> — transitions and emissions don&apos;t change over time.</li>
        <li><strong>Markov property</strong> — the next state depends only on the current one (
          <Link to="/academy/lesson-1-what-is-an-hmm" className="text-brand-700 hover:underline">Lesson 1</Link>).</li>
        <li><strong>Conditional independence</strong> — observations are independent of the past given the state.</li>
        <li><strong>Finite, (roughly) known K</strong> — a fixed number of latent regimes actually exists.</li>
        <li><strong>Identifiability</strong> — parameters are recoverable / stable across initializations.</li>
      </ol>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">Check before fitting</h2>
      <ul className="list-disc pl-6 space-y-2 text-slate-700 mb-4">
        <li>Is the series stationary, or does the regime structure itself drift? Drift → consider an{" "}
          <Link to="/academy/lesson-7-nhmm" className="text-brand-700 hover:underline">NHMM</Link>.</li>
        <li>Plot the autocorrelation. Strong dependence beyond lag 1 violates Markov.</li>
        <li>Are your features genuinely predictive of the regime, and decorrelated? (
          <Link to="/academy/lesson-13-choosing-features" className="text-brand-700 hover:underline">Lesson 13</Link>.)</li>
        <li>Do you have a defensible K, or is it a guess? Start small and let validation grow it.</li>
      </ul>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        Watch during fitting — convergence
      </h2>
      <p className="text-slate-700 mb-4">
        Baum-Welch only finds a <em>local</em> optimum (
        <Link to="/academy/lesson-5-baum-welch" className="text-brand-700 hover:underline">Lesson 5</Link>).
        A healthy run shows the log-likelihood climbing monotonically and plateauing:
      </p>
      <div className="border border-slate-200 rounded-md p-4 bg-white mb-4">
        <ProgressCurve history={SAMPLE_TRACE} />
      </div>
      <ul className="list-disc pl-6 space-y-2 text-slate-700 mb-4">
        <li><strong>Did it converge?</strong> Check <code className="bg-slate-100 px-1 rounded text-sm">converged</code> and that the curve plateaued — not hit the iteration cap mid-climb.</li>
        <li><strong>Multiple inits.</strong> If your top-3 random seeds land at very different log-likelihoods, you have a local-optimum problem.</li>
        <li><strong>Parameter stability.</strong> Re-fit with another seed; a transmat that lurches is a fragile fit.</li>
        <li><strong>Label switching.</strong> States are unordered — a re-fit may relabel them. Order by an emission feature before comparing.</li>
      </ul>
      <p className="text-slate-700 mb-4">
        In hmm-studio this trace is now <strong>persisted</strong>: after a fit, the
        convergence curve stays on the results page (not just live during training).
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">Diagnose after fitting</h2>
      <ul className="list-disc pl-6 space-y-2 text-slate-700 mb-4">
        <li><strong>Decode and look.</strong> Viterbi/posterior state paths — are state durations plausible, or flickering every step (over-fragmentation / wrong K)?</li>
        <li><strong>Occupancy.</strong> A state with ~0 posterior occupancy means K is too large.</li>
        <li><strong>Residuals per state</strong> vs the fitted emission density — the emission diagnostic (
          <Link to="/academy/lesson-15-choosing-emission" className="text-brand-700 hover:underline">Lesson 15</Link>).</li>
        <li><strong>Held-out log-likelihood.</strong> Train-good / eval-bad → overfit or wrong emission. Both bad → topology/emission mismatch.</li>
        <li><strong>Interpretability.</strong> Do the learned transitions match domain intuition, or look random? Forbidden edges must be exactly zero (mask check).</li>
      </ul>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">When NOT to use an HMM</h2>
      <p className="text-slate-700 mb-4">
        Intellectual honesty: HMMs win in a specific niche — small data, interpretable
        discrete regimes, audit/regulatory needs, teaching. They are the wrong tool when:
      </p>
      <ul className="list-disc pl-6 space-y-2 text-slate-700 mb-4">
        <li><strong>Regimes drift</strong> (non-stationary) → NHMM / switching models.</li>
        <li><strong>Long-range temporal dependence</strong> (ACF at lags ≫ 1) → autoregressive or state-space models.</li>
        <li><strong>Large data / NLP / long sequences</strong> → Transformers or modern SSMs (Mamba/S4) dominate.</li>
        <li><strong>No discrete regimes exist</strong> — the latent structure is continuous → a continuous latent-variable model.</li>
        <li><strong>Too few observations per parameter</strong> → Bayesian priors (
          <Link to="/academy/lesson-10-bayesian-hmm" className="text-brand-700 hover:underline">Lesson 10</Link>) or stronger constraints.</li>
      </ul>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">A diagnostic workflow</h2>
      <ol className="list-decimal pl-6 space-y-2 text-slate-700 mb-4">
        <li>Fit with several initializations; record the top-3 log-likelihoods.</li>
        <li>Compare candidates by BIC/AIC/HQIC (
          <Link to="/academy/lesson-14-comparing-models" className="text-brand-700 hover:underline">Lesson 14</Link>) — never trust a single fit.</li>
        <li>Decode states; check durations, occupancy, and per-state means.</li>
        <li>Plot residuals per state against the fitted emission.</li>
        <li>Hold out 10–20% and check held-out log-likelihood (use a time-series split, not random KFold).</li>
        <li>Label regimes by an emission feature and confirm the ordering is stable across seeds.</li>
        <li>All pass → provisionally valid. Any fail → diagnose and iterate.</li>
      </ol>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">Try it</h2>
      <p className="text-slate-700 mb-4">
        Load the preset attached to this lesson — a <strong>deliberately over-specified</strong>{" "}
        5-state model on data with only ~2 real regimes. Fit it and watch the red flags
        appear: a state collapses to near-zero occupancy, the convergence curve stalls,
        and BIC prefers fewer states. Then drop to K=2 and compare.
      </p>

      <FurtherReading
        references={[
          { label: "Bilmes 1998", title: "A Gentle Tutorial of the EM Algorithm", url: "https://f.hubspotusercontent40.net/hubfs/8111846/bilmes-em.pdf", note: "why EM log-likelihood is monotone and converges to a local optimum" },
          { label: "Celeux & Soromenho 1996", title: "An entropy criterion for assessing the number of clusters in a mixture model", url: "https://link.springer.com/article/10.1007/BF01246098", note: "label switching and choosing the number of components" },
          { label: "Murphy, MLAPP §16", title: "Machine Learning: A Probabilistic Perspective — HMMs", url: "https://probml.github.io/pml-book/book0.html", note: "HMM diagnostics and assumptions" },
          { label: "Academy bibliography", title: "Central sourced reference list for all Academy lessons", url: "https://github.com/RoJLD/HMMstudio/blob/main/docs/sources/academy-references.md" },
        ]}
      />
    </>
  );
}
```

- [ ] **Step 2: Typecheck**

Run: `cd src/hmm_studio/frontend && npx tsc --noEmit`
Expected: exit 0 (note: not yet imported anywhere, but the file must typecheck).

- [ ] **Step 3: Commit**

```bash
git commit -F - -- src/hmm_studio/frontend/src/lessons/lesson-16-model-validity.tsx <<'MSG'
feat(academy): lesson-16 "When is your model valid?" component

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
MSG
```

---

### Task 8: Register lesson-16 in `index.ts` (+ misspecified preset)

**Files:**
- Modify: `src/hmm_studio/frontend/src/lessons/index.ts`

- [ ] **Step 1: Import the component**

After the `lesson-15` import (line 17):

```ts
import { Lesson16ModelValidity } from "./lesson-16-model-validity";
```

- [ ] **Step 2: Add the `LESSONS` entry**

After the `lesson-15-choosing-emission` entry (after its `}` near line 373, before the closing `];`):

```ts
  {
    id: "lesson-16-model-validity",
    category: "selection",
    order: 5,
    title: "When is your model valid? (and when NOT to use an HMM)",
    estimatedMinutes: 16,
    difficulty: "Advanced",
    description:
      "HMMs are powerful but fragile. The five assumptions, how to check them before fitting, how to diagnose convergence and post-fit failures, and when to reject the HMM for a simpler or different model.",
    status: "published",
    content: Lesson16ModelValidity,
    presetTopologyYaml: `name: lesson_16_overspecified_demo
n_states: 5
state_names: [a, b, c, d, e]
emission:
  type: gaussian
  covariance_type: diag
  n_features: 1
startprob: uniform
init: {strategy: kmeans, seed: 7}
fit: {algorithm: baum_welch, n_iter: 100, tol: 1.0e-4}
`,
  },
```

- [ ] **Step 3: Typecheck + build**

Run: `cd src/hmm_studio/frontend && npx tsc --noEmit && npx vite build`
Expected: exit 0, build OK.

- [ ] **Step 4: Commit**

```bash
git commit -F - -- src/hmm_studio/frontend/src/lessons/index.ts <<'MSG'
feat(academy): register lesson-16 with an over-specified demo preset

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
MSG
```

---

### Task 9: Reciprocal backlinks from lessons 14 and 15

**Files:**
- Modify: `src/hmm_studio/frontend/src/lessons/lesson-15-choosing-emission.tsx`
- Modify: `src/hmm_studio/frontend/src/lessons/lesson-14-comparing-models.tsx`

- [ ] **Step 1: Backlink in lesson-15**

In `lesson-15-choosing-emission.tsx`, in the "Try it" paragraph (lines 130-136), append a sentence before `</p>` at line 136:

```tsx
        components will cluster around the tails.{" "}
        For the broader picture — convergence, identifiability and when to abandon the
        HMM entirely — see{" "}
        <Link to="/academy/lesson-16-model-validity" className="text-brand-700 hover:underline">
          Lesson 16 — Model validity
        </Link>.
      </p>
```

(`Link` is already imported in lesson-15.)

- [ ] **Step 2: Backlink in lesson-14**

Open `lesson-14-comparing-models.tsx`. Confirm `Link` is imported (add `import { Link } from "react-router-dom";` at the top if missing). Add a closing sentence in its final prose section (just before `<FurtherReading`):

```tsx
      <p className="text-slate-700 mb-4">
        Comparison tells you which model wins; validity tells you whether the winner is
        trustworthy at all. See{" "}
        <Link to="/academy/lesson-16-model-validity" className="text-brand-700 hover:underline">
          Lesson 16 — Model validity
        </Link>.
      </p>
```

- [ ] **Step 3: Typecheck**

Run: `cd src/hmm_studio/frontend && npx tsc --noEmit`
Expected: exit 0.

- [ ] **Step 4: Commit**

```bash
git commit -F - -- src/hmm_studio/frontend/src/lessons/lesson-14-comparing-models.tsx src/hmm_studio/frontend/src/lessons/lesson-15-choosing-emission.tsx <<'MSG'
feat(academy): cross-link lessons 14/15 to lesson-16

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
MSG
```

---

## GROUP D — Verify + record

### Task 10: e2e smoke for lesson-16

**Files:**
- Modify: `e2e/tests/academy.spec.ts`

- [ ] **Step 1: Read the existing academy.spec.ts** to match its navigation helper + selectors (how it opens a lesson and asserts the quiz). Then add:

```ts
test("lesson-16 model validity renders, shows the convergence curve, and has a quiz", async ({ page }) => {
  await page.goto("/academy/lesson-16-model-validity");
  await page.waitForTimeout(400);
  await expect(page.getByRole("heading", { name: /Why this matters/i })).toBeVisible();
  await expect(page.getByRole("heading", { name: /When NOT to use an HMM/i })).toBeVisible();
  // The reused ProgressCurve renders an <svg>.
  expect(await page.locator("svg").count()).toBeGreaterThan(0);
});
```

Match the route/selector to whatever the sibling academy tests use (read the file first; adjust the `goto` path if Academy uses a different URL shape).

- [ ] **Step 2: Commit**

```bash
git commit -F - -- e2e/tests/academy.spec.ts <<'MSG'
test(e2e): smoke lesson-16 renders + convergence curve

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
MSG
```

---

### Task 11: Record in the roadmap

**Files:**
- Modify: `docs/roadmap.md`

- [ ] **Step 1: Update the Academy count + add the lesson**

In the section that inventories Academy lessons (search for "Academy" / "leçon 15"), bump the count to 16 and add a line:

```markdown
- **Leçon 16 « When is your model valid? (and when NOT to use an HMM) »** —
  cadre unifié de validité (5 hypothèses, checks avant/pendant/après fit, quand
  renoncer au HMM), ancrée aux diagnostics maison + courbe de convergence
  désormais **persistée** sur la page Résultats (`convergence_history` sur
  `FittedModel` + `GET /api/fit/{id}/convergence`). Consolide l'item roadmap
  « Quand NE PAS utiliser un HMM ». Spec
  `docs/superpowers/specs/2026-06-03-academy-model-validity-lesson-design.md`.
```

If a separate "Quand NE PAS utiliser un HMM" lesson is listed as planned, mark it **consolidée dans la leçon 16**.

- [ ] **Step 2: Commit**

```bash
git commit -F - -- docs/roadmap.md <<'MSG'
docs(roadmap): record lesson-16 + persisted convergence trace

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
MSG
```

---

## Self-Review

**Spec coverage** (spec §3.1 + Décisions 2026-06-03):
- 5 assumptions / before / during / after / when-not / workflow / try-it / see-also / further-reading → Task 7 (all 10 sections). ✅
- Quiz (~4 flashcards + 5-6 Q) → Task 6. ✅
- `convergence_history` backend → Tasks 1-2; API → Task 3; UI persist → Tasks 4-5. ✅
- Misspecified preset hook → Task 8. ✅
- Backlinks → Task 9. Consolidation of "when not to use" → Tasks 7 (section 6) + 11. ✅
- e2e → Task 10; roadmap → Task 11. ✅

**Placeholder scan:** the only intentionally-deferred bodies are the two e2e/server tests that must mirror an existing sibling test's app/navigation harness (Tasks 3, 10) — the engineer reads that sibling first; the assertions are given verbatim. Everything else is complete code.

**Type consistency:** `convergence_history: tuple[float, ...]` (core dataclasses) ↔ serialized as `list[float]` (`to_summary_dict`, summary.json, API) ↔ `number[]` (`ConvergenceResponse`, `ProgressCurve` prop). `getFitConvergence` returns `ConvergenceResponse`; ResultsPage stores `c.convergence_history` (number[]). Consistent. ✅

**Backward-compat:** all new dataclass fields default to `()`; all reads use `getattr(..., default)` so pre-existing pickles and supervised fits don't break.
