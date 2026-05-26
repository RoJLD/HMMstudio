"""Regression test for the Valentin ETH GMM-HMM port.

Mirrors ``notebooks/10_valentin_eth_gmm_hmm.ipynb`` end-to-end and pins the
key metrics (log-likelihood, BIC, convergence) so accidental changes to the
``valentin_eth`` prep recipe, the GMM init strategy, or the EM loop are
caught immediately.

The dataset is private and not committed. The test SKIPS unless the env var
``HMM_VALENTIN_ETH_PATH`` points at the file
``JDD_ETH_après la corrélation_FINAL_HMM.csv`` (Valentin Laborie 2025 S2
deliverable).

Reference values were captured on 2026-05-23 with hmm-studio at commit
``a864953`` (post v1.1.0). Tolerances are loose enough (±5%) to absorb
numpy / hmmlearn micro-variations across versions but tight enough to flag
real regressions in the prep + fit pipeline.
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path

import pytest

# Reference values from the 2026-05-23 run on Valentin's CSV
REF_LOG_LIKELIHOOD = -635.72
REF_BIC = 1678.04
REF_AIC = 1371.43
REF_N_OBS_AFTER_PREP = 3402
REF_PCA_EXPLAINED_VAR = 0.880
REF_ITERS_RANGE = (50, 300)  # widely loose

TOL_LL = 0.05  # 5% relative tolerance on log-likelihood
TOL_BIC = 0.05
TOL_PCA = 0.02


def _csv_path() -> Path | None:
    raw = os.environ.get("HMM_VALENTIN_ETH_PATH")
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_file() else None


pytestmark = pytest.mark.skipif(
    _csv_path() is None,
    reason=(
        "HMM_VALENTIN_ETH_PATH is unset or does not point at an existing file. "
        "Set it to the absolute path of Valentin's "
        "JDD_ETH_après la corrélation_FINAL_HMM.csv to run this regression."
    ),
)


@pytest.fixture(scope="module")
def fitted_setup():
    """Load CSV → recipe → PCA → fit. Returns the dict the assertions check."""
    import pandas as pd
    from sklearn.decomposition import PCA

    from hmm_core.fit import fit
    from hmm_core.io import load_topology
    from hmm_core.prep import Pipeline

    csv_path = _csv_path()
    assert csv_path is not None  # guarded by skipif

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        df = (
            pd.read_csv(csv_path, encoding="ISO-8859-1", parse_dates=["date"])
            .sort_values("date")
            .set_index("date")
        )
        prep = Pipeline.from_recipe("valentin_eth").fit_transform(df)
        pca = PCA(n_components=2, random_state=42)
        X_pca = pca.fit_transform(prep.df.values)

        topology_yaml = (
            Path(__file__).parent.parent
            / "examples"
            / "valentin_eth_3regime_gmm.yaml"
        )
        topo = load_topology(str(topology_yaml))
        fitted = fit(topo, X_pca, seed=42)

    return {
        "prep_rows": prep.df.shape[0],
        "pca_explained_var": float(pca.explained_variance_ratio_.sum()),
        "fitted": fitted,
        "X_pca_len": len(X_pca),
    }


def test_recipe_output_shape(fitted_setup):
    assert fitted_setup["prep_rows"] == REF_N_OBS_AFTER_PREP, (
        f"Recipe output rows changed: {fitted_setup['prep_rows']} vs "
        f"reference {REF_N_OBS_AFTER_PREP}. Inspect valentin_eth.yaml."
    )


def test_pca_explained_variance(fitted_setup):
    got = fitted_setup["pca_explained_var"]
    assert abs(got - REF_PCA_EXPLAINED_VAR) < TOL_PCA, (
        f"PCA explained variance drifted: got {got:.3f}, ref {REF_PCA_EXPLAINED_VAR:.3f}"
    )


def test_log_likelihood_within_tolerance(fitted_setup):
    fitted = fitted_setup["fitted"]
    ll = fitted.log_likelihood
    rel_err = abs(ll - REF_LOG_LIKELIHOOD) / abs(REF_LOG_LIKELIHOOD)
    assert rel_err < TOL_LL, (
        f"Log-likelihood drifted: got {ll:.2f}, ref {REF_LOG_LIKELIHOOD:.2f} "
        f"(relative error {rel_err:.3%} > {TOL_LL:.0%})"
    )


def test_bic_within_tolerance(fitted_setup):
    fitted = fitted_setup["fitted"]
    rel_err = abs(fitted.bic - REF_BIC) / abs(REF_BIC)
    assert rel_err < TOL_BIC, (
        f"BIC drifted: got {fitted.bic:.2f}, ref {REF_BIC:.2f} "
        f"(relative error {rel_err:.3%})"
    )


def test_converges_within_iter_budget(fitted_setup):
    fitted = fitted_setup["fitted"]
    assert fitted.converged, "EM did not converge"
    lo, hi = REF_ITERS_RANGE
    assert lo <= fitted.n_iter_actual <= hi, (
        f"Iterations outside expected range: {fitted.n_iter_actual} not in [{lo}, {hi}]"
    )


def test_three_phases_all_populated(fitted_setup):
    """Smoke check: each of the 3 latent phases gets at least 5% of the timeline."""
    import numpy as np

    fitted = fitted_setup["fitted"]
    # Re-decode from the fitted model on the same X
    # (X_pca isn't stored on the fixture to keep memory low; rebuild minimally)
    import pandas as pd
    from sklearn.decomposition import PCA

    from hmm_core.prep import Pipeline

    csv_path = _csv_path()
    df = (
        pd.read_csv(csv_path, encoding="ISO-8859-1", parse_dates=["date"])
        .sort_values("date")
        .set_index("date")
    )
    prep = Pipeline.from_recipe("valentin_eth").fit_transform(df)
    X_pca = PCA(n_components=2, random_state=42).fit_transform(prep.df.values)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        states = fitted.model.predict(X_pca)

    for i in range(fitted.topology.n_states):
        pct = float(np.mean(states == i))
        assert pct > 0.05, (
            f"Phase {i} ({fitted.topology.state_names[i]}) is degenerate: "
            f"only {pct:.1%} of timeline — fit is broken."
        )
