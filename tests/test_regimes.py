"""Tests for hmm_core.regimes — semantic state labelling.

Covers the Giudici 2020 BTC-regime convention (bear / stable / bull,
ordered by mean log-return) plus the generic ordering helpers on Gaussian,
GMM, and Poisson emissions.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pytest

from hmm_core.fit import fit
from hmm_core.io import load_topology
from hmm_core.regimes import (
    regime_labels,
    regime_order_by_feature_mean,
)
from hmm_core.topology import EmissionSpec, FitSpec, InitSpec, Topology


def _three_regime_gaussian_data(seed: int = 0):
    """Synthetic 1-D returns with three well-separated regime means."""
    rng = np.random.default_rng(seed)
    # bear (low), stable (mid), bull (high) blocks
    bear = rng.normal(-3.0, 0.4, (120, 1))
    stable = rng.normal(0.0, 0.4, (120, 1))
    bull = rng.normal(3.0, 0.4, (120, 1))
    return np.vstack([bear, stable, bull])


def _giudici_topo():
    return Topology(
        name="giudici_test",
        n_states=3,
        state_names=["bear", "stable", "bull"],
        emission=EmissionSpec(type="gaussian", covariance_type="diag", n_features=1),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=100, tol=1e-4),
    )


def test_regime_order_ascending_by_mean():
    """Order is ascending by mean feature: result[0] is lowest-mean state."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = fit(_giudici_topo(), _three_regime_gaussian_data(), seed=42)
    order = regime_order_by_feature_mean(result, feature=0)
    means = np.asarray(result.model.means_)[:, 0]
    # The ordering must sort the means ascending
    assert means[order[0]] <= means[order[1]] <= means[order[2]]
    assert sorted(order) == [0, 1, 2]  # a valid permutation


def test_regime_labels_bear_stable_bull():
    """Lowest-mean state gets 'bear', highest gets 'bull'."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = fit(_giudici_topo(), _three_regime_gaussian_data(), seed=42)
    labels = regime_labels(result, ["bear", "stable", "bull"], feature=0)
    means = np.asarray(result.model.means_)[:, 0]
    # The state labelled 'bear' must have the minimum mean; 'bull' the maximum.
    bear_idx = [i for i, lab in labels.items() if lab == "bear"][0]
    bull_idx = [i for i, lab in labels.items() if lab == "bull"][0]
    assert means[bear_idx] == means.min()
    assert means[bull_idx] == means.max()
    assert set(labels.values()) == {"bear", "stable", "bull"}


def test_regime_labels_wrong_count_raises():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = fit(_giudici_topo(), _three_regime_gaussian_data(), seed=42)
    with pytest.raises(ValueError, match="expected 3 labels"):
        regime_labels(result, ["low", "high"], feature=0)


def test_regime_order_poisson():
    """Ordering works on Poisson emissions via lambdas_."""
    rng = np.random.default_rng(1)
    low = rng.poisson(1.0, (100, 1))
    high = rng.poisson(12.0, (100, 1))
    X = np.vstack([low, high]).astype(float)
    topo = Topology(
        name="poisson_test",
        n_states=2,
        state_names=["quiet", "busy"],
        emission=EmissionSpec(type="poisson", n_features=1),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=0),
        fit=FitSpec(algorithm="baum_welch", n_iter=50, tol=1e-4),
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = fit(topo, X, seed=0)
    order = regime_order_by_feature_mean(result, feature=0)
    lambdas = np.asarray(result.model.lambdas_)[:, 0]
    assert lambdas[order[0]] <= lambdas[order[1]]


def test_regime_order_multinomial_raises():
    """Multinomial has no continuous feature-mean -> clear TypeError."""
    rng = np.random.default_rng(2)
    X = rng.integers(0, 4, (200, 1))
    topo = Topology(
        name="multi_test",
        n_states=2,
        state_names=["a", "b"],
        emission=EmissionSpec(type="multinomial", n_symbols=4),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="random", seed=0),
        fit=FitSpec(algorithm="baum_welch", n_iter=30, tol=1e-4),
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = fit(topo, X, seed=0)
    with pytest.raises(TypeError, match="means_|lambdas_"):
        regime_order_by_feature_mean(result, feature=0)


def test_giudici_example_yaml_loads_and_fits():
    """The bundled Giudici example topology loads, fits, and canonicalises."""
    yaml_path = Path(__file__).parent.parent / "examples" / "giudici_2020_btc_regimes.yaml"
    topo = load_topology(str(yaml_path))
    assert topo.n_states == 3
    assert topo.emission.type == "gaussian"
    assert topo.emission.covariance_type == "diag"
    assert topo.emission.n_features == 1
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = fit(topo, _three_regime_gaussian_data(), seed=42)
    labels = regime_labels(result, ["bear", "stable", "bull"])
    assert set(labels.values()) == {"bear", "stable", "bull"}
