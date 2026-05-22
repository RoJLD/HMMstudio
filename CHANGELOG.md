# Changelog

All notable changes to `hmm-studio` are documented here. This project follows
[Semantic Versioning](https://semver.org/) and the
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.

## [1.0.0] — 2026-05-22

First production release. The package now ships the full vertical stack:
a constrained-fit HMM engine (`hmm_core`) and a web UI (`hmm_studio`) for
authoring topologies, fitting, comparing K, and visualizing results.

### Added — engine (`hmm_core`)

- Four constrained emission classes wrapping `hmmlearn`: Gaussian, GMM,
  Categorical (Multinomial), Poisson. Forbidden transitions stay exactly
  zero through all EM iterations.
- `Topology` declarative YAML schema with `allowed_transitions`,
  `startprob`, init strategy, and fit hyperparameters.
- Four initialization strategies: `uniform`, `random`, `kmeans`,
  `data_frequencies` (cluster-trajectory counts).
- NHMM (non-homogeneous HMM) via two-stage EM + per-state multinomial
  logistic regression on covariates. Exposes `A_t` (T × K × K).
- Supervised training path (Phase A.7): closed-form MLE when state labels
  are observed. Mask-aware, deterministic, no EM iteration.
- Per-state `EmissionSpec` (Phase A.8): optional init hints
  (`init_mean` / `init_lambda` / `init_emissionprob`) per state. Same-type
  constraint; heterogeneous-type per state deferred.
- Dirichlet priors on transitions (Phase A.9): scalar
  `transmat_prior_alpha` or full `transmat_prior_matrix`. MAP smoothing
  in `_do_mstep` for all four emission classes.
- Multi-sequence support: `fit(X, lengths=[L1, L2, ...])` skips spurious
  cross-boundary transitions in `data_frequencies` and forwards `lengths`
  to hmmlearn.
- Backend abstraction (`HMMBackend` Protocol, ADR-0003): the rest of
  `hmm_core` is decoupled from hmmlearn; alternative backends
  (pomegranate, dynamax, NumPy-only) can be registered.
- CLI `hmm-fit validate / run / decode / show` for direct shell use.
- File formats: YAML topology (round-trippable), pickle model bundle,
  JSON summary (with `mask_violation_norm` sanity), parquet decoded
  output.

### Added — web UI (`hmm_studio`)

- FastAPI backend with topology validation, dataset upload, fit job
  orchestration via `ThreadPoolExecutor`, SQLite persistence for job
  history.
- WebSocket `/ws/fit/{id}` streaming live log-likelihood per Baum-Welch
  iteration (polling-based, no hmmlearn patches).
- Three additional REST endpoints for visualization: `/api/fit/{id}/transmat`,
  `/decoded`, `/emissions`, plus `/A_at?t=N` for NHMM frames.
- K-scan endpoint `/api/fit/scan/start` — parent/child jobs, parallel
  Baum-Welch across `K ∈ [k_min, k_max]`, best-K picker by BIC/AIC.
- External annotations: upload CSV (`t,label[,color]`) attached to a
  dataset, displayed as overlay markers on the Viterbi timeline.
- React + Vite + TypeScript + Tailwind frontend. Five pages: Home, Data,
  Topology, Fit, Results, Scan.
- Topology editor (React Flow): drag-drop states, draw transitions,
  inline rename, undo/redo (50 steps), live validation (debounced 400ms),
  YAML import/export, URL sharing (base64), localStorage persistence.
- Per-state emission panel (B.4.2): editable `init_mean` / `init_lambda` /
  `init_emissionprob` per state when a node is selected.
- Per-edge prior panel (B.4.3): editable Dirichlet weight per transition
  when an edge is selected; visual cue (indigo + thicker stroke + label).
- Fit launcher: seed override, covariate selector (for NHMM), sequence
  boundaries (for multi-sequence), K-scan mode toggle.
- Results view: transition matrix heatmap (forbidden edges in gray with
  `×`), Viterbi colored timeline with cursor and annotations overlay,
  emissions panel, live convergence curve, NHMM A(t) animated heatmap
  with timeline player synchronization.
- Timeline player (C.2): play / pause / step / scrub / 4 speeds, drives
  the Viterbi cursor and the NHMM A(t) frame in lock-step.
- SVG export buttons on all visualizations (transmat, Viterbi, A(t),
  BIC scatter, progress curve). Pure browser-native SVG download — no
  Python or third-party rendering dependency.
- Dark mode (light / dark / system, persisted in localStorage).

### Added — packaging and infrastructure

- Docker multi-stage image (Node 20 builds React, Python 3.12 runs
  FastAPI + serves static).
- `docker-compose.yml` with named volume for SQLite + uploads + results.
- Rancher Desktop launcher scripts (`start.ps1` / `start.bat` /
  `stop.ps1` / `stop.bat`) — one-click run, auto-starts Rancher if
  needed, opens browser when healthy.
- GitHub Actions CI workflow (matrix Python 3.11 / 3.12 / 3.13: pytest +
  ruff + black).
- mkdocs-material documentation site with nav for roadmap, sub-project
  specs, and ADRs.
- MIT LICENSE, CITATION.cff.

### Documentation

- 6 ADRs (`docs/decisions/0001`–`0006`) capturing every cross-cutting
  decision: backend choice, B stack, backend abstraction, supervised
  training scope, per-state emission scope, Dirichlet prior scope.
- 3 sub-project specs (A, B, C) under `docs/specs/`.
- 4 implementation plans archived under `docs/plans/`.

### Tests

- 154 tests, ≥85% coverage on `src/hmm_core/`.

---

## [0.2.0] — 2026-05-22 (development)

- Phase A.1: NHMM (`fit_nhmm` + `NHMMFittedModel`) ported from the
  existing crypto-dashboard prototype into `hmm_core`.
- Phase A.next polish: GMM tied `n_params` correctness, `lengths`
  parameter, coverage gaps closed (74% → 92% on `init.py`).
- Z.1: GitHub Actions CI + pre-commit config.
- Phase D: regression test confirming the crypto dashboard's `fit_hmm`
  remains numerically identical to `hmm_core.fit` on the same data
  (drift = 6×10⁻⁶ %). Dashboard internals later swapped to delegate to
  `hmm_core`.

## [0.1.0] — 2026-05-21

- Initial release of `hmm-core` engine + `hmm-fit` CLI.
