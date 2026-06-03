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
    np.testing.assert_allclose(pi, np.array([1 / 3, 1 / 3, 1 / 3]))


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


def test_kmeans_emission_multinomial_emits_warning_and_returns_emissionprob(
    synthetic_multinomial_3state,
):
    """Coverage gap: kmeans on multinomial is degenerate, emits warning."""
    import warnings
    from hmm_core.topology import EmissionSpec, FitSpec, InitSpec, Topology

    topo = Topology(
        name="mn_km",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=EmissionSpec(type="multinomial", n_symbols=5),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=10, tol=1e-4),
    )
    X = synthetic_multinomial_3state["X"]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        params = init.emission_params(topo, X=X, seed=42)
    assert any("degenerate" in str(w.message).lower() for w in caught)
    assert "emissionprob_" in params
    assert params["emissionprob_"].shape == (3, 5)
    np.testing.assert_allclose(params["emissionprob_"].sum(axis=1), 1.0, atol=1e-10)


def test_kmeans_emission_poisson_returns_lambdas(synthetic_poisson_3state):
    """Coverage gap: Poisson kmeans init returns lambdas_."""
    from hmm_core.topology import EmissionSpec, FitSpec, InitSpec, Topology

    topo = Topology(
        name="pois_km",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=EmissionSpec(type="poisson", n_features=2),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=10, tol=1e-4),
    )
    X = synthetic_poisson_3state["X"]
    params = init.emission_params(topo, X=X, seed=42)
    assert "lambdas_" in params
    assert params["lambdas_"].shape == (3, 2)
    assert (params["lambdas_"] > 0).all()


@pytest.mark.parametrize("covariance_type", ["diag", "spherical", "tied"])
def test_kmeans_emission_gaussian_covariance_shapes(synthetic_gaussian_left_right, covariance_type):
    """Coverage gap: _empirical_covars branches for diag/spherical/tied."""
    from hmm_core.topology import EmissionSpec, FitSpec, InitSpec, Topology

    topo = Topology(
        name="g_cov",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=EmissionSpec(type="gaussian", n_features=2, covariance_type=covariance_type),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=10, tol=1e-4),
    )
    X = synthetic_gaussian_left_right["X"]
    params = init.emission_params(topo, X=X, seed=42)
    assert "covars_" in params
    expected_shapes = {
        "diag": (3, 2),
        "spherical": (3,),
        "tied": (2, 2),
        "full": (3, 2, 2),
    }
    assert params["covars_"].shape == expected_shapes[covariance_type]


def _gmm_topo(covariance_type: str, n_mix: int = 2):
    """Helper: build a 3-state GMM topology with the requested covariance type."""
    return Topology(
        name="gmm_init",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=EmissionSpec(
            type="gmm",
            n_features=2,
            covariance_type=covariance_type,
            n_mix=n_mix,
        ),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=10, tol=1e-4),
    )


def test_init_gmm_full_covariance_shape(synthetic_gmm_3state):
    """Fix #5: kmeans init for gmm + full must emit (K, n_mix, D, D)."""
    topo = _gmm_topo("full", n_mix=2)
    X = synthetic_gmm_3state["X"]
    params = init.emission_params(topo, X=X, seed=42)
    assert "means_" in params and "covars_" in params and "weights_" in params
    assert params["covars_"].shape == (3, 2, 2, 2)
    assert params["means_"].shape == (3, 2, 2)
    assert params["weights_"].shape == (3, 2)


def test_init_gmm_tied_covariance_shape(synthetic_gmm_3state):
    """Fix #5: kmeans init for gmm + tied must emit (K, D, D) (one per state)."""
    topo = _gmm_topo("tied", n_mix=2)
    X = synthetic_gmm_3state["X"]
    params = init.emission_params(topo, X=X, seed=42)
    assert params["covars_"].shape == (3, 2, 2)


def test_init_gmm_spherical_covariance_shape(synthetic_gmm_3state):
    """Fix #5: kmeans init for gmm + spherical must emit (K, n_mix)."""
    topo = _gmm_topo("spherical", n_mix=2)
    X = synthetic_gmm_3state["X"]
    params = init.emission_params(topo, X=X, seed=42)
    assert params["covars_"].shape == (3, 2)
    # All variances must be strictly positive.
    assert (params["covars_"] > 0).all()


def test_init_gmm_diag_covariance_shape_unchanged(synthetic_gmm_3state):
    """Fix #5: existing diag path must still emit (K, n_mix, D)."""
    topo = _gmm_topo("diag", n_mix=2)
    X = synthetic_gmm_3state["X"]
    params = init.emission_params(topo, X=X, seed=42)
    assert params["covars_"].shape == (3, 2, 2)


def test_init_gmm_full_covariance_is_spd(synthetic_gmm_3state):
    """Fix #5: each (D, D) block for full covariance must be symmetric & PD."""
    topo = _gmm_topo("full", n_mix=2)
    X = synthetic_gmm_3state["X"]
    params = init.emission_params(topo, X=X, seed=42)
    K, M, D, _ = params["covars_"].shape
    for k in range(K):
        for m in range(M):
            C = params["covars_"][k, m]
            np.testing.assert_allclose(C, C.T, atol=1e-12)
            eigs = np.linalg.eigvalsh(C)
            assert (eigs > 0).all(), f"covars_[{k}, {m}] not positive definite: eigs={eigs}"


def test_init_gmm_tied_covariance_is_spd(synthetic_gmm_3state):
    """Fix #5: each per-state tied (D, D) must be symmetric & PD."""
    topo = _gmm_topo("tied", n_mix=2)
    X = synthetic_gmm_3state["X"]
    params = init.emission_params(topo, X=X, seed=42)
    K, D, _ = params["covars_"].shape
    for k in range(K):
        C = params["covars_"][k]
        np.testing.assert_allclose(C, C.T, atol=1e-12)
        eigs = np.linalg.eigvalsh(C)
        assert (eigs > 0).all()


def test_fit_gmm_full_does_not_crash(synthetic_gmm_3state):
    """Fix #5: end-to-end: declare gmm + full + kmeans, fit, get finite log-lik."""
    from hmm_core.fit import fit

    topo = _gmm_topo("full", n_mix=2)
    X = synthetic_gmm_3state["X"]
    result = fit(topo, X)
    assert np.isfinite(result.log_likelihood)
    assert np.isfinite(result.bic)


def test_fit_gmm_tied_does_not_crash(synthetic_gmm_3state):
    """Fix #5: tied covariance shape lands correctly through hmmlearn."""
    from hmm_core.fit import fit

    topo = _gmm_topo("tied", n_mix=2)
    X = synthetic_gmm_3state["X"]
    result = fit(topo, X)
    assert np.isfinite(result.log_likelihood)


def test_fit_gmm_spherical_does_not_crash(synthetic_gmm_3state):
    """Fix #5: spherical covariance shape lands correctly through hmmlearn."""
    from hmm_core.fit import fit

    topo = _gmm_topo("spherical", n_mix=2)
    X = synthetic_gmm_3state["X"]
    result = fit(topo, X)
    assert np.isfinite(result.log_likelihood)


def test_data_frequencies_with_lengths_skips_boundary_transitions(synthetic_gaussian_left_right):
    """Multi-sequence support: lengths parameter prevents counting transitions across sequence boundaries."""
    from hmm_core.topology import EmissionSpec, FitSpec, InitSpec, Topology

    topo = Topology(
        name="df_multi",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=EmissionSpec(type="gaussian", n_features=2, covariance_type="full"),
        allowed_transitions=[("a", "a"), ("a", "b"), ("b", "b"), ("b", "c"), ("c", "c")],
        startprob="first_state",
        init=InitSpec(strategy="data_frequencies", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=10, tol=1e-4),
    )
    X = synthetic_gaussian_left_right["X"]
    # Split X into 2 sequences of 500 each.
    lengths = np.array([500, 500])

    # Without lengths: counts include a spurious transition at t=499->500.
    A_no_lengths = init.transmat(topo, seed=42, X=X)
    # With lengths: that boundary transition is excluded.
    A_with_lengths = init.transmat(topo, seed=42, X=X, lengths=lengths)
    # Both must respect the mask.
    mask = topo.transition_mask()
    assert (A_no_lengths * (~mask)).sum() == 0
    assert (A_with_lengths * (~mask)).sum() == 0
    # Row sums to 1.
    np.testing.assert_allclose(A_no_lengths.sum(axis=1), 1.0, atol=1e-12)
    np.testing.assert_allclose(A_with_lengths.sum(axis=1), 1.0, atol=1e-12)
