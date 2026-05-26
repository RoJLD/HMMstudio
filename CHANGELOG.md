# Changelog

All notable changes to `hmm-studio` are documented here. This project follows
[Semantic Versioning](https://semver.org/) and the
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.

## [Unreleased]

Distribution-surface release: `hmm-studio` becomes pip-installable and
Jupyter-/sklearn-native per [ADR-0012](docs/decisions/0012-distribution-strategy-hybrid.md).
Three new HMM variants (GMM-NHMM, Factorial NHMM, supervised path completed),
a declarative data prep layer, a local-filesystem data warehouse with
editable settings, a six-layer scientific validation suite, and a
seven-lesson interactive Academy land alongside the Phase I distribution
surfaces.

### Added — engine (`hmm_core`)

- **GMM-NHMM** (Phase A.10, `fit_gmm_nhmm`): GMM emissions with
  covariate-dependent transitions via a 2-stage decomposition (GMM-HMM
  base + per-state logistic regression on the Viterbi-derived
  `(Z_t, z_{t+1})` pairs). Joint-state expansion (`K·M`) rejected at
  implementation time as over-parameterised without the factorisation
  constraint — see [ADR-0007](docs/decisions/0007-gmm-nhmm-scope.md).
- **Factorial NHMM** (Phase A.13, `fit_factorial_nhmm`): D parallel chains
  with per-chain covariates, via 2-stage decomposition over the joint
  product space (`K_joint = ∏K_d`, hard cap at 27). Exposes
  `decode_chain` and `A_t` per chain. Demonstrates 27× parameter savings
  vs the joint HMM at D=3, K=3.
- **Data prep layer** (Phase B.11, `hmm_core.prep`): declarative `Pipeline`
  builder + 21 atomic ops + 8 bundled YAML recipes (general purpose and
  HMM-flavoured: financial log returns, regime features, etc.). Recursive
  composition via YAML `includes:`, provenance sidecar written on
  `fit_transform`. `Pipeline.from_recipe(name)` for one-liner use.
- **Jupyter rich displays** (Phase I.1): `_repr_html_` on `Topology`,
  `FittedModel`, `NHMMFittedModel`, `GMMNHMMFittedModel`,
  `FactorialNHMMFittedModel`, `Pipeline`, `PreparedResult`. Pure HTML +
  inline CSS, zero JavaScript — renders in JupyterLab, VS Code,
  Colab, Hex, Deepnote without any extension installed. Shared helpers
  for matrix heatmaps, sequence strips, chip lists in `hmm_core._jupyter`.
- **scikit-learn-compatible API** (Phase I.2, `hmm_core.sklearn.HMMClassifier`):
  `BaseEstimator` + `ClassifierMixin`. Passes the official
  `sklearn.utils.estimator_checks.check_estimator` battery. Drops into
  `Pipeline`, `cross_val_score`, `GridSearchCV` without ceremony.

### Added — web UI / studio

- **Data warehouse** (Phase B.10): point the studio at a host directory
  via `HMM_STUDIO_WAREHOUSE_PATH` (or the Settings page); browse CSV /
  Parquet / JSON / JSONL / Excel / Feather / TSV files in the new
  `WarehouseSidebar` with format badges, preview, and per-dataset
  `.hmm.yaml` sidecar metadata editor. Backend exposes six REST
  endpoints (`list / refresh / preview / get-meta / put-meta / upload`)
  plus a `promote` endpoint that loads a warehouse file into the studio's
  Dataset table for the fit pipeline. Path-traversal blocked at
  `safe_resolve`. Scope discipline documented in
  [ADR-0010](docs/decisions/0010-data-warehouse-scope.md).
- **Settings page** (`/settings`): editable `warehouse_path` with DB
  override > env var > unset precedence, applied per request (no server
  restart needed). `SettingsRow` singleton table; cache invalidated on
  update.
- **Phase E Academy**: 7 interactive lessons (What is an HMM? — Markov
  chains — Forward algorithm — Viterbi — Baum-Welch — Constrained
  topologies — NHMM) with embedded D3 demos, "Try in editor" handoff to
  the topology editor, and progress persistence (`mark complete`,
  localStorage).
- **Frontend bundle split**: manual chunks for `react-vendor` /
  `reactflow` / `d3` / `state` / `yaml` / `app`. Reduces initial parse
  cost and lets browsers cache vendor code independently.

### Added — CLI / packaging

- `hmm-fit batch <dir>` — parallel fits across a directory of
  `(topology.yaml, data.csv)` pairs. Reports BIC / AIC / log-likelihood
  in a Rich table at the end.

### Added — validation suite (`validation/`)

Six-layer scientific validation, run separately from the unit tests:

- **V.1** — cross-check against vanilla `hmmlearn` (4 tests, ensures
  the constrained subclasses match the upstream baseline on
  unconstrained inputs).
- **V.2** — statistical recovery on synthetic data with Hungarian
  matching for state-label permutation (5 tests).
- **V.3** — textbook canonicals: Russell & Norvig umbrella world (AIMA
  Sec. 14.2 filtering + smoothing), Durbin et al. dishonest casino
  (Viterbi accuracy ≥ 70%), Jurafsky / Eisner ice cream (6 tests total).
- **V.4** — numerical stability stress (degenerate covariances,
  near-singular transmat rows, log-domain accumulators) (5 tests).
- **V.5** — A.10 GMM-NHMM cross-check vs independent oracles (5 tests).
- **V.6** — A.13 Factorial NHMM cross-check + the 27× parameter-savings
  proof (5 tests).
- **V.perf** — performance regression suite: 4 K-scales × Gaussian /
  NHMM / Dirichlet-prior overhead (asserts upper bound on per-iteration
  time to catch accidental quadratic regressions).

### Added — E2E (`e2e/`, Playwright)

- Golden-path test: upload → topology → fit → inspect transmat → decode.
- Topology editor: undo, export YAML, import YAML, validation flow.
- Academy: index page render, lesson rendering, "Try in editor" bridge,
  mark-complete persistence.
- Accessibility: `axe-core` audit on the main pages (warn-by-default,
  `STRICT_A11Y=1` to fail).
- Warehouse: sidebar listing, dataset preview, sidecar edit roundtrip
  (with revert), use-for-fit promotion (fixture warehouse dir +
  `HMM_STUDIO_WAREHOUSE_PATH` wired in the CI workflow).
- Tour recording (Playwright video) + ffmpeg conversion guide.

### Added — notebook gallery (`notebooks/`)

Eight runnable notebooks, each pip-only, no external data:

1. **Quickstart** — 30-second tour (declare topology, fit, decode,
   left-right constrained variant).
2. **NHMM for crypto regimes** — covariate-driven transitions, `A_at`
   inspection.
3. **Data prep recipes** — bundled recipes, Python builder, sidecar.
4. **sklearn pipeline integration** — `HMMClassifier` in `Pipeline`,
   `GridSearchCV`, `cross_val_score`.
5. **GMM-NHMM sub-modes** — 2 regimes × 2 sub-modes, BIC vs single
   Gaussian.
6. **Factorial NHMM multi-factor** — trend × vol, per-chain covariates,
   parameter savings.
7. **Textbook AIMA umbrella** — reproduce Russell & Norvig Chap. 14
   filtering + smoothing within 5×10⁻³ of the published values.
8. **Textbook Durbin dishonest casino** — Viterbi accuracy assertion
   on a sampled T=1000 sequence (≥ 70%, above the always-fair baseline).

### Added — documentation

- **ADR-0007** GMM-NHMM scope.
- **ADR-0010** data warehouse scope (local-only, sidecar YAML, anti
  scope-creep guardrails).
- **ADR-0012** hybrid distribution strategy (HMM specialist + integration
  surfaces — *NOT* a generic research sandbox; Phase I = priority).
- Six new phase specs (A.10, A.13, B.10, B.11, E, V) under `docs/specs/`.
- GitHub Pages deploy workflow + contributing guide + mkdocs tweaks.

### Changed

- Repository test count: **154 → 283** (+129 unit tests; +36 validation
  tests across V.1–V.6 + V.perf; +17 Jupyter `_repr_html_` tests; +15
  warehouse tests; +7 settings tests; +5 E2E specs).
- Studio frontend now ships split chunks (lazy-loaded React Flow / d3 /
  state / yaml / vendor) instead of one monolithic bundle.
- `_store_dataframe_as_dataset()` helper factored out of
  `/api/data/upload` and reused by `POST /api/warehouse/{rel_path}/promote`
  so the warehouse-to-fit handoff shares the upload path.
- Replaced all `datetime.utcnow()` calls (16 sites) with a shared
  `hmm_studio.server._time.utcnow()` helper, removing 94 Python 3.13
  `DeprecationWarning` lines from the test output.
- `test_endpoints.py` and `test_warehouse.py` fixtures now use
  `with TestClient(app) as c: yield c` so FastAPI lifespan teardown
  shuts down each test's `JobRunner.ThreadPoolExecutor`, preventing
  thread leaks across the test suite.

### Tests

- 283 unit tests pass (≥ 37s clean run).
- 36 validation tests + V.perf regression suite.
- 5 Playwright specs covering golden path, topology editor, academy,
  accessibility, warehouse.

---

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
