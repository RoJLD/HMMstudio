# hmm-studio notebook gallery

Canonical Jupyter notebooks demonstrating `hmm-studio` capabilities.

Every notebook is **runnable as-is** (no external data dependencies) and
showcases rich HTML rendering of `hmm-studio` objects (heatmaps, statistics
tables, sequence strips).

## Running locally

```bash
pip install "hmm-studio[dev]"
jupyter lab notebooks/
```

## Running in a hosted environment

The notebooks have no GPU requirements and run in seconds. They work in :
- JupyterLab / Jupyter Notebook
- VS Code notebook view
- Google Colab (after `pip install hmm-studio`)
- Hex / Deepnote (after install)

## Notebooks

| # | Notebook | Topic |
|---|---|---|
| 01 | [Quickstart](01_quickstart.ipynb) | 30-second tour : declare topology, fit, decode. Includes left-right constrained example. |
| 02 | [NHMM for crypto regimes](02_nhmm_crypto.ipynb) | Covariate-dependent transitions, A_t inspection, decoded path accuracy. |
| 03 | [Data prep recipes](03_data_prep_recipes.ipynb) | Bundled recipes, Python pipeline builder, provenance sidecar. |
| 04 | [sklearn pipeline integration](04_sklearn_pipeline.ipynb) | Drop-in `HMMClassifier` in sklearn `Pipeline`, `GridSearchCV`, `cross_val_score`. |
| 05 | [GMM-NHMM sub-modes](05_gmm_nhmm_submodes.ipynb) | Multi-modal regimes : each state hosts a Gaussian mixture, transitions modulated by covariates. |
| 06 | [Factorial NHMM multi-factor](06_factorial_nhmm_multifactor.ipynb) | Independent regime dimensions (trend × vol), per-chain covariates, parameter savings vs joint HMM. |
| 07 | [Textbook : AIMA umbrella world](07_textbook_aima_umbrella.ipynb) | Reproduce Russell & Norvig Chap. 14 smoothing + filtering values on the canonical 5-step sequence. |
| 08 | [Textbook : Durbin dishonest casino](08_textbook_dishonest_casino.ipynb) | Reproduce the Viterbi recovery accuracy from Durbin et al. *Biological Sequence Analysis* Chap. 3. |

## Philosophy

These notebooks ARE the documentation. They demonstrate :
1. **Pip-installable** — no separate environment needed
2. **Jupyter-native** — rich HTML displays everywhere
3. **Composable** — every object is an input or output of others
4. **Reproducible** — fixed seeds, provenance sidecars

This is the **hmm-studio philosophy** : we're the deepest HMM library in
your Python scientific stack. We don't replace your research environment ;
we slot in as the HMM specialist.

See [docs/decisions/0012-distribution-strategy-hybrid.md](../docs/decisions/0012-distribution-strategy-hybrid.md)
for the strategic positioning.
