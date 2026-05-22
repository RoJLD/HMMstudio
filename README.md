# hmm-studio

<!-- After pushing to GitHub, replace the placeholder below with the real badge URLs. -->
<!-- [![CI](https://github.com/<user>/hmm-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/<user>/hmm-studio/actions/workflows/ci.yml) -->

`hmm-studio` is a Python package and web application for authoring, fitting,
and visualizing Hidden Markov Models with **structurally constrained transition
matrices**. It ships two integrated layers: `hmm_core`, a domain-agnostic
constrained Baum-Welch engine, and `hmm_studio`, a FastAPI + React web UI
that lets you draw topologies, launch fits, compare model orders (K-scan),
and inspect results — all from a browser.

## Why this exists

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

Supervised training (observed state labels):

```python
result = fit(topo, X, state_labels=y)      # y shape (T,), int in [0, K)
```

## Documentation

- [Roadmap](docs/roadmap.md) — strategic overview and planned work.
- [Specs](docs/specs/) — detailed specs for sub-projects A, B, C.
- [ADRs](docs/decisions/) — 6 architecture decision records.
- [CHANGELOG](CHANGELOG.md) — full history.

Serve locally with `mkdocs serve` (requires `pip install "hmm-studio[docs]"`).

## Publishing

`hmm-studio` uses [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
(OIDC, no API token required). Once the GitHub remote is configured:

1. Register the project at https://pypi.org/manage/account/publishing/ pointing
   to the `release.yml` workflow.
2. Push a version tag: `git tag -a v1.0.0 -m "..." && git push origin v1.0.0`.
3. GitHub Actions builds the wheel (including the React frontend) and publishes
   to PyPI automatically.

## License

MIT — see [LICENSE](LICENSE).

## Citation

If you use `hmm-studio` in academic work, please cite it via the
[CITATION.cff](CITATION.cff) file at the repository root. GitHub provides a
"Cite this repository" widget that reads it directly.
