"""Tests for the HMMBackend abstraction layer."""

from __future__ import annotations

import numpy as np
import pytest

from hmm_core.backends import (
    BackendFitResult,
    HMMBackend,
    HmmlearnBackend,
    get_backend,
    list_backends,
    register_backend,
)
from hmm_core.fit import fit
from hmm_core.topology import EmissionSpec, FitSpec, InitSpec, Topology


def _gaussian_topology() -> Topology:
    return Topology(
        name="test",
        n_states=2,
        state_names=["a", "b"],
        emission=EmissionSpec(type="gaussian", covariance_type="diag", n_features=1),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="uniform", seed=0),
        fit=FitSpec(algorithm="baum_welch", n_iter=5, tol=1e-3),
    )


def _toy_data(seed: int = 0, n: int = 30) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return np.concatenate([rng.normal(0, 1, n), rng.normal(5, 1, n)]).reshape(-1, 1)


def test_default_backend_is_hmmlearn():
    backend = get_backend()
    assert backend.name == "hmmlearn"
    assert isinstance(backend, HmmlearnBackend)


def test_get_backend_by_name():
    assert get_backend("hmmlearn").name == "hmmlearn"


def test_get_backend_unknown_raises():
    with pytest.raises(ValueError, match="unknown HMM backend"):
        get_backend("does-not-exist")


def test_list_backends_contains_hmmlearn():
    assert "hmmlearn" in list_backends()


def test_hmmlearn_backend_satisfies_protocol():
    # runtime_checkable Protocol — duck-type the interface.
    assert isinstance(HmmlearnBackend(), HMMBackend)


def test_fit_accepts_backend_string():
    topo = _gaussian_topology()
    X = _toy_data()
    result = fit(topo, X, backend="hmmlearn")
    assert result.converged or result.n_iter_actual == topo.fit.n_iter
    assert result.model is not None


def test_fit_accepts_backend_instance():
    topo = _gaussian_topology()
    X = _toy_data()
    result = fit(topo, X, backend=HmmlearnBackend())
    assert result.model is not None


def test_fit_default_backend_equivalent_to_explicit():
    topo = _gaussian_topology()
    X = _toy_data()
    a = fit(topo, X)
    b = fit(topo, X, backend="hmmlearn")
    assert a.log_likelihood == pytest.approx(b.log_likelihood)


def test_register_custom_backend_and_use_via_fit():
    """A user can plug in a third-party backend and fit() will route to it."""
    calls: dict[str, int] = {"fit": 0}

    class FakeBackend:
        name = "fake"

        def fit(
            self,
            topology,
            X,
            *,
            seed,
            lengths,
            initial_transmat,
            initial_startprob,
            emission_kwargs,
            mask,
            **kwargs,  # forward-compat: accept future protocol kwargs (progress_callback, etc.)
        ):
            calls["fit"] += 1
            return BackendFitResult(
                model=object(),
                transmat=initial_transmat,
                startprob=initial_startprob,
                log_likelihood=-123.0,
                n_iter_actual=1,
                converged=True,
            )

        def decode(self, model, X, lengths=None):  # pragma: no cover
            return np.zeros(len(X), dtype=int)

        def predict_proba(self, model, X, lengths=None):  # pragma: no cover
            return np.zeros((len(X), 2))

        def score(self, model, X, lengths=None):  # pragma: no cover
            return -123.0

    register_backend("fake", FakeBackend)
    try:
        result = fit(_gaussian_topology(), _toy_data(), backend="fake")
        assert calls["fit"] == 1
        assert result.log_likelihood == -123.0
        assert result.converged is True
    finally:
        # Re-register hmmlearn as default to avoid leaking state to other tests.
        register_backend("hmmlearn", HmmlearnBackend, default=True)


def test_backend_decode_and_score_roundtrip():
    backend = get_backend("hmmlearn")
    topo = _gaussian_topology()
    X = _toy_data()
    result = fit(topo, X)
    states = backend.decode(result.model, X)
    assert states.shape == (len(X),)
    assert set(np.unique(states)).issubset({0, 1})

    lp = backend.score(result.model, X)
    assert lp == pytest.approx(result.log_likelihood)

    posteriors = backend.predict_proba(result.model, X)
    assert posteriors.shape == (len(X), topo.n_states)
    assert np.allclose(posteriors.sum(axis=1), 1.0)
