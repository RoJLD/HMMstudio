# hmm-studio

[![CI](https://github.com/RoJLD/HMMstudio/actions/workflows/ci.yml/badge.svg)](https://github.com/RoJLD/HMMstudio/actions/workflows/ci.yml)
[![docs](https://github.com/RoJLD/HMMstudio/actions/workflows/docs.yml/badge.svg)](https://rojld.github.io/HMMstudio/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

`hmm-studio` is the deepest HMM library in the Python scientific stack —
**pip-installable, sklearn-compatible, Jupyter-native**, with an optional
standalone GUI for non-Python users. We don't replace your research
environment; we slot in as the HMM specialist.

Under the hood it ships two integrated layers: `hmm_core`, a domain-agnostic
constrained Baum-Welch engine with Jupyter rich displays and a scikit-learn
estimator surface, and `hmm_studio`, an optional FastAPI + React studio for
drawing topologies, browsing a local data warehouse, and inspecting fits
from a browser.

See [ADR-0012 — distribution strategy](docs/decisions/0012-distribution-strategy-hybrid.md)
for the positioning rationale.

## Why constrained HMMs?

Standard HMM libraries (hmmlearn, pomegranate) fit ergodic models: every
transition edge is free. Real applications often need **structural priors** —
Bakis left-right speech models, lifecycle models with forbidden
back-transitions, branching regime topologies. `hmm-studio` lets you declare
which transitions are allowed and runs constrained Baum-Welch that respects
those zeros at every M-step. Dirichlet priors, per-state emission hints,
non-homogeneous HMMs (NHMM), and supervised training are all first-class.

## Install

### pip (engine + CLI only)

```bash
pip install hmm-studio
hmm-fit --help
```

### pip (full stack: engine + web UI)

```bash
pip install "hmm-studio[web]"
python scripts/build_frontend.py   # builds React assets once
hmm-studio                         # opens http://127.0.0.1:8000
```

### Docker / Rancher Desktop (recommended for the UI)

```powershell
.\start.ps1      # Windows (also works: start.bat)
```

Builds the multi-stage image (Node 20 → React build; Python 3.12 → FastAPI),
starts the container with a named volume (SQLite DB + uploads + results survive
restarts), waits for `/health`, and opens the browser automatically.

```powershell
.\stop.ps1                # graceful stop
docker compose down       # full teardown (volume kept)
docker compose down -v    # wipe volume (clears DB, uploads, results)
```

**Desktop shortcut**: right-click `start.bat` → "Send to" → "Desktop (create
shortcut)". Rename to "hmm-studio".

## Quickstart in Jupyter (recommended)

`hmm-studio` is **Jupyter-native** : every object renders as a rich HTML view
inline (heatmaps, statistics tables, sequence strips). The fastest way to
get started :

```python
from hmm_core.topology import Topology, EmissionSpec, FitSpec, InitSpec
from hmm_core.fit import fit
import numpy as np

# 1. Build a topology (renders inline as HTML in Jupyter)
topo = Topology(
    name="quickstart",
    n_states=3,
    state_names=["low", "mid", "high"],
    emission=EmissionSpec(type="gaussian", covariance_type="diag", n_features=1),
    allowed_transitions=None,                   # ergodic
    startprob="uniform",
    init=InitSpec(strategy="kmeans", seed=42),
    fit=FitSpec(algorithm="baum_welch", n_iter=100, tol=1e-4),
)
topo                                            # rich HTML view

# 2. Fit on data (FittedModel renders heatmap + stats)
X = np.random.default_rng(42).normal(size=(200, 1))
result = fit(topo, X, seed=42)
result                                          # rich HTML view

# 3. Decode
viterbi_states = result.model.predict(X)
```

See the [notebook gallery](notebooks/) for 8 runnable examples covering
the full feature set : quickstart, NHMM regime detection, data preprocessing
recipes, sklearn pipeline integration, GMM-NHMM sub-modes, Factorial NHMM
multi-factor, and the canonical textbook problems (AIMA umbrella, Durbin
dishonest casino).

## Academy : zero-install learning

The notebook gallery doubles as the hmm-studio **Academy** — a structured
learning path from "what is a hidden state" to advanced multi-factor regime
modeling. One-click run via Binder, no environment setup needed :

[![Open in Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/RoJLD/HMMstudio/main?urlpath=lab/tree/notebooks)

The Binder badge launches the entire gallery in a hosted JupyterLab — ~30
seconds to first cell. The 8 notebooks include rich HTML rendering of every
hmm-studio object (heatmaps, statistics tables, sequence strips) and reproduce
canonical textbook problems (Russell & Norvig AIMA Chap. 14, Durbin et al.
*Biological Sequence Analysis* Chap. 3) to demonstrate that the math is right.

See [notebooks/README.md](notebooks/) for the full index and suggested
learning path.

## Drop-in with scikit-learn

`HMMClassifier` slots into any existing `sklearn` workflow — `Pipeline`,
`GridSearchCV`, `cross_val_score`, `clone`, `joblib.dump`. Same fit /
predict / score contract as `RandomForestClassifier` etc.

```python
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GridSearchCV
from hmm_core.sklearn_compat import HMMClassifier

pipe = Pipeline([
    ("scaler", StandardScaler()),
    ("hmm", HMMClassifier(n_states=3, emission_type="gaussian")),
])

# Grid search over K + init strategy
search = GridSearchCV(
    HMMClassifier(),
    param_grid={"n_states": [2, 3, 4], "init_strategy": ["kmeans", "random"]},
    cv=3, scoring="accuracy",
)
search.fit(X, y)
print(search.best_params_)
```

Full walkthrough in [notebooks/04_sklearn_pipeline.ipynb](notebooks/04_sklearn_pipeline.ipynb).

## Notebook gallery

Eight runnable notebooks, pip-only, no external data. Each one renders
`hmm-studio` objects inline as rich HTML (heatmaps, statistics tables,
sequence strips).

| # | Notebook | Topic |
|---|---|---|
| 01 | [Quickstart](notebooks/01_quickstart.ipynb) | 30-second tour : declare topology, fit, decode. Includes left-right constrained example. |
| 02 | [NHMM for crypto regimes](notebooks/02_nhmm_crypto.ipynb) | Covariate-dependent transitions, A_t inspection, decoded path accuracy. |
| 03 | [Data prep recipes](notebooks/03_data_prep_recipes.ipynb) | Bundled recipes, Python pipeline builder, provenance sidecar. |
| 04 | [sklearn pipeline integration](notebooks/04_sklearn_pipeline.ipynb) | Drop-in `HMMClassifier` in sklearn `Pipeline`, `GridSearchCV`, `cross_val_score`. |
| 05 | [GMM-NHMM sub-modes](notebooks/05_gmm_nhmm_submodes.ipynb) | Multi-modal regimes : each state hosts a Gaussian mixture, transitions modulated by covariates. |
| 06 | [Factorial NHMM multi-factor](notebooks/06_factorial_nhmm_multifactor.ipynb) | Independent regime dimensions (trend × vol), per-chain covariates, parameter savings vs joint HMM. |
| 07 | [Textbook : AIMA umbrella world](notebooks/07_textbook_aima_umbrella.ipynb) | Reproduce Russell & Norvig Chap. 14 smoothing + filtering values on the canonical 5-step sequence. |
| 08 | [Textbook : Durbin dishonest casino](notebooks/08_textbook_dishonest_casino.ipynb) | Reproduce the Viterbi recovery accuracy from Durbin et al. *Biological Sequence Analysis* Chap. 3. |

See [notebooks/README.md](notebooks/README.md) for the gallery philosophy
and hosted-environment notes (Colab / Hex / Deepnote).

## 30-second tour

### CLI

```bash
# Validate a topology YAML.
hmm-fit validate examples/topology_left_right.yaml

# Fit with constraints (left-right, forbidden back-edges).
hmm-fit run examples/topology_left_right.yaml examples/data_gaussian.csv \
    --output results/demo

# Inspect — forbidden edges print as `x` instead of probabilities.
hmm-fit show results/demo/model.pkl

# Decode new data.
hmm-fit decode results/demo/model.pkl examples/data_gaussian.csv \
    --output results/demo/decoded.parquet
```

### Web UI

After `hmm-studio` (or `.\start.ps1`):

1. **Data** — upload a CSV, optionally attach an annotation file
   (`t,label[,color]`).
2. **Topology** — drag-drop states onto the canvas, draw transitions, set
   emission type, init strategy, and fit hyperparameters. Import/export YAML.
3. **Fit** — launch a fit job (seed, covariate, sequence lengths). Watch the
   live convergence curve over WebSocket.
4. **Results** — transition matrix heatmap (forbidden edges grayed with `×`),
   Viterbi timeline with annotation overlay, emissions panel, NHMM A(t)
   animated heatmap with a synchronized timeline player.
5. **Scan** — run K-scan (`K ∈ [k_min, k_max]`), compare BIC/AIC, pick best
   model order.

## Advanced HMM variants

Beyond the constrained Gaussian / multinomial / Poisson HMMs above,
`hmm_core` ships three variants for harder regime-modeling problems.

### GMM-NHMM — multi-modal regimes

When a single regime hides multiple sub-modes (a "bear" state with both a
grinding-decline mode and a panic-crash mode, etc.), a Gaussian-mixture
emission captures the within-regime heterogeneity while the NHMM logits
let exogenous covariates drive transitions between regimes.

```python
from hmm_core.topology import Topology, EmissionSpec, FitSpec, InitSpec
from hmm_core.gmm_nhmm import fit_gmm_nhmm

topo = Topology(
    name="gmm_nhmm_demo",
    n_states=2, state_names=["bear", "bull"],
    emission=EmissionSpec(type="gmm", n_features=1, n_mix=2, covariance_type="diag"),
    allowed_transitions=None, startprob="uniform",
    init=InitSpec(strategy="kmeans", seed=42),
    fit=FitSpec(algorithm="baum_welch", n_iter=100, tol=1e-4),
)
result = fit_gmm_nhmm(topo, X, Z, covariate_names=["vol", "macro"], seed=42)
result                                # rich HTML : per-regime sub-modes + A_t
print(result.A_at(t_idx=100))         # K x K transition matrix at t=100
```

Full walkthrough : [notebooks/05_gmm_nhmm_submodes.ipynb](notebooks/05_gmm_nhmm_submodes.ipynb).
See also [docs/guides/gmm-nhmm.md](docs/guides/gmm-nhmm.md) for the user guide.

### Factorial NHMM — multi-factor regimes

When the system's "state" is the cross-product of several **independent**
regime dimensions (trend × volatility × macro), a Factorial NHMM
parameterizes each chain separately. Per-chain transitions are driven by
chain-specific covariates, and the joint state is recovered by
`np.unravel_index`. Parameter cost drops from `K_joint²` to
`Σ_d K_d²` — 27× savings at `D=3, K=3`.

```python
from hmm_core.topology import EmissionSpec
from hmm_core.factorial_nhmm import FactorialChainSpec, fit_factorial_nhmm

chains = [
    FactorialChainSpec(name="trend", n_states=3),
    FactorialChainSpec(name="vol",   n_states=2),
]
result = fit_factorial_nhmm(
    chains, X,
    covariates_per_chain={"trend": Z_macro, "vol": Z_realized_vol},
    emission=EmissionSpec(type="gaussian", n_features=2, covariance_type="diag"),
    seed=42,
)
result                                          # rich HTML : per-chain heatmaps
trend_path = result.decode_chain(X, "trend")    # (T,) in [0, 3)
A_t_vol = result.A_t("vol")                     # (T, 2, 2)
```

Full walkthrough : [notebooks/06_factorial_nhmm_multifactor.ipynb](notebooks/06_factorial_nhmm_multifactor.ipynb).
See also [docs/guides/factorial-nhmm.md](docs/guides/factorial-nhmm.md) for the user guide.

### Supervised training

When you have ground-truth state annotations on a held-out segment, pass
them with `state_labels=` to skip Baum-Welch entirely and use closed-form
MLE for emissions and transitions. Useful for calibration on labeled
sub-sequences before decoding the unlabeled rest.

```python
result = fit(topo, X, state_labels=y)      # y shape (T,), int in [0, K)
```

## Data prep layer

Most HMM tutorials skip data preparation (log-returns, rolling features,
forward-fill, train/test alignment) — yet that's where most real-world
projects die. `hmm_core.prep` ships a declarative `Pipeline` builder, 21
atomic pandas-thin ops, and **8 bundled YAML recipes** (4 general:
normalize / forward-fill / winsorize / resample; 4 HMM-canonical:
financial log returns, volatility features, crypto basic prep, train-ready
features).

```python
from hmm_core.prep import Pipeline
import pandas as pd

df = pd.read_csv("close_prices.csv")

# One-liner with a bundled recipe
pipe = Pipeline.from_recipe("financial_log_returns")
prepared = pipe.fit_transform(df)
prepared                              # rich HTML : steps + preview
X = prepared.observations             # ready for fit()
```

Every `fit_transform` writes a **provenance sidecar** alongside the
output — the exact compiled step list with resolved parameters — so
preprocessing is reproducible and auditable.

Python escape hatch:

```python
pipe = Pipeline()
pipe.add_step("log_diff", column="close", new_name="log_return")
pipe.add_step("rolling_std", column="log_return", window=20)
pipe.add_step("zscore", columns=["log_return", "rolling_std_20"])
prepared = pipe.fit_transform(df)
```

Full walkthrough : [notebooks/03_data_prep_recipes.ipynb](notebooks/03_data_prep_recipes.ipynb).

## Features

### Engine (`hmm_core`)

| Feature | Detail |
|---|---|
| Emission types | Gaussian, GMM, Categorical (Multinomial), Poisson |
| Constraint enforcement | Binary mask applied after every M-step; forbidden edges remain exactly 0 |
| Initialization | `uniform`, `random`, `kmeans`, `data_frequencies` |
| NHMM | Two-stage EM + per-state multinomial logistic regression on covariates |
| Supervised training | Closed-form MLE from observed state labels (no EM) |
| Per-state emission hints | `init_mean`, `init_lambda`, `init_emissionprob` per state |
| Dirichlet priors | Scalar `transmat_prior_alpha` or full prior matrix; MAP M-step |
| Multi-sequence | `fit(X, lengths=[L1, L2, ...])` — cross-boundary transitions skipped |
| Backend abstraction | `HMMBackend` Protocol (ADR-0003); plug in pomegranate/dynamax |
| File formats | YAML topology, pickle model bundle, JSON summary, parquet decoded output |

### Web UI (`hmm_studio`)

- Topology editor: drag-drop, inline rename, undo/redo (50 steps), live
  validation, YAML import/export, URL sharing (base64), localStorage
  persistence.
- Per-state emission panel and per-edge Dirichlet prior panel in the editor.
- Fit launcher with seed, covariate selector, sequence-boundary input, and
  K-scan mode toggle.
- Results view: heatmap, Viterbi timeline, convergence curve, NHMM A(t)
  heatmap with timeline player (play/pause/step/scrub, 4 speeds).
- SVG export on every visualization (no server-side rendering dependency).
- Dark mode (light / dark / system, persisted in localStorage).
- **Data warehouse**: directory-based dataset browser with sidecar metadata,
  sidebar tree, format badges (CSV / Parquet / JSON / JSONL / Excel /
  Feather / TSV), preview pane, and **"Use for fit"** promotion into the
  studio's Dataset table. Configure via the `HMM_STUDIO_WAREHOUSE_PATH`
  env var or the new `/settings` page (DB override > env var > unset).
- **Academy**: 7 interactive lessons (What is an HMM? — Markov chains —
  Forward algorithm — Viterbi — Baum-Welch — Constrained topologies —
  NHMM) with embedded D3 demos, **"Try in editor"** handoff to the
  topology editor, and per-lesson progress persisted in localStorage.
- REST API documented at `http://127.0.0.1:8000/docs` (Swagger UI).

## Topology YAML schema

```yaml
name: my_model              # free-text identifier
n_states: 4                 # K
state_names: [s0, s1, s2, s3]

emission:
  type: gaussian            # gaussian | gmm | multinomial | poisson
  covariance_type: full     # gaussian/gmm: full | diag | tied | spherical
  n_features: 2             # gaussian/gmm/poisson: observation dimension
  n_mix: null               # gmm only: mixture components per state
  n_symbols: null           # multinomial only: vocabulary size

# Omit allowed_transitions => ergodic (all edges allowed).
# Listed pairs = the ONLY allowed edges; everything else is forced to 0.
allowed_transitions:
  - [s0, s0]
  - [s0, s1]
  - [s1, s1]
  - [s1, s2]
  - [s2, s2]
  - [s2, s3]
  - [s3, s3]

startprob: first_state      # "uniform" | "first_state" | [0.7, 0.1, 0.1, 0.1]

init:
  strategy: kmeans          # uniform | random | kmeans | data_frequencies
  seed: 42

fit:
  algorithm: baum_welch
  n_iter: 200
  tol: 1.0e-4
```

## Data format

| Emission type | CSV layout |
|---|---|
| `gaussian`, `gmm`, `poisson` | `n_features` numeric columns, one row per time step |
| `multinomial` | Single integer column, values in `[0, n_symbols)` |
| Annotations | `t,label[,color]` — `t` is a zero-based integer row index |

## Python API

```python
from hmm_core.fit import fit
from hmm_core.io import load_topology, save_model
import pandas as pd

topo = load_topology("topology.yaml")
X = pd.read_csv("data.csv").to_numpy()

result = fit(topo, X)
print(result.log_likelihood, result.bic, result.converged)
print(result.model.transmat_)     # respects topology.transition_mask()

save_model(result, "results/run_1")
```

Multi-sequence fit:

```python
result = fit(topo, X, lengths=[500, 500, 300])
```

NHMM fit:

```python
from hmm_core.nhmm import fit_nhmm
result = fit_nhmm(topo, X, covariates=Z)   # Z shape (T, n_covariates)
print(result.A_t.shape)                    # (T, K, K)
```

For GMM-NHMM, Factorial NHMM, supervised training, and the data prep
layer, see the [Advanced HMM variants](#advanced-hmm-variants) and
[Data prep layer](#data-prep-layer) sections above.

## Documentation

Full documentation is built with [mkdocs-material](https://squidfunk.github.io/mkdocs-material/)
and (when the repo has a remote) auto-deployed to GitHub Pages on every push to `main`.

Build it locally:

```bash
pip install -e ".[docs]"
mkdocs serve   # http://127.0.0.1:8000
```

Hosted at <https://rojld.github.io/HMMstudio/>.

To add a doc page, see [docs/contributing.md](docs/contributing.md).

**User guides** for the advanced variants and the prep layer live under
[`docs/guides/`](docs/guides/) — topic-oriented walkthroughs that
complement the API reference and notebook gallery.

Other quick links:

- [Notebook gallery](notebooks/) — 8 runnable notebooks (Quickstart, NHMM,
  data prep, sklearn, GMM-NHMM, Factorial NHMM, two textbook reproductions).
- [User guides](docs/guides/) — topic-oriented walkthroughs for the
  advanced variants and the prep layer.
- [Validation suite](validation/) — scientific validation layers V.1–V.6
  (cross-check vs `hmmlearn`, statistical recovery, textbook canonicals,
  numerical stability, GMM-NHMM oracles, Factorial NHMM + parameter-savings
  proof) plus V.perf regression tests.
- [Roadmap](docs/roadmap.md) — strategic overview and planned work.
- [Specs](docs/specs/) — detailed specs for sub-projects A, B, C.
- [ADRs](docs/decisions/) — architecture decision records.
- [CHANGELOG](CHANGELOG.md) — full history.

## Publishing

`hmm-studio` uses [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
(OIDC, no API token required). The release workflow lives at
[`.github/workflows/release.yml`](.github/workflows/release.yml) and fires on
any `v*.*.*` tag push.

To cut a release:

1. Bump the version in `pyproject.toml`, `CITATION.cff`, the two `__init__.py`
   files, and `src/hmm_studio/frontend/package.json`.
2. Add the version section to [CHANGELOG.md](CHANGELOG.md).
3. Tag and push: `git tag -a vX.Y.Z -m "..." && git push origin vX.Y.Z`.
4. GitHub Actions builds the wheel (Python + React frontend) and publishes
   to PyPI automatically.

First-time setup: register the project at
<https://pypi.org/manage/account/publishing/> as Pending Publisher with
owner `RoJLD`, repo `HMMstudio`, workflow `release.yml`.

## Acknowledgements

Parts of `hmm-studio` were informed by **Nathan Berbinau**'s unsupervised crypto
regime-detection research
([github.com/NathanBerbinau](https://github.com/NathanBerbinau)) — the HQIC
criterion, the model-comparison direction (`hmm-fit compare` / `/compare`), the
Giudici (2020) preset + regime labelling, mutual-information feature selection,
and the model-selection case study taught in Academy lesson 14. See
[CONTRIBUTORS.md](CONTRIBUTORS.md) for the full breakdown.

## License

MIT — see [LICENSE](LICENSE).

## Citation

If you use `hmm-studio` in academic work, please cite it via the
[CITATION.cff](CITATION.cff) file at the repository root. GitHub provides a
"Cite this repository" widget that reads it directly.
