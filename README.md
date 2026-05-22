# hmm-studio

> CI is configured but not yet active — this repo has no remote. After
> pushing to GitHub, add `[![CI](https://github.com/<user>/<repo>/actions/workflows/ci.yml/badge.svg)](https://github.com/<user>/<repo>/actions/workflows/ci.yml)` below the title.

HMM topology editor, constrained fit engine, and visualizer.

This repo currently ships **`hmm-core`** — a domain-agnostic Python engine
for fitting HMMs with structurally constrained transition matrices.
A future `hmm-studio` web UI (node-based topology editor) will sit on top
of `hmm-core` and is tracked under [docs/specs/](docs/specs/).

## Why this exists

`hmmlearn` (and most HMM libraries) fit ergodic models: every transition
edge is free. Real applications often need **structural priors** — Bakis
left-right speech models, lifecycle models with forbidden back-transitions,
branching topologies. `hmm-core` lets you declare which transitions are
allowed and runs constrained Baum-Welch that respects those zeros at every
M-step.

## Install

```bash
git clone <repo-url>
cd hmm_studio
python -m venv .venv
.venv\Scripts\activate              # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest                              # all green
```

## 30-second tour

```bash
# 1. Generate a synthetic 4-state Gaussian sequence.
python examples/generate_demo_data.py

# 2. Validate the topology YAML.
hmm-fit validate examples/topology_left_right.yaml

# 3. Fit with constraints (left-right + forbidden back-edges).
hmm-fit run examples/topology_left_right.yaml examples/data_gaussian.csv \
    --output results/demo

# 4. Inspect.
hmm-fit show results/demo/model.pkl
# Forbidden edges print as `x` instead of probabilities.

# 5. Decode new data.
hmm-fit decode results/demo/model.pkl examples/data_gaussian.csv \
    --output results/demo/decoded.parquet
```

## Topology YAML schema

```yaml
name: my_model              # free-text identifier
n_states: 4                 # K
state_names: [s0, s1, s2, s3]

emission:
  type: gaussian            # gaussian | gmm | multinomial | poisson
  covariance_type: full     # gaussian/gmm: full | diag | tied | spherical
  n_features: 2             # gaussian/gmm/poisson: observation dimension
  n_mix: null               # gmm only: number of mixture components per state
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

- **gaussian / gmm / poisson** : CSV with `n_features` numeric columns.
- **multinomial** : CSV with a single integer column, values in `[0, n_symbols)`.

The order of CSV columns is the order of observation features.

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

## Multinomial example

```yaml
name: dna_codons
n_states: 3
state_names: [intron, exon, regulatory]
emission:
  type: multinomial
  n_symbols: 4              # A, C, G, T
startprob: uniform
init: {strategy: uniform, seed: 0}
fit: {algorithm: baum_welch, n_iter: 100, tol: 1.0e-4}
# Omit allowed_transitions => ergodic
```

## Sub-projects

- **A — `hmm-core`** (shipped here) — Python engine + CLI.
- **B — `hmm-studio`** (planned) — FastAPI + React Flow node-based topology
  editor that produces these YAML files.
- **C — Advanced viz** (planned) — NHMM breathing transitions, replay UI.

## Web UI (B.1 backend skeleton + B.4.1 topology editor)

`hmm-studio` (sub-project B) is in progress. The backend ships with:

- FastAPI app with topology validation, dataset upload, and fit job orchestration
- SQLite persistence (jobs survive restarts)
- ThreadPoolExecutor for parallel fits
- Swagger UI at `/docs`

Install + launch:

```bash
pip install -e ".[web,dev]"
python scripts/build_frontend.py   # builds + copies frontend assets
hmm-studio                          # http://127.0.0.1:8000
```

If you skip the frontend build step, only the REST API is served — the React UI returns a default FastAPI 404.

Swagger UI is always available at `http://127.0.0.1:8000/docs` regardless of whether the frontend build has been run.

### Visual topology editor (B.4.1)

The visual topology editor is shipped. After `hmm-studio`, open
`http://127.0.0.1:8000/topology` in a browser to:

- Drag-drop states onto the canvas
- Draw transitions by dragging from a node's right handle to another's left
- Rename states by clicking on the label
- Configure global emission/init/fit params in the side panel
- See live validation feedback (debounced 400ms against the API)
- Undo/redo (50 steps)
- Import / Export topology YAML (byte-compatible with `hmm-fit`)

Data upload (B.5) and results view (B.6) are next.

The visual editor currently exposes the hmm-core API as it exists today
(single global EmissionSpec, hard 0/1 allowed_transitions). Per-state
emissions (A.8 + B.4.2) and Dirichlet priors on transitions (A.9 +
B.4.3) are planned extensions documented in the roadmap.

See [docs/roadmap.md](docs/roadmap.md)
and [docs/specs/2026-05-21-hmm-studio-web-design.md](docs/specs/2026-05-21-hmm-studio-web-design.md).

## One-click launcher (Rancher Desktop / Docker)

For a packaged Docker deployment with Rancher Desktop (or Docker Desktop):

```
.\start.ps1        # or start.bat
```

This builds the image (multi-stage: Node 20 builds the React frontend, then
Python 3.12 installs the package with the frontend baked into `server/static/`),
runs the container with a named volume for the SQLite DB + uploads + results
(survives image rebuilds), waits for `/health`, and opens the UI at
`http://localhost:8000`.

```
.\stop.ps1                # graceful stop, restart fast via start.ps1
docker compose down       # full teardown (volume kept)
docker compose down -v    # wipe volume too (clears DB, uploads, results)
```

**Desktop shortcut**: right-click `start.bat`, "Send to" → "Desktop (create
shortcut)". Rename to "hmm-studio" if you like.

## License

MIT — see [LICENSE](LICENSE).

## Citation

If you use `hmm-studio` in academic work, please cite it via the
[CITATION.cff](CITATION.cff) file at the repository root (GitHub provides
a "Cite this repository" widget that reads it).
