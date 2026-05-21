"""Tests for fit_nhmm: 2-stage NHMM with covariate-dependent transitions."""

from __future__ import annotations

import numpy as np

from hmm_core.nhmm import NHMMFittedModel, fit_nhmm
from hmm_core.topology import EmissionSpec, FitSpec, InitSpec, Topology


def _gaussian_topo_k3():
    return Topology(
        name="g3",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=EmissionSpec(type="gaussian", n_features=2, covariance_type="full"),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=20, tol=1e-4),
    )


def test_fit_nhmm_returns_nhmm_fitted_model(synthetic_nhmm_data):
    topo = _gaussian_topo_k3()
    X = synthetic_nhmm_data["X"]
    Z = synthetic_nhmm_data["Z"]
    result = fit_nhmm(topo, X, Z, covariate_names=["z"], seed=42)
    assert isinstance(result, NHMMFittedModel)
    assert result.base is not None
    assert result.covariate_names == ["z"]
    assert result.A_t.shape == (len(X), 3, 3)


def test_A_t_rows_sum_to_one(synthetic_nhmm_data):
    topo = _gaussian_topo_k3()
    result = fit_nhmm(
        topo, synthetic_nhmm_data["X"], synthetic_nhmm_data["Z"], covariate_names=["z"], seed=42
    )
    # Every t, every row should sum to 1.
    sums = result.A_t.sum(axis=2)  # (T, K)
    np.testing.assert_allclose(sums, 1.0, atol=1e-10)


def test_A_t_respects_mask(synthetic_nhmm_data):
    """When the base topology has a mask, A_t must also respect it."""
    topo = Topology(
        name="lr3",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=EmissionSpec(type="gaussian", n_features=2, covariance_type="diag"),
        allowed_transitions=[("a", "a"), ("a", "b"), ("b", "b"), ("b", "c"), ("c", "c")],
        startprob="first_state",
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=20, tol=1e-4),
    )
    result = fit_nhmm(
        topo, synthetic_nhmm_data["X"], synthetic_nhmm_data["Z"], covariate_names=["z"], seed=42
    )
    mask = topo.transition_mask()
    # A_t[t] * (~mask) should be ~0 for every t.
    violations = (result.A_t * (~mask)[None, :, :]).sum(axis=(1, 2))
    assert (violations < 1e-10).all()


def test_A_t_varies_with_covariate(synthetic_nhmm_data):
    """If the covariate truly drives transitions, A_t should differ between
    extreme Z values. Without this property, NHMM is no better than HMM."""
    topo = _gaussian_topo_k3()
    result = fit_nhmm(
        topo, synthetic_nhmm_data["X"], synthetic_nhmm_data["Z"], covariate_names=["z"], seed=42
    )
    Z = synthetic_nhmm_data["Z"][:, 0]
    # Compare A_t at the lowest 5% Z values vs highest 5%.
    low_idx = np.argsort(Z)[:50]
    high_idx = np.argsort(Z)[-50:]
    A_low_mean = result.A_t[low_idx].mean(axis=0)
    A_high_mean = result.A_t[high_idx].mean(axis=0)
    # They should differ noticeably (not identical to 6 decimals).
    diff = np.abs(A_low_mean - A_high_mean).max()
    assert diff > 0.01, f"A_t doesn't depend on covariate (max diff: {diff})"


def test_fit_nhmm_few_transitions_falls_back():
    """If a source state has fewer than min_transitions, NHMM falls back to
    homogeneous A row. No crash."""
    # Very short sequence: state 2 is unlikely to see many transitions.
    rng = np.random.default_rng(0)
    X = rng.normal(size=(50, 2))
    Z = rng.normal(size=(50, 1))
    topo = _gaussian_topo_k3()
    result = fit_nhmm(topo, X, Z, covariate_names=["z"], seed=0, min_transitions=10)
    assert isinstance(result, NHMMFittedModel)
    # Result is sane regardless.
    sums = result.A_t.sum(axis=2)
    np.testing.assert_allclose(sums, 1.0, atol=1e-10)


def test_A_at_t_helper(synthetic_nhmm_data):
    """Convenience method NHMMFittedModel.A_at(t) returns the right slice."""
    topo = _gaussian_topo_k3()
    result = fit_nhmm(
        topo, synthetic_nhmm_data["X"], synthetic_nhmm_data["Z"], covariate_names=["z"], seed=42
    )
    np.testing.assert_array_equal(result.A_at(100), result.A_t[100])
    # Out-of-bounds falls back to base homogeneous transmat.
    np.testing.assert_array_equal(result.A_at(-1), result.base.model.transmat_)
    np.testing.assert_array_equal(result.A_at(99999), result.base.model.transmat_)
