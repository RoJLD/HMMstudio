"""Tests for the Bayesian HMM backend (Phase A.6).

These tests are **opt-in** : they require pymc, which is a soft optional
dependency. Each test calls ``pytest.importorskip("pymc")`` so the test
suite passes regardless of the install profile.

Coverage :
- Backend registers correctly when pymc is installed
- ``fit`` returns a valid ``BackendFitResult`` with finite log-likelihood
- Posterior means recover synthetic parameters within Bayesian tolerance
- ``decode`` / ``predict_proba`` / ``score`` work on the fitted model
- Scope validation : non-Gaussian emissions raise ``NotImplementedError``
- Scope validation : constrained mask raises ``NotImplementedError``
- ``last_idata_`` is populated after fit (arviz InferenceData)
"""

from __future__ import annotations

import numpy as np
import pytest

from hmm_core.fit import fit as core_fit
from hmm_core.topology import EmissionSpec, FitSpec, InitSpec, Topology

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def two_regime_data():
    """Two well-separated 1D Gaussian regimes — easy posterior recovery."""
    rng = np.random.default_rng(42)
    X = np.concatenate(
        [
            rng.normal(0.0, 0.5, (50, 1)),
            rng.normal(5.0, 0.5, (50, 1)),
            rng.normal(0.0, 0.5, (40, 1)),
            rng.normal(5.0, 0.5, (40, 1)),
        ]
    )
    return X


@pytest.fixture
def small_topology():
    return Topology(
        name="bayes_test",
        n_states=2,
        state_names=["a", "b"],
        emission=EmissionSpec(type="gaussian", covariance_type="diag", n_features=1),
        allowed_transitions=None,  # ergodic — required by MVP
        startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=10, tol=1e-3),
    )


# ---------------------------------------------------------------------------
# Registration & availability
# ---------------------------------------------------------------------------


def test_bayesian_backend_registered_when_pymc_available():
    """When pymc is installed, the bayesian backend appears in the registry."""
    pytest.importorskip("pymc", reason="pymc not installed")
    from hmm_core.backends import list_backends

    assert "bayesian" in list_backends()


def test_bayesian_backend_class_importable():
    pytest.importorskip("pymc", reason="pymc not installed")
    from hmm_core.backends import BayesianHMMBackend

    assert BayesianHMMBackend is not None
    backend = BayesianHMMBackend()
    assert backend.name == "bayesian"


# ---------------------------------------------------------------------------
# Basic fit & contract
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_bayesian_backend_fit_returns_valid_result(two_regime_data, small_topology):
    """fit() returns a BackendFitResult with finite log-likelihood and right shapes."""
    pytest.importorskip("pymc", reason="pymc not installed")
    from hmm_core.backends import BayesianHMMBackend

    backend = BayesianHMMBackend(n_samples=200, n_tune=100, n_chains=2)
    result = core_fit(small_topology, two_regime_data, seed=42, backend=backend)
    assert isinstance(result.model, object)
    assert np.isfinite(result.log_likelihood)
    assert result.model.transmat_.shape == (2, 2)
    assert result.model.means_.shape == (2, 1)


@pytest.mark.slow
def test_bayesian_backend_idata_populated_after_fit(two_regime_data, small_topology):
    """last_idata_ must contain a valid arviz InferenceData."""
    pytest.importorskip("pymc", reason="pymc not installed")
    import arviz as az
    from hmm_core.backends import BayesianHMMBackend

    backend = BayesianHMMBackend(n_samples=200, n_tune=100, n_chains=2)
    _ = core_fit(small_topology, two_regime_data, seed=42, backend=backend)

    idata = backend.last_idata_
    assert idata is not None
    assert isinstance(idata, az.InferenceData)
    # Posterior should have our 4 sampled groups : transmat, startprob, mus, sigmas
    for name in ["transmat", "startprob", "mus", "sigmas"]:
        assert name in idata.posterior.data_vars


@pytest.mark.slow
def test_bayesian_recovers_synthetic_means_within_tolerance(two_regime_data, small_topology):
    """Posterior mean of mus should be close to the true {0, 5}."""
    pytest.importorskip("pymc", reason="pymc not installed")
    from hmm_core.backends import BayesianHMMBackend

    backend = BayesianHMMBackend(n_samples=300, n_tune=200, n_chains=2)
    result = core_fit(small_topology, two_regime_data, seed=42, backend=backend)

    means = np.sort(np.asarray(result.model.means_).ravel())
    # True means are 0 and 5 — accept Bayesian uncertainty within 0.5
    assert means[0] == pytest.approx(0.0, abs=0.5)
    assert means[1] == pytest.approx(5.0, abs=0.5)


@pytest.mark.slow
def test_bayesian_decode_works_via_posterior_mean(two_regime_data, small_topology):
    """decode/predict_proba/score should work on the posterior-mean model."""
    pytest.importorskip("pymc", reason="pymc not installed")
    from hmm_core.backends import BayesianHMMBackend

    backend = BayesianHMMBackend(n_samples=200, n_tune=100, n_chains=2)
    result = core_fit(small_topology, two_regime_data, seed=42, backend=backend)

    # decode
    viterbi = backend.decode(result.model, two_regime_data)
    assert viterbi.shape == (len(two_regime_data),)
    assert set(np.unique(viterbi)).issubset({0, 1})

    # predict_proba
    posteriors = backend.predict_proba(result.model, two_regime_data)
    assert posteriors.shape == (len(two_regime_data), 2)
    np.testing.assert_allclose(posteriors.sum(axis=1), 1.0, atol=1e-9)

    # score
    lp = backend.score(result.model, two_regime_data)
    assert np.isfinite(lp)


# ---------------------------------------------------------------------------
# Scope validation (MVP limitations)
# ---------------------------------------------------------------------------


def test_bayesian_rejects_multinomial_emission(two_regime_data):
    """MVP supports only Gaussian — multinomial must raise clear NotImplementedError."""
    pytest.importorskip("pymc", reason="pymc not installed")
    from hmm_core.backends import BayesianHMMBackend

    topo = Topology(
        name="bayes_multinomial",
        n_states=2,
        state_names=["a", "b"],
        emission=EmissionSpec(type="multinomial", n_symbols=4),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="uniform", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=10, tol=1e-3),
    )
    X = np.array([[0], [1], [2], [3], [0]])

    backend = BayesianHMMBackend(n_samples=50, n_tune=50, n_chains=1)
    with pytest.raises(NotImplementedError, match="gaussian"):
        core_fit(topo, X, seed=42, backend=backend)


def test_bayesian_rejects_full_covariance(two_regime_data):
    """MVP supports only diagonal covariance — full / tied / spherical raise."""
    pytest.importorskip("pymc", reason="pymc not installed")
    from hmm_core.backends import BayesianHMMBackend

    topo = Topology(
        name="bayes_full",
        n_states=2,
        state_names=["a", "b"],
        emission=EmissionSpec(type="gaussian", covariance_type="full", n_features=1),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=10, tol=1e-3),
    )

    backend = BayesianHMMBackend(n_samples=50, n_tune=50, n_chains=1)
    with pytest.raises(NotImplementedError, match="diagonal"):
        core_fit(topo, two_regime_data, seed=42, backend=backend)


def test_bayesian_rejects_constrained_mask(two_regime_data):
    """MVP supports only ergodic — left-right etc. raise NotImplementedError."""
    pytest.importorskip("pymc", reason="pymc not installed")
    from hmm_core.backends import BayesianHMMBackend

    topo = Topology(
        name="bayes_left_right",
        n_states=2,
        state_names=["a", "b"],
        emission=EmissionSpec(type="gaussian", covariance_type="diag", n_features=1),
        allowed_transitions=[("a", "a"), ("a", "b"), ("b", "b")],  # left-right strict
        startprob="first_state",
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=10, tol=1e-3),
    )

    backend = BayesianHMMBackend(n_samples=50, n_tune=50, n_chains=1)
    with pytest.raises(NotImplementedError, match="ergodic"):
        core_fit(topo, two_regime_data, seed=42, backend=backend)


def test_bayesian_fit_supervised_not_implemented(two_regime_data, small_topology):
    """fit_supervised on Bayesian backend raises with a pointer to HmmlearnBackend."""
    pytest.importorskip("pymc", reason="pymc not installed")
    from hmm_core.backends import BayesianHMMBackend

    backend = BayesianHMMBackend()
    states = np.zeros(len(two_regime_data), dtype=int)
    with pytest.raises(NotImplementedError, match="HmmlearnBackend|supervised"):
        backend.fit_supervised(
            small_topology,
            two_regime_data,
            states,
            seed=42,
            lengths=None,
            mask=small_topology.transition_mask(),
        )


# ---------------------------------------------------------------------------
# Integration with the registry (Strategy A pattern)
# ---------------------------------------------------------------------------


def test_get_backend_bayesian_returns_instance():
    pytest.importorskip("pymc", reason="pymc not installed")
    from hmm_core.backends import get_backend

    backend = get_backend("bayesian")
    assert backend.name == "bayesian"


@pytest.mark.slow
def test_fit_dispatches_to_bayesian_by_name(two_regime_data, small_topology):
    """fit(topology, X, backend='bayesian') routes to the Bayesian backend."""
    pytest.importorskip("pymc", reason="pymc not installed")

    result = core_fit(
        small_topology,
        two_regime_data,
        seed=42,
        backend="bayesian",
    )
    assert np.isfinite(result.log_likelihood)
