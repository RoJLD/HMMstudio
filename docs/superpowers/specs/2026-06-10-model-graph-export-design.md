# Model-graph export — design

**Date**: 2026-06-10
**Status**: current
**Scope**: a new, isolated, additive export surface (`hmm_core.export_graph`) — no
change to fit/backends/topology.

## 1. Contexte / problème

hmm_studio fits HMMs; the **gitnexus Graph Platform** (sister project) can import,
visualize (2D/3D, layouts, matrix), run graph-theory (centrality, communities,
dead-weights), overlay activations, and **diff** any graph that arrives in its generic
`model-graph` JSON contract — but only if something *emits* that contract. gitnexus
defined the contract + a synthetic fixture; this is the **"both ends owned"** producer:
a fitted HMM is *literally* a state-transition graph (zero tracing), so exporting it is
cheap and turns the gitnexus pipeline real end-to-end on actual trained models.

This is an **integration/interop surface** (like the existing save/load `io.py`,
Jupyter, sklearn surfaces), not a pivot out of HMM-land: it serializes an HMM *as a
graph*; gitnexus happens to be the consumer of that portable format.

## 2. Objectif

Two pure functions on a `FittedModel` produce serializable dicts matching the gitnexus
contract:
- `export_model_graph(fitted, *, name=None) -> dict` — the **static** structure:
  states + transitions (always), observations + emissions (discrete/multinomial only).
- `export_activations(fitted, X, *, name=None, lengths=None) -> dict` — the **dynamic**
  overlay from a decoded sequence: per-state occupancy + per-transition frequency.

Success: fitting a small Gaussian left-right HMM and exporting yields a `model-graph`
dict with K state nodes + the non-zero transitions as weighted edges; exporting
activations over a sequence yields per-state occupancies summing to ~1 and transition
counts along the Viterbi path. A multinomial HMM additionally yields observation nodes
+ emission edges.

## 3. Design

New module `src/hmm_core/export_graph.py` (mirrors `io.py` style: NumPy docstrings,
`from __future__ import annotations`, stdlib `json`-friendly dicts, `ValueError` on bad
input). Exported from `hmm_core/__init__.py`.

### 3.1 `export_model_graph(fitted, *, name=None) -> dict`

Reads `A = fitted.model.transmat_` (K×K), `topo = fitted.topology` (`n_states`,
`state_names`, `emission`). Builds:

- **`model`**: `{ "name": name or topo.name, "framework": "hmm", "version": <hmm_core version> }`.
- **State nodes**: for each state `s = state_names[i]` → `{ "id": s, "type": "state",
  "label": s }`.
- **Transition edges**: for each `(i, j)` with `A[i, j] > EPS` (EPS = 1e-9, drops
  forbidden/masked edges) → `{ "from": state_names[i], "to": state_names[j],
  "kind": "transition", "weight": float(A[i, j]) }`.
- **Emissions — multinomial ONLY** (`topo.emission.type == "multinomial"`, where discrete
  observation symbols + `emissionprob_` exist): observation nodes
  `{ "id": f"obs_{k}", "type": "observation", "label": f"obs_{k}" }` for
  `k in range(n_symbols)`, and emission edges `{ "from": state_names[i], "to": f"obs_{k}",
  "kind": "emission", "weight": float(emissionprob_[i, k]) }` for `emissionprob_[i,k] > EPS`.
  For **continuous** emissions (gaussian/gmm/poisson) there is no discrete observation
  node — emissions are **omitted** (the exported graph is states + transitions, still a
  valid, useful model graph). Documented; richer continuous-emission representation
  deferred (§5).

`framework` version: read `hmm_core.__version__` if present, else `None`.

### 3.2 `export_activations(fitted, X, *, name=None, lengths=None) -> dict`

Reads the model's inference methods (`predict_proba`, `predict`). Builds:
- **`model`**: `{ "name": name or topo.name, "version": <version> }`.
- **`run`**: `{ "n_samples": int(len(X)), "seed": fitted.seed }`.
- **Node magnitudes** (state occupancy): `gamma = fitted.model.predict_proba(X)` (T×K),
  `occ = gamma.mean(axis=0)` → `{ state_names[i]: float(occ[i]) }`. (Occupancies sum ~1.)
- **Edge frequencies** (transition counts along the Viterbi path): `path =
  fitted.model.predict(X)` (T,), count consecutive `(path[t], path[t+1])` pairs →
  `{ f"{state_names[i]}->transition->{state_names[j]}": int(count) }`. Edge id matches the
  gitnexus importer convention `${from}->${kind}->${to}` (kind = `transition`). Only
  observed (count > 0) transitions are emitted. `lengths` (hmmlearn multi-sequence
  convention) is passed through to `predict`/`predict_proba` and used to NOT count
  transitions across sequence boundaries.

### 3.3 Variants (NHMM / GMM-NHMM)

v1 targets the canonical **`FittedModel`** (`.model.transmat_`/`predict`/`predict_proba`).
NHMM/GMM-NHMM expose a `.base: FittedModel` (per the explore) — supporting them is a thin
follow-up (their transitions are time-varying, so a static `transmat_` is an
approximation/aggregate). Out of scope for v1; the functions accept a `FittedModel` and
raise a clear `ValueError`/`TypeError` if handed an object without `model.transmat_`.

### 3.4 Writing files (optional convenience)

The functions return **dicts** (composable, testable). A thin `save_model_graph(fitted,
out_dir, *, name=None)` writing `model-graph.json` (and, given X, `model-activations.json`)
via `json.dump(..., indent=2)` is a small convenience mirroring `io.save_model`; include
it so the gitnexus source-dir contract (`<source>/model-graph.json`) is one call. Keep the
dict-returning functions as the tested core.

## 4. Verification

- **pytest** (`tests/test_export_graph.py`), mirroring `test_io_model.py` + the
  `conftest.py` fixtures:
  - `export_model_graph` on `synthetic_gaussian_left_right` (K=3 left-right): 3 state
    nodes, all `type=='state'`; transition edges only where `A>0` (left-right ⇒ no
    backward edges), weights in (0,1], `framework=='hmm'`; **no** observation/emission
    nodes (continuous).
  - `export_model_graph` on a **multinomial** fixture (or a small fit): observation nodes
    = n_symbols, emission edges present with weights in (0,1].
  - `export_activations`: state-occupancy dict keyed by state_names, values sum ≈ 1.0;
    transition-count dict keyed `${from}->transition->${to}` with int counts > 0; counts
    total = T-1 (single sequence).
  - The emitted dicts are JSON-serializable (`json.dumps` round-trips).
  - Bad input (object without `.model.transmat_`) → clear error.
- Run: `python -m pytest tests/test_export_graph.py -v` (uses the repo `.venv`, which has
  numpy + hmmlearn).
- `gitnexus_detect_changes()` (per this repo's CLAUDE.md) could not be run in this env
  (needs the indexed gitnexus stack); the change is a **new isolated module** + two
  additive `__init__` exports + a new test — scope is self-evidently additive (flagged in
  the commit/summary, not silently skipped).

## 5. Scope boundaries

**In scope**: `export_model_graph` + `export_activations` (+ a thin `save_model_graph`
file-writer) for the canonical `FittedModel`, exported from `__init__`, with pytest.

**Out of scope (deferred)**:
- **NHMM / GMM-NHMM / factorial** export (time-varying transitions — need an
  aggregate/time-sliced representation decision).
- **Continuous-emission observation nodes** (gaussian/gmm/poisson) — no discrete symbol;
  a "distribution node per state" representation is a later idea. v1 = states+transitions
  for continuous.
- **Round-trip / import back into hmm_studio** — this is export-only.
- **CLI / web-UI button** to export — the functions + file-writer are the surface; wiring
  a CLI flag is a thin follow-up.

## 6. Open questions

- **Activation node keys = state_names vs `state_i`.** Using `state_names` keeps the
  activations keyed identically to the model-graph node ids (so gitnexus matches them) —
  chosen. If a topology had non-gitnexus-safe state names, the importer/id-safety is
  gitnexus's concern; hmm_studio emits the names as-is.
- **Version source.** `hmm_core.__version__` if defined; else `None`. Confirm the attr
  exists at build time; fall back gracefully.
