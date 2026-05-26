# hmm-studio notebook gallery

[![Open in Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/RoJLD/HMMstudio/main?urlpath=lab/tree/notebooks)
[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/RoJLD/HMMstudio/blob/main/notebooks/)

Canonical Jupyter notebooks demonstrating `hmm-studio` capabilities.

**One-click run** : the Binder badge above launches the entire gallery in a
cloud notebook server — no install, no setup, ~30 seconds to first cell
output. The Colab badge opens individual notebooks in Google Colab (you'll
need to `!pip install hmm-studio` in the first cell).

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
- **mybinder.org** — click the Binder badge above (zero install)
- **Google Colab** — click the Colab badge or open any notebook URL on github
- **JupyterLab / Jupyter Notebook** — local
- **VS Code notebook view** — local
- **Hex / Deepnote** — after `pip install hmm-studio`

## Notebooks

| # | Notebook | Topic | Binder |
|---|---|---|---|
| 01 | [Quickstart](01_quickstart.ipynb) | 30-second tour : declare topology, fit, decode. Includes left-right constrained example. | [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/RoJLD/HMMstudio/main?urlpath=lab/tree/notebooks/01_quickstart.ipynb) |
| 02 | [NHMM for crypto regimes](02_nhmm_crypto.ipynb) | Covariate-dependent transitions, A_t inspection, decoded path accuracy. | [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/RoJLD/HMMstudio/main?urlpath=lab/tree/notebooks/02_nhmm_crypto.ipynb) |
| 03 | [Data prep recipes](03_data_prep_recipes.ipynb) | Bundled recipes, Python pipeline builder, provenance sidecar. | [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/RoJLD/HMMstudio/main?urlpath=lab/tree/notebooks/03_data_prep_recipes.ipynb) |
| 04 | [sklearn pipeline integration](04_sklearn_pipeline.ipynb) | Drop-in `HMMClassifier` in sklearn `Pipeline`, `GridSearchCV`, `cross_val_score`. | [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/RoJLD/HMMstudio/main?urlpath=lab/tree/notebooks/04_sklearn_pipeline.ipynb) |
| 05 | [GMM-NHMM sub-modes](05_gmm_nhmm_submodes.ipynb) | Multi-modal regimes : each state hosts a Gaussian mixture, transitions modulated by covariates. | [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/RoJLD/HMMstudio/main?urlpath=lab/tree/notebooks/05_gmm_nhmm_submodes.ipynb) |
| 06 | [Factorial NHMM multi-factor](06_factorial_nhmm_multifactor.ipynb) | Independent regime dimensions (trend × vol), per-chain covariates, parameter savings vs joint HMM. | [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/RoJLD/HMMstudio/main?urlpath=lab/tree/notebooks/06_factorial_nhmm_multifactor.ipynb) |
| 07 | [Textbook : AIMA umbrella world](07_textbook_aima_umbrella.ipynb) | Reproduce Russell & Norvig Chap. 14 smoothing + filtering values on the canonical 5-step sequence. | [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/RoJLD/HMMstudio/main?urlpath=lab/tree/notebooks/07_textbook_aima_umbrella.ipynb) |
| 08 | [Textbook : Durbin dishonest casino](08_textbook_dishonest_casino.ipynb) | Reproduce the Viterbi recovery accuracy from Durbin et al. *Biological Sequence Analysis* Chap. 3. | [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/RoJLD/HMMstudio/main?urlpath=lab/tree/notebooks/08_textbook_dishonest_casino.ipynb) |

## Suggested learning path

For HMM newcomers, run the notebooks in order :

1. **01 → 02** : foundations (topology + covariate transitions)
2. **03** : preprocessing (recipes + provenance — useful for any modeling)
3. **04** : sklearn integration (the practical mainstream workflow)
4. **05 → 06** : advanced models (sub-modes within regimes, multi-factor regimes)
5. **07 → 08** : canonical textbook problems (build confidence the math is right)

For practitioners with a specific use case : jump straight to whichever notebook
matches your problem (regime detection → 02 or 06, sklearn pipeline → 04,
sub-mode discovery → 05, validation → 07/08).

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
