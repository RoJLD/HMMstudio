# Changelog

All notable changes to `hmm-studio` are documented here. This project follows
[Semantic Versioning](https://semver.org/) and the
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.

## [Unreleased]

### Added

- Parameter help: a `?` next to each parameter on the Topology editor, Fit, and
  Compare pages opens a popover explaining it, with a "Learn more →" deep link to
  the relevant Academy lesson. Backed by a single `paramHelp` content registry.

### Added — model-variant selection (Phase 1: Python core)

- Web UI **Compare** page (`/compare`): fit a comparable emission × K grid
  (Gaussian / GMM / Poisson) on the current dataset and rank candidates by
  BIC / AIC / HQIC, reusing the K-scan parent/child engine. Backed by
  `POST /api/fit/compare/start` + `GET /api/fit/compare/{id}`. NHMM/Factorial
  remain Python-API / `hmm-fit compare` only.
- New `hmm_core.selection` module (exported at package top level):
  - `compare_models(X, candidates, *, lengths=None, seed=42) -> ModelComparison`
    — fits each candidate HMM spec on the same `X` and ranks the comparable
    ones by BIC / AIC / HQIC. Robust: a candidate whose fit raises is captured
    with an `error` and NaN metrics, never fatal to the comparison.
  - Candidate types: `TopologyCandidate` (comparable, models P(X)),
    `NHMMCandidate` and `FactorialCandidate` (flagged `comparable=False` —
    they model P(X|Z) / a joint product space, so they appear in the table
    but are never chosen as "best by criterion").
  - `auto_grid(base_topology, k_range, emission_types, n_mix=2)` — generates
    the comparable emission × K grid.
  - `ModelComparison` with `.ranked(criterion)`, `.to_summary_dict()`, and a
    Jupyter `_repr_html_` (non-comparable rows greyed + ⚠).
- `hmm-fit compare <spec_dir> <data.csv> [--criterion bic|aic|hqic]` — fit several
  candidate topologies on the same data and print a ranked BIC/AIC/HQIC table.
  Candidates come from a directory of topology YAMLs or an optional `grid.yaml`
  (`base`, `k_range`, `emission_types`, `n_mix`). NHMM/Factorial remain Python-API only.
- Phase 1 of `docs/specs/2026-05-27-model-variant-selection.md`. CLI
  (`hmm-fit compare`) and the `/compare` web page are Phases 2-3.
- The in-scope, HMM-only slice of the Nathan/Robin ModelFinder.

### Added — unsupervised feature selection

- New `hmm_core.features` module (exported at package top level):
  - `unsupervised_feature_selection(features, n_clusters=10, ...)` — clusters
    candidate feature columns by normalised mutual information (NMI) and keeps
    one representative (the *medoid*) per cluster, returning a decorrelated
    strict subset of the input columns ready to feed `fit()`. Pipeline:
    `StandardScaler` + jitter → diagonal-MI entropy → pairwise NMI
    (`sklearn.feature_selection.mutual_info_regression`, the Kraskov et al.
    2004 k-NN estimator) → `1 - NMI` distance → scipy agglomerative
    hierarchical clustering → medoid per cluster. **Zero new dependencies**
    (sklearn + scipy already present).
  - `FeatureSelectionResult` frozen dataclass — bundles the selected subset
    with the full p×p NMI matrix (for a diagnostic heatmap), the cluster
    membership dict, and the medoid-per-cluster mapping.
  - Answers the "which features should the HMM see?" question that sits just
    before the fit — collapses correlated/redundant indicator panels (e.g.
    30-40 on-chain crypto columns) into a decorrelated set. Ported from the
    Robin crypto research `cmex_crypto/features/unsupervised_selection.py`.
- New prep op **`select_features_unsupervised`** — thin recipe-friendly
  `df -> df` wrapper that returns only the selected columns (the rich NMI
  metadata is available by calling the function directly). Usable from YAML
  recipes, e.g. `- op: select_features_unsupervised` / `n_clusters: 8`.
- 10 tests in `tests/test_features.py` (subset/exact-count, correlated
  collapse, independent-all-kept, NMI matrix shape/diag/symmetry, medoid
  centrality, validation errors, prep-op standalone + in-Pipeline,
  reproducibility under a fixed seed).
- Scope (per spec `docs/specs/2026-05-27-unsupervised-feature-selection.md`):
  unsupervised only. Supervised mRMR (target-aware), the `dcor`
  distance-correlation variant, PCA, and NHMM-covariate causality selection
  are explicitly out of scope / deferred.
- Academy lesson 13 "Choosing features for your HMM" — concept + code lesson
  (no D3 demo, no notebook) covering the redundant-features problem, NMI
  clustering + medoid selection, the function API and the
  `select_features_unsupervised` prep op, and when to use it vs a curated
  feature set. Academy now has 13 lessons.

### Added — HQIC model-selection criterion

- `FittedModel` now carries `hqic` (Hannan-Quinn Information Criterion,
  `-2·LL + 2·k·ln(ln n)`) and `n_obs` (training-sequence length) alongside
  the existing `bic` / `aic`. HQIC's penalty grows slower than BIC
  (`ln ln n` vs `ln n`) but faster than AIC — it's the criterion several
  HMM-in-finance papers prefer for regime-count selection on long series
  where BIC over-penalises. Surfaced in `to_summary_dict()`,
  `to_summary_json()`, the `_repr_html_` stats table, and `summary.json`
  on disk.
- K-scan exposes `best_k_by_hqic` next to `best_k_by_bic` / `_aic`. The
  Scan page shows an HQIC column and a "Best by HQIC: K=…" badge.
  (Surfaced from the Nathan/Robin crypto research `ModelFinder` — the
  in-scope, HMM-only slice of their model-selection tooling.)

### Added — Giudici 2020 regime preset + state labelling

- `examples/giudici_2020_btc_regimes.yaml` : the canonical 3-state
  Gaussian HMM (diagonal covariance, single log-return feature) from
  Giudici & Abu Hashish (2020), "A hidden Markov model to detect regime
  changes in cryptoasset markets". A published-paper preset, loadable in
  the topology editor / `load_topology`.
- New `hmm_core.regimes` module with two generic state-labelling helpers
  (exported at package top level):
  - `regime_order_by_feature_mean(fitted, feature=0)` — state indices
    sorted ascending by their emission mean on a feature (works on
    Gaussian / GMM / Poisson ; raises on Multinomial where a numeric
    mean is undefined).
  - `regime_labels(fitted, ["bear", "stable", "bull"], feature=0)` —
    maps each raw EM state index to a human label, lowest-mean → first
    label. Resolves the "EM states have arbitrary order" interpretation
    problem. Ported from the Nathan/Robin crypto research `regimes/giudici.py`.
- 6 tests in `tests/test_regimes.py` (Gaussian ordering, bear/stable/bull
  labelling, Poisson, Multinomial-raises, wrong-label-count, example YAML
  loads-and-fits).

### Added — engine (`hmm_core.prep`)

- Two new prep ops:
  - **`log1p`** — apply `np.log1p` to listed (or all numeric) columns; by
    default skips columns containing any negative value so it chains
    safely after generic preprocessing.
  - **`drop_low_variance`** — drop columns that are near-constant
    (`std < threshold`) or mostly-zero (`zeros_fraction > threshold`).
    Encodes the "degenerate column" filter pattern that came up in the
    Valentin ETH port.
- New bundled recipe `valentin_eth` (5-step pipeline: 365-day rolling
  mean → dropna → drop_low_variance → log1p → zscore) ready for use via
  `Pipeline.from_recipe("valentin_eth")`.

### Added — examples + notebooks

- `examples/valentin_eth_3regime_gmm.yaml`: 3-state GMM topology (diag
  covariance, `n_mix=3`, ergodic; documents Valentin's strict left-right
  original and why it would need a frozen-startprob M-step to work
  as-is).
- `notebooks/10_valentin_eth_gmm_hmm.ipynb`: ports Valentin Laborie's
  *2025 S2* ETH lifecycle GMM-HMM end-to-end through hmm-studio idioms
  (private data: set `HMM_VALENTIN_ETH_PATH` env var to the CSV path
  before running).

### Added — tests

- `tests/test_valentin_eth_regression.py`: 6 regression tests pinning the
  log-likelihood (−636 ± 5%), BIC, PCA explained variance, EM convergence,
  prep-output shape, and phase populations. **Auto-skipped** when
  `HMM_VALENTIN_ETH_PATH` is unset (private dataset not in the repo).
- 5 new prep-op tests covering `log1p` (explicit columns, negative-skip,
  forced-on-negative) and `drop_low_variance` (default + thresholds).

### Changed — `.gitignore`

- Added `*JDD_ETH*.csv`, `*JDD_BTC*.csv`, `**/private_data/`,
  `notebooks/data/` patterns to prevent accidental commit of private
  research datasets referenced from notebooks via env vars.

### Added — post-v1.1 quality pass (Valentin ETH port debrief)

- **`FittedModel.to_summary_dict()` + `.to_summary_json()`**: single source
  of truth for the fit's reportable metrics (log-likelihood, BIC/AIC,
  n_iter_actual, converged, n_params, seed, duration, emission shape).
  Same pair of methods on `NHMMFittedModel`, `GMMNHMMFittedModel`, and
  `FactorialNHMMFittedModel` — each variant adds its own metadata
  (covariate_names, n_mix, K_per_chain / K_joint / chain_names …) on top
  of the base summary so regression tests, run logs, and CHANGELOG
  entries no longer re-derive the same dict by hand.
- **GMM kmeans init for `full` / `tied` / `spherical` covariance**:
  previously the kmeans branch in `init.py` only emitted the diag-shape
  `(K, M, D)` covars array, so declaring `emission: {type: gmm,
  covariance_type: full, …}` silently failed at fit time inside
  hmmlearn's `GMMHMM`. The branch now produces the correct shape for
  every covariance_type (`full` → `(K, M, D, D)`, `tied` → `(K, D, D)`,
  `spherical` → `(K, M)`), with SPD symmetrisation + 1e-6 ridge on the
  full case.
- **Startprob smoothing in `_do_mstep`**: every `Constrained*HMM`
  subclass now calls a shared `_smooth_startprob_(model, eps=1e-30)`
  helper after the base M-step. This adds a tiny epsilon to
  `startprob_` and renormalises, and falls back to uniform if a NaN/Inf
  appears (the pathology hit by strict left-right + `first_state` when
  a state is only visited at `t=0`). eps is small enough that the V.1
  cross-check vs vanilla hmmlearn still passes at its 1e-12 tolerance.
- **`FitSpec.freeze_startprob` and `FitSpec.freeze_transmat`**
  (defaults `False`): translate to hmmlearn's `params` string by
  removing `'s'` / `'t'` so the corresponding matrix is not re-fit in
  the M-step. The YAML loader recognises both keys under the `fit:`
  block. Users who provide a hand-crafted prior on either matrix can
  now clamp it — making Valentin's original strict-left-right pattern
  expressible without the ergodic workaround (left as a follow-up to
  update the example YAML / notebook accordingly).

### Added — tests (post-v1.1 quality pass)

- 9 new init tests in `tests/test_init_strategies.py` covering GMM
  `full` / `tied` / `spherical` / `diag` covariance shape, SPD
  validation, and end-to-end fits.
- 5 new tests in `tests/test_strict_left_right.py` asserting no NaN
  appears in fitted matrices under strict-left-right + first_state, and
  that the smoothing is invisible on ergodic / vanilla-equivalent fits.
- 9 new tests in `tests/test_freeze_params.py` covering FitSpec
  defaults, YAML round-trip, frozen-startprob / frozen-transmat
  preservation through EM, and emission updates still happening when
  both are frozen.
- 7 new tests in `tests/test_fit_dispatcher.py` for
  `to_summary_dict` / `to_summary_json` across `FittedModel`,
  `NHMMFittedModel`, `GMMNHMMFittedModel`, `FactorialNHMMFittedModel`,
  including JSON round-trip.

### Added — shared regression-test helper

- `tests/_regression_helpers.py`: factors the "load CSV → recipe → optional
  post-prep transform → fit → compare to reference" pattern out of every
  regression test. Components: `env_csv_path()` (env-var path lookup),
  `skipif_env_missing()` (module-level skip marker), `RegressionReference`
  (frozen dataclass with per-field tolerances and an iter-range special
  case), `assert_summary_matches_reference()` (numeric vs boolean vs
  string vs None handling), and `run_recipe_fit()` (end-to-end wrapper).
- `tests/test_valentin_eth_regression.py` refactored to use the helper —
  shrank from 6 ad-hoc tests + bespoke fixture (170 LOC) to 3 declarative
  tests + one reference dict (110 LOC) for equivalent coverage.
- `tests/test_regression_helpers.py`: 14 unit tests for the helper itself
  (env-var lookup, tolerance modes, error paths).

### Changed — launcher scripts

- **Docker image-SHA stale check** (replaces the host-mtime check from
  the earlier `bec5bbe` attempt): `start.ps1` / `start.bat` now ALWAYS
  run `docker compose build` (Docker layer cache makes it fast when
  nothing changed) and compare the `hmm-studio:latest` image SHA before
  and after. If the SHA changed, the running container is recreated on
  the new image. If unchanged AND container is up, just open the
  browser. This is Docker-aware — the previous host-mtime check
  compared `src/hmm_studio/server/static/` which is NOT mounted into
  the Docker container (the Dockerfile copies the built bundle in at
  image-build time), so it never actually triggered for the Docker
  launch path. Net effect: editing a `.tsx` file then clicking
  `start.bat` now reliably rebuilds the image, recreates the container,
  and serves the new UI instead of the cached one.
- **Removed global `$ErrorActionPreference = "Stop"`** from `start.ps1`
  because under Windows PowerShell it converts native-command stderr
  writes into `NativeCommandError` (e.g. `docker info` emits "WARNING:
  No swap limit support" on Linux Docker daemons → script aborts).
  Each step still checks `$LASTEXITCODE` explicitly.
- The earlier `scripts/check_frontend_stale.ps1` helper stays in the
  tree as a dev-mode tool (useful for non-Docker workflows like
  `hmm-studio` CLI from a local venv, or "should I rebuild before
  pushing ?" checks) — just no longer called by the Docker launchers.

### Added — Academy lesson ↔ notebook bubbles

- New reusable `<NotebookLink />` component (Option B from the
  lessons-to-notebooks integration design : surface a 4-button
  launcher card at the bottom of each lesson rather than embed the
  notebook in an iframe). Buttons :
  - **Launch in Binder** (zero-install cloud, ~30 s spin-up)
  - **Open in Colab** (familiar to ML researchers)
  - **View on GitHub** (read rendered notebook)
  - **Download .ipynb** (run locally with Jupyter)
- `LessonMeta` gains an optional `notebookLink: NotebookRef` field.
  `LessonPage` renders the launcher card between the lesson body and
  the "Mark as complete" / prev-next nav, so the flow is :
  *theory → demo → further reading → run the notebook*.
- 9 of the 12 lessons mapped to a companion notebook : L1 / L5 / L6
  → `01_quickstart`, L3 → `07_textbook_aima_umbrella`, L4 →
  `08_textbook_dishonest_casino`, L7 → `02_nhmm_crypto`, L8 →
  `05_gmm_nhmm_submodes`, L9 → `06_factorial_nhmm_multifactor`,
  L10 → `09_bayesian_hmm`. L2 (Markov chains), L11 (semi-supervised),
  L12 (HHMM theory-only) deliberately have no notebook companion —
  L2 is concept-only, L11 ships code snippets inline, L12 is gated
  on external signal.

### Added — 5 advanced Academy lessons (8 → 12)

Extends the Academy from 7 to 12 lessons, covering the variants
hmm-studio has shipped over the post-v1.0 wave :

- **Lesson 8 — GMM-HMM : sub-modes inside each regime** (Advanced,
  ~15 min). When a single Gaussian per state isn't enough ; 2-stage
  decomposition rationale ; pointer to notebook 05.
- **Lesson 9 — Factorial NHMM : independent regime dimensions**
  (Advanced, ~18 min). D parallel chains, K_joint = ∏K_d,
  27× parameter savings calc ; pointer to notebook 06.
- **Lesson 10 — Bayesian HMM : credible intervals on parameters**
  (Advanced, ~18 min). PyMC NUTS sampler, priors, when to reach for
  it ; pointer to notebook 09 and the `[bayesian]` extra.
- **Lesson 11 — Semi-supervised training : partial labels**
  (Intermediate, ~15 min). NaN / -1 sentinel API, E-step clamp,
  multi-sequence handling, edge cases.
- **Lesson 12 — Hierarchical HMM (theory only)** (Advanced,
  ~12 min). Concept lesson with explicit "code gated, spec only"
  banner ; references Fine-Singer-Tishby 1998 for self-study.

All five include a "Further reading" section sourcing the corresponding
Tier 3 (variant-specific) entries in
`docs/sources/academy-references.md` — Reynolds GMM tutorial + Columbia
E6870 (lesson 8) ; Ghahramani-Jordan 1997 (lesson 9) ; Damiano Stan
HMM + arXiv 2509.17806 Bayesian NHMM (lesson 10) ; Tamposis 2019 +
BMC 2021 + Springer PHMM (lesson 11) ; Fine-Singer-Tishby 1998
(lesson 12).

### Added — Academy "Further reading" + sourced bibliography

- New `docs/sources/academy-references.md`: 4-tier bibliography (~20
  canonical PDFs) covering the foundational tutorials (Rabiner, Bishop,
  Murphy, Jurafsky SLP3, Russell-Norvig AIMA), algorithm-specific
  references (Bilmes EM tutorial, MIT 6.867 / 16.410, Princeton ORF557),
  variants (Bengio-Frasconi IOHMM, Ghahramani-Jordan Factorial,
  Fine-Singer-Tishby Hierarchical, GMM-HMM via Reynolds + Columbia
  E6870 + Edinburgh ASR, semi-supervised via Tamposis et al.,
  Bayesian via Stan tutorial + arXiv), and textbook canonicals
  (Durbin et al. *Biological Sequence Analysis*, Eisner ice-cream
  spreadsheet).
- Reusable `<FurtherReading />` React component in
  `src/hmm_studio/frontend/src/components/academy/`. Renders a styled
  list of references with optional one-line notes, and links to the
  central bibliography.
- All 7 Academy lessons now end with a "Further reading" section
  citing 2-4 references each, mapped to the topic of the lesson
  (Lesson 1 cites Rabiner / AIMA / Bishop ; Lesson 5 Baum-Welch cites
  Bilmes / Rabiner §III.C / MIT 16.410 / Eisner ice-cream ; etc.).

### Fixed — browser cache on index.html

- The SPA fallback in `src/hmm_studio/server/app.py` now serves
  `index.html` with `Cache-Control: no-store, no-cache, must-revalidate,
  max-age=0` (plus `Pragma: no-cache` + `Expires: 0` for older browsers).
  Without this, browsers happily cached the entry-point HTML between
  releases, so even a rebuilt-and-recreated container kept showing the
  old UI because the cached `index.html` referenced the old asset
  hashes. Hashed assets in `/assets/` stay aggressively cacheable —
  their hash changes with content, so the browser refetches naturally.
- Launchers (`start.ps1` / `start.bat`) now append a `?_=<unix-ts>`
  query when opening the browser. Belt-and-suspenders : if the browser
  is carrying a pre-fix cached `index.html`, the new URL looks "fresh"
  and forces a refetch on the very first launch after upgrading.

---

## [1.1.0] — 2026-05-23

Distribution-surface release: `hmm-studio` becomes pip-installable and
Jupyter-/sklearn-native per [ADR-0012](docs/decisions/0012-distribution-strategy-hybrid.md).
Four new HMM variants (GMM-NHMM, Factorial NHMM, Bayesian via PyMC NUTS,
supervised path completed), a declarative data prep layer, a
local-filesystem data warehouse with editable settings, a six-layer
scientific validation suite, and a seven-lesson interactive Academy land
alongside the three Phase I distribution surfaces (Jupyter rich displays,
scikit-learn compatibility, PyMC bridge).

### Added — engine (`hmm_core`)

- **A.6 Bayesian HMM backend + I.3 PyMC bridge** (`hmm_core.backends.bayesian_backend.BayesianHMMBackend`):
  drop-in `HMMBackend` implementation using PyMC NUTS for full posterior
  inference (priors: Dirichlet on transmat/startprob, Normal on means,
  HalfNormal on sigmas; likelihood via `pytensor.scan` log-forward).
  Posterior mean drops into a `ConstrainedGaussianHMM` so `decode` /
  `predict` / `score` reuse the existing frequentist machinery. Full
  `arviz.InferenceData` is exposed on `backend.last_idata_` for credible
  intervals and posterior predictive checks. Installs via `pip install
  "hmm-studio[bayesian]"` (PyMC ≥ 6.0, arviz ≥ 1.0). Registered as
  backend `"bayesian"` via lazy import (pymc optional, the rest of
  hmm-core works without it).
- **A.7.1 supervised GMM + semi-supervised training**: closed-form per-state
  `GaussianMixture` fit closes the supervised-GMM gap (was `NotImplementedError`).
  Pass `states` with NaN (float) or `-1` (int) entries at unlabelled positions
  to trigger semi-supervised EM with E-step clamped at labelled positions.
  Initial parameters come from supervised MLE on the labelled subset.
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
- **scikit-learn-compatible API** (Phase I.2, `hmm_core.sklearn_compat.HMMClassifier`):
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

Nine runnable notebooks, each pip-only, no external data:

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
9. **Bayesian HMM (PyMC)** — full posterior inference via NUTS, credible
   intervals on transmat / means, posterior predictive checks. Requires
   the `[bayesian]` extra.

### Added — documentation

- **ADR-0007** GMM-NHMM scope.
- **ADR-0010** data warehouse scope (local-only, sidecar YAML, anti
  scope-creep guardrails).
- **ADR-0012** hybrid distribution strategy (HMM specialist + integration
  surfaces — *NOT* a generic research sandbox; Phase I = priority).
- Six new phase specs (A.10, A.13, B.10, B.11, E, V) under `docs/specs/`.
- GitHub Pages deploy workflow + contributing guide + mkdocs tweaks.

### Changed

- Repository test count: **154 → 309 default** (+155; 14 supervised /
  semi-supervised A.7.1 plus the GMM-NHMM / Factorial NHMM / prep /
  warehouse / settings / Jupyter `_repr_html_` suites and the V.1-V.6
  + V.perf validation layer). The 12 Bayesian backend tests are marked
  `slow` and require the `[bayesian]` extra; run with
  `pytest -m slow` to include them (321 total).
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
