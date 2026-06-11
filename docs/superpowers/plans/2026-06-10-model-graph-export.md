# Model-graph export — Implementation Plan

> REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Spec: `docs/superpowers/specs/2026-06-10-model-graph-export-design.md`.

**Goal:** `hmm_core.export_graph` with `export_model_graph(fitted,*,name=None) -> dict`, `export_activations(fitted,X,*,name=None,lengths=None) -> dict`, and a thin `save_model_graph(fitted,out_dir,*,name=None,X=None)` file-writer. Exported from `hmm_core/__init__`. pytest.

**Verification:** from the worktree, `PYTHONPATH=<worktree>/src <main-repo>/.venv/Scripts/python.exe -m pytest tests/test_export_graph.py -v` (the main `.venv` has numpy+hmmlearn; the worktree has no venv of its own).

### Task 1: `export_graph.py` + `__init__` exports + tests
**Files:** create `src/hmm_core/export_graph.py`; modify `src/hmm_core/__init__.py` (add the 3 names to imports + `__all__`); create `tests/test_export_graph.py`.

- [ ] **Step 1: test first** `tests/test_export_graph.py` — mirror `tests/test_io_model.py` + reuse `conftest.py` fixtures (`synthetic_gaussian_left_right`, a multinomial fixture if one exists else build a tiny multinomial topology+fit). Cases per spec §4: gaussian → 3 state nodes, transition edges only where A>0, weights∈(0,1], framework=='hmm', no observation nodes; multinomial → observation nodes = n_symbols + emission edges; activations → occupancy dict (sum≈1) + transition-count dict keyed `${from}->transition->${to}` (int>0, total=T-1); JSON-serializable; bad input → error.
- [ ] **Step 2: run, verify FAIL** (module missing).
- [ ] **Step 3: implement** `export_graph.py` per spec §3.1/§3.2/§3.4. Read `fitted.model.transmat_`, `fitted.topology.{n_states,state_names,emission}`; `EPS=1e-9`; multinomial uses `fitted.model.emissionprob_` + `fitted.topology.emission.n_symbols`; activations use `fitted.model.predict_proba(X)`/`predict(X)` (pass `lengths` through if given, and don't count cross-sequence transitions); version from `getattr(hmm_core,'__version__',None)`. Guard non-FittedModel / missing `transmat_` with a clear error.
- [ ] **Step 4: run, verify PASS.** Add the exports to `__init__`.
- [ ] **Step 5:** report (controller runs the authoritative pytest + commits).

### Post-build (controller)
1. Run pytest in the worktree (venv+PYTHONPATH as above) — green.
2. Commit on `feat/model-graph-export` (GitHub identity, Co-Authored-By trailer) + push; note `gitnexus_detect_changes` not run (env) but change is additive/isolated. Update roadmap/INVENTORY if present.
3. Remove the worktree after push.
