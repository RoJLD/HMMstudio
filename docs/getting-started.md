# Getting started

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

## Python API

```python
from hmm_core import fit, load_topology, save_model
import pandas as pd

topo = load_topology("topology.yaml")
X = pd.read_csv("data.csv").to_numpy()
result = fit(topo, X)

print(result.log_likelihood, result.bic, result.converged)
print(result.model.transmat_)     # respects topology.transition_mask()

save_model(result, "results/run_1")
```

## NHMM (covariate-dependent transitions)

```python
from hmm_core import fit_nhmm

result = fit_nhmm(
    topo,
    X,
    Z,                          # covariates, shape (T, n_covariates)
    covariate_names=["macro_z", "rsi"],
)

# A_t[t] is the K x K transition matrix at time t, dependent on Z[t]
print(result.A_t.shape)         # (T, K, K)
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
