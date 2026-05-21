"""Tests for init.transmat / init.startprob / init.emission_params."""

from __future__ import annotations

import numpy as np
import pytest

from hmm_core import init
from hmm_core.topology import (
    EmissionSpec,
    FitSpec,
    InitSpec,
    Topology,
)


def _make_topo(strategy: str, startprob: str | list = "uniform"):
    return Topology(
        name="t",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=EmissionSpec(type="gaussian", n_features=2, covariance_type="full"),
        allowed_transitions=[("a", "a"), ("a", "b"), ("b", "b"), ("b", "c"), ("c", "c")],
        startprob=startprob,
        init=InitSpec(strategy=strategy, seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=10, tol=1e-4),
    )


def test_uniform_transmat_respects_mask():
    topo = _make_topo("uniform")
    A = init.transmat(topo, seed=42)
    mask = topo.transition_mask()
    assert (A * (~mask)).sum() == 0
    np.testing.assert_allclose(A.sum(axis=1), 1.0, atol=1e-12)
    # Row 0 has 2 allowed edges, so each is 0.5.
    assert A[0, 0] == pytest.approx(0.5)
    assert A[0, 1] == pytest.approx(0.5)


def test_random_transmat_respects_mask_and_is_deterministic():
    topo = _make_topo("random")
    A1 = init.transmat(topo, seed=42)
    A2 = init.transmat(topo, seed=42)
    np.testing.assert_allclose(A1, A2)
    mask = topo.transition_mask()
    assert (A1 * (~mask)).sum() == 0
    np.testing.assert_allclose(A1.sum(axis=1), 1.0, atol=1e-12)
    # Random != uniform.
    assert not np.allclose(A1, init.transmat(_make_topo("uniform"), seed=42))


def test_startprob_uniform():
    topo = _make_topo("uniform", startprob="uniform")
    pi = init.startprob(topo, seed=42)
    np.testing.assert_allclose(pi, np.array([1/3, 1/3, 1/3]))


def test_startprob_first_state():
    topo = _make_topo("uniform", startprob="first_state")
    pi = init.startprob(topo, seed=42)
    np.testing.assert_allclose(pi, np.array([1.0, 0.0, 0.0]))


def test_startprob_explicit_list():
    topo = _make_topo("uniform", startprob=[0.5, 0.3, 0.2])
    pi = init.startprob(topo, seed=42)
    np.testing.assert_allclose(pi, np.array([0.5, 0.3, 0.2]))


def test_kmeans_requires_X():
    topo = _make_topo("kmeans")
    with pytest.raises(ValueError, match="kmeans"):
        init.transmat(topo, seed=42, X=None)
    with pytest.raises(ValueError, match="kmeans"):
        init.emission_params(topo, X=None, seed=42)


def test_kmeans_emission_means_match_centroids(synthetic_gaussian_left_right):
    topo = _make_topo("kmeans")
    X = synthetic_gaussian_left_right["X"]
    params = init.emission_params(topo, X=X, seed=42)
    assert "means_" in params
    assert "covars_" in params
    assert params["means_"].shape == (3, 2)
    # Verify against direct k-means.
    from sklearn.cluster import KMeans
    km = KMeans(n_clusters=3, random_state=42, n_init=10).fit(X)
    # Order may differ; check that each centroid is matched to one mean.
    for c in km.cluster_centers_:
        dists = np.linalg.norm(params["means_"] - c, axis=1)
        assert dists.min() < 1e-8


def test_data_frequencies_requires_X():
    topo = _make_topo("data_frequencies")
    with pytest.raises(ValueError, match="data_frequencies"):
        init.transmat(topo, seed=42, X=None)


def test_data_frequencies_respects_mask(synthetic_gaussian_left_right):
    topo = _make_topo("data_frequencies")
    X = synthetic_gaussian_left_right["X"]
    A = init.transmat(topo, seed=42, X=X)
    mask = topo.transition_mask()
    assert (A * (~mask)).sum() == 0
    np.testing.assert_allclose(A.sum(axis=1), 1.0, atol=1e-12)


def test_data_frequencies_emission_matches_kmeans(synthetic_gaussian_left_right):
    """data_frequencies reuses kmeans for emission params (same as 'kmeans')."""
    topo_df = _make_topo("data_frequencies")
    topo_km = _make_topo("kmeans")
    X = synthetic_gaussian_left_right["X"]
    params_df = init.emission_params(topo_df, X=X, seed=42)
    params_km = init.emission_params(topo_km, X=X, seed=42)
    np.testing.assert_allclose(params_df["means_"], params_km["means_"])
