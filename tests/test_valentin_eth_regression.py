"""Regression test for the Valentin ETH GMM-HMM port.

Mirrors ``notebooks/10_valentin_eth_gmm_hmm.ipynb`` end-to-end and pins the
key fit metrics so accidental changes to the ``valentin_eth`` prep recipe,
the GMM init strategy, or the EM loop are caught immediately.

The dataset is private and not committed. The test SKIPS unless the env var
``HMM_VALENTIN_ETH_PATH`` points at the file
``JDD_ETH_après la corrélation_FINAL_HMM.csv`` (Valentin Laborie 2025 S2
deliverable).

Reference values captured 2026-05-23 with hmm-studio at commit ``6f4d3e0``
(post v1.1.0, pre quality-pass). Tolerances are loose enough (±5%) to
absorb numpy / hmmlearn micro-variations across versions but tight enough
to flag real regressions.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests._regression_helpers import (
    RegressionReference,
    assert_summary_matches_reference,
    env_csv_path,
    run_recipe_fit,
    skipif_env_missing,
)

pytestmark = skipif_env_missing("HMM_VALENTIN_ETH_PATH", "Valentin ETH")


VALENTIN_REFERENCE = RegressionReference(
    summary={
        "topology_name": "valentin_eth_3regime_gmm",
        "n_states": 3,
        "emission_type": "gmm",
        "n_features": 2,
        "n_mix": 3,
        "log_likelihood": -635.72,
        "bic": 1678.04,
        "aic": 1371.43,
        "converged": True,
        "n_iter_actual": 138,
        "prep_rows": 3402,
    },
    rel_tol=0.05,
    iter_range=(50, 300),
)


@pytest.fixture(scope="module")
def summary() -> dict:
    """Run the full pipeline once and reuse the summary across tests."""
    from sklearn.decomposition import PCA

    pca = PCA(n_components=2, random_state=42)

    return run_recipe_fit(
        csv_path=env_csv_path("HMM_VALENTIN_ETH_PATH"),  # type: ignore[arg-type]
        recipe_name="valentin_eth",
        topology_yaml=Path(__file__).parent.parent / "examples" / "valentin_eth_3regime_gmm.yaml",
        csv_kwargs={"encoding": "ISO-8859-1", "parse_dates": ["date"]},
        sort_index_col="date",
        post_prep=lambda df: pca.fit_transform(df.values),
        fit_seed=42,
    )


def test_summary_matches_reference(summary: dict) -> None:
    """One assertion covering every pinned field of the reference fit."""
    assert_summary_matches_reference(summary, VALENTIN_REFERENCE)


def test_post_prep_shape(summary: dict) -> None:
    """PCA output is 2-D and has the expected row count."""
    assert summary["post_prep_shape"] == (
        3402,
        2,
    ), f"Post-PCA shape changed: {summary['post_prep_shape']} vs (3402, 2)"


def test_three_phases_all_populated(summary: dict) -> None:
    """Smoke check : each of the 3 latent phases gets > 5% of the timeline.

    Re-fits because Viterbi is not in to_summary_dict ; cached fixture
    only carries metric scalars. The cost is marginal (one PCA + EM
    re-run; ~2 s in practice).
    """
    import warnings

    import numpy as np
    import pandas as pd
    from sklearn.decomposition import PCA

    from hmm_core.fit import fit
    from hmm_core.io import load_topology
    from hmm_core.prep import Pipeline

    csv_path = env_csv_path("HMM_VALENTIN_ETH_PATH")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        df = (
            pd.read_csv(csv_path, encoding="ISO-8859-1", parse_dates=["date"])
            .sort_values("date")
            .set_index("date")
        )
        prep = Pipeline.from_recipe("valentin_eth").fit_transform(df)
        X_pca = PCA(n_components=2, random_state=42).fit_transform(prep.df.values)
        topo = load_topology(
            str(Path(__file__).parent.parent / "examples" / "valentin_eth_3regime_gmm.yaml")
        )
        fitted = fit(topo, X_pca, seed=42)
        states = fitted.model.predict(X_pca)

    for i in range(fitted.topology.n_states):
        pct = float(np.mean(states == i))
        assert pct > 0.05, (
            f"Phase {i} ({fitted.topology.state_names[i]}) is degenerate: "
            f"only {pct:.1%} of timeline — fit is broken."
        )
