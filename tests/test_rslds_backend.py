"""Full-tier slow tests for the rSLDS backend.

Gated by ``pytest.importorskip("ssm")`` AND ``@pytest.mark.slow`` — these tests
involve actual Laplace-EM fits (50 iters, 100+ obs) and run in ~1-3 minutes each.
Run only inside tools/docker/rslds.Dockerfile (the user's Windows host can't
install ssm)."""

from __future__ import annotations

import numpy as np
import pytest

ssm = pytest.importorskip("ssm")  # noqa: F841

from hmm_core.backends import get_backend
from hmm_core.backends._protocol import BackendFitResult
from hmm_core.backends.rslds_backend import RSLDSBackend, RSLDSFittedBundle
from hmm_core.topology import EmissionSpec, FitSpec, InitSpec, Topology


pytestmark = pytest.mark.slow


@pytest.fixture
def medium_X():
    rng = np.random.default_rng(0)
    return rng.normal(size=(150, 4)).astype(np.float64)


@pytest.fixture
def topology_k3_n50():
    return Topology(
        name="rslds_full",
        n_states=3,
        state_names=["s0", "s1", "s2"],
        emission=EmissionSpec(type="gaussian", n_features=4, covariance_type="full"),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="uniform", seed=0),
        fit=FitSpec(algorithm="baum_welch", n_iter=50, tol=1e-4),
    )


def _fit_kwargs(K: int) -> dict:
    return dict(
        seed=0, lengths=None,
        initial_transmat=np.full((K, K), 1.0 / K),
        initial_startprob=np.full(K, 1.0 / K),
        emission_kwargs={},
        mask=np.ones((K, K), dtype=bool),
    )


def test_rslds_plain_full_fit(medium_X, topology_k3_n50):
    """Plain SLDS path : 50-iter fit, verify result shape and ELBO finite."""
    backend = get_backend("rslds")
    assert backend.regularize == "none"
    result = backend.fit(topology_k3_n50, medium_X, **_fit_kwargs(3))
    assert isinstance(result, BackendFitResult)
    assert isinstance(result.model, RSLDSFittedBundle)
    assert np.isfinite(result.log_likelihood)
    assert result.n_iter_actual == 50


def test_rslds_elasticnet_full_fit(medium_X, topology_k3_n50):
    """Elastic-Net path : the shim must drive Laplace-EM without crashing.

    We also check that the dynamics matrices have at least some near-zero
    entries (a coarse sparsity sanity check; not a tight assertion because
    sparsity depends on alpha/l1_ratio and the data).

    Skipped when Nathan's ``ssm_extensions`` (Projet_Robin/ssm_extensions.py) is
    not on the Python path — it's an opt-in external dependency for the EN
    regularizer. The plain (regularize='none') path covers the core spike."""
    pytest.importorskip("ssm_extensions")
    backend = RSLDSBackend(regularize="elastic_net")
    result = backend.fit(topology_k3_n50, medium_X, **_fit_kwargs(3))
    bundle = result.model
    assert isinstance(bundle, RSLDSFittedBundle)
    assert bundle.regularize == "elastic_net"
    # Coarse: at least 10% of |A_k| entries are below 0.05 (regularization bites).
    frac_small = (np.abs(bundle.dynamics_As) < 0.05).mean()
    assert frac_small > 0.1, f"Expected ElasticNet sparsity, got frac_small={frac_small:.3f}"


def test_rslds_fit_supervised_not_implemented(medium_X, topology_k3_n50):
    backend = get_backend("rslds")
    states = np.zeros(len(medium_X), dtype=int)
    K = topology_k3_n50.n_states
    with pytest.raises(NotImplementedError, match="fit_supervised"):
        backend.fit_supervised(
            topology_k3_n50, medium_X, states,
            seed=0, lengths=None,
            mask=np.ones((K, K), dtype=bool),
        )


def test_rslds_decode_and_predict_proba_on_held_out(medium_X, topology_k3_n50):
    """decode and predict_proba must work on a fresh held-out sequence."""
    backend = get_backend("rslds")
    result = backend.fit(topology_k3_n50, medium_X[:100], **_fit_kwargs(3))

    held_out = medium_X[100:]  # 50 obs not seen at fit
    path = backend.decode(result.model, held_out)
    probs = backend.predict_proba(result.model, held_out)
    score = backend.score(result.model, held_out)

    K = topology_k3_n50.n_states
    assert path.shape == (50,)
    assert np.issubdtype(path.dtype, np.integer)
    assert path.min() >= 0 and path.max() < K
    assert probs.shape == (50, K)
    np.testing.assert_allclose(probs.sum(axis=1), 1.0, atol=1e-6)
    assert np.isfinite(score)


def test_rslds_score_docstring_marks_elbo_not_marginal():
    """The score docstring MUST explicitly warn that it returns ELBO, not the
    marginal log-likelihood — preventing accidental BIC/AIC comparisons."""
    backend = get_backend("rslds")
    doc = backend.score.__doc__ or ""
    assert "ELBO" in doc
    assert "marginal" in doc.lower()


def test_rslds_invalid_regularize_raises():
    with pytest.raises(ValueError, match="regularize"):
        RSLDSBackend(regularize="kendall")
