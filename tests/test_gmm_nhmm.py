"""Tests for A.10: GMM-NHMM (two-stage MVP)."""

from __future__ import annotations

import numpy as np
import pytest

from hmm_core import GMMNHMMFittedModel, fit_gmm_nhmm
from hmm_core.topology import (
    EmissionSpec,
    FitSpec,
    InitSpec,
    Topology,
    TopologyError,
)


def _gmm_topo(K=3, n_mix=2):
    return Topology(
        name="gmm_nhmm",
        n_states=K,
        state_names=[f"s{i}" for i in range(K)],
        emission=EmissionSpec(type="gmm", n_features=2, covariance_type="diag", n_mix=n_mix),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=20, tol=1e-3),
    )


def test_fit_gmm_nhmm_returns_correct_type(synthetic_gmm_nhmm_data):
    topo = _gmm_topo()
    result = fit_gmm_nhmm(
        topo,
        synthetic_gmm_nhmm_data["X"],
        synthetic_gmm_nhmm_data["Z"],
        covariate_names=["z"],
        seed=42,
    )
    assert isinstance(result, GMMNHMMFittedModel)
    assert result.base is not None
    assert result.n_states == 3
    assert result.n_mix == 2
    assert result.A_t.shape == (len(synthetic_gmm_nhmm_data["X"]), 3, 3)


def test_fit_gmm_nhmm_A_t_rows_sum_to_one(synthetic_gmm_nhmm_data):
    topo = _gmm_topo()
    result = fit_gmm_nhmm(
        topo,
        synthetic_gmm_nhmm_data["X"],
        synthetic_gmm_nhmm_data["Z"],
        covariate_names=["z"],
        seed=42,
    )
    sums = result.A_t.sum(axis=2)
    np.testing.assert_allclose(sums, 1.0, atol=1e-10)


def test_fit_gmm_nhmm_respects_mask(synthetic_gmm_nhmm_data):
    """When the topology has a mask, A_t respects it too.

    Uses a **tridiagonal** mask (forbid skip-1 jumps a↔c) which matches the
    fixture's transition structure : the fixture only transitions to adjacent
    states (s0↔s1, s1↔s2), never directly s0→s2 or s2→s0. A strict left-right
    mask would starve some states of observations (the fixture is not
    monotonic), causing the base GMM fit to degenerate. Tridiagonal is the
    correct constraint family to exercise mask enforcement on this data.
    """
    topo = Topology(
        name="gmm_nhmm_tridiag",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=EmissionSpec(type="gmm", n_features=2, covariance_type="diag", n_mix=2),
        allowed_transitions=[
            ("a", "a"),
            ("a", "b"),
            ("b", "a"),
            ("b", "b"),
            ("b", "c"),
            ("c", "b"),
            ("c", "c"),
        ],
        startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=20, tol=1e-3),
    )
    result = fit_gmm_nhmm(
        topo,
        synthetic_gmm_nhmm_data["X"],
        synthetic_gmm_nhmm_data["Z"],
        covariate_names=["z"],
        seed=42,
    )
    mask = topo.transition_mask()
    violations = (result.A_t * (~mask)[None, :, :]).sum(axis=(1, 2))
    assert (violations < 1e-10).all()


def test_fit_gmm_nhmm_A_t_varies_with_covariate(synthetic_gmm_nhmm_data):
    """A_t should differ between low-Z and high-Z time points."""
    topo = _gmm_topo()
    result = fit_gmm_nhmm(
        topo,
        synthetic_gmm_nhmm_data["X"],
        synthetic_gmm_nhmm_data["Z"],
        covariate_names=["z"],
        seed=42,
    )
    Z = synthetic_gmm_nhmm_data["Z"][:, 0]
    low_idx = np.argsort(Z)[:75]
    high_idx = np.argsort(Z)[-75:]
    diff = np.abs(result.A_t[low_idx].mean(axis=0) - result.A_t[high_idx].mean(axis=0)).max()
    assert diff > 0.01, f"A_t doesn't depend on covariate (max diff: {diff})"


def test_fit_gmm_nhmm_rejects_non_gmm_emission():
    """fit_gmm_nhmm should reject Topologies with non-GMM emission."""
    topo = Topology(
        name="bad",
        n_states=2,
        state_names=["a", "b"],
        emission=EmissionSpec(type="gaussian", n_features=1, covariance_type="full"),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="uniform", seed=0),
        fit=FitSpec(algorithm="baum_welch", n_iter=5, tol=1e-3),
    )
    X = np.zeros((20, 1))
    Z = np.zeros((20, 1))
    with pytest.raises(TopologyError, match="gmm"):
        fit_gmm_nhmm(topo, X, Z, covariate_names=["z"])


def test_fit_gmm_nhmm_A_at_helper(synthetic_gmm_nhmm_data):
    topo = _gmm_topo()
    result = fit_gmm_nhmm(
        topo,
        synthetic_gmm_nhmm_data["X"],
        synthetic_gmm_nhmm_data["Z"],
        covariate_names=["z"],
        seed=42,
    )
    np.testing.assert_array_equal(result.A_at(100), result.A_t[100])
    # Out-of-range falls back to base
    np.testing.assert_array_equal(result.A_at(-1), result.base.model.transmat_)
    np.testing.assert_array_equal(result.A_at(99999), result.base.model.transmat_)


def test_fit_gmm_nhmm_few_transitions_falls_back():
    """Short sequence should still complete via fallback rows."""
    rng = np.random.default_rng(0)
    X = rng.normal(size=(40, 2))
    Z = rng.normal(size=(40, 1))
    topo = _gmm_topo(K=3, n_mix=2)
    result = fit_gmm_nhmm(topo, X, Z, covariate_names=["z"], seed=0, min_transitions=10)
    assert isinstance(result, GMMNHMMFittedModel)
    sums = result.A_t.sum(axis=2)
    np.testing.assert_allclose(sums, 1.0, atol=1e-10)
