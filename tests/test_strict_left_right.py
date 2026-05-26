"""Fix #6: smoothing startprob in _do_mstep prevents NaN on strict left-right.

With a strict left-right topology (state 0 never revisited after the first
timestep) and ``startprob='first_state'``, hmmlearn's M-step re-fits startprob
from the forward-backward responsibilities. The per-state responsibility sum
collapses to ~0 for never-revisited states and the normalisation produces 0/0
= NaN, which propagates to transmat/means and breaks the fit.

Each test fits a strict left-right model and asserts no NaN/Inf appears in any
parameter. We also assert the smoothing has no detectable effect on an ergodic
fit (within numerical precision).
"""

from __future__ import annotations

import numpy as np

from hmm_core.fit import fit
from hmm_core.fit.gaussian import ConstrainedGaussianHMM
from hmm_core.topology import (
    EmissionSpec,
    FitSpec,
    InitSpec,
    Topology,
)


def _strict_left_right_gaussian(startprob="first_state", covariance_type="full"):
    return Topology(
        name="lr3_strict",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=EmissionSpec(
            type="gaussian", n_features=2, covariance_type=covariance_type
        ),
        allowed_transitions=[
            ("a", "a"),
            ("a", "b"),
            ("b", "b"),
            ("b", "c"),
            ("c", "c"),
        ],
        startprob=startprob,
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=20, tol=1e-4),
    )


def _strict_left_right_gmm():
    return Topology(
        name="lr3_strict_gmm",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=EmissionSpec(
            type="gmm", n_features=2, covariance_type="diag", n_mix=2
        ),
        allowed_transitions=[
            ("a", "a"),
            ("a", "b"),
            ("b", "b"),
            ("b", "c"),
            ("c", "c"),
        ],
        startprob="first_state",
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=20, tol=1e-4),
    )


def test_strict_left_right_gaussian_no_nan(synthetic_gaussian_left_right):
    topo = _strict_left_right_gaussian()
    X = synthetic_gaussian_left_right["X"]
    result = fit(topo, X)
    sp = np.asarray(result.model.startprob_)
    A = np.asarray(result.model.transmat_)
    M = np.asarray(result.model.means_)
    assert np.isfinite(sp).all(), f"startprob has NaN/Inf: {sp}"
    assert np.isfinite(A).all(), f"transmat has NaN/Inf:\n{A}"
    assert np.isfinite(M).all(), f"means has NaN/Inf:\n{M}"
    assert np.isfinite(result.log_likelihood)


def test_strict_left_right_gmm_no_nan(synthetic_gmm_3state):
    topo = _strict_left_right_gmm()
    X = synthetic_gmm_3state["X"]
    result = fit(topo, X)
    sp = np.asarray(result.model.startprob_)
    A = np.asarray(result.model.transmat_)
    M = np.asarray(result.model.means_)
    W = np.asarray(result.model.weights_)
    assert np.isfinite(sp).all()
    assert np.isfinite(A).all()
    assert np.isfinite(M).all()
    assert np.isfinite(W).all()
    assert np.isfinite(result.log_likelihood)


def test_strict_left_right_startprob_within_simplex(synthetic_gaussian_left_right):
    """startprob must stay a valid probability vector through fitting."""
    topo = _strict_left_right_gaussian()
    X = synthetic_gaussian_left_right["X"]
    result = fit(topo, X)
    sp = np.asarray(result.model.startprob_)
    assert (sp >= 0).all(), f"startprob has negative entries: {sp}"
    assert sp.sum() == np.float64(sp.sum())  # not NaN
    np.testing.assert_allclose(sp.sum(), 1.0, atol=1e-10)


def test_smoothing_does_not_affect_ergodic_fit(synthetic_gaussian_left_right):
    """The eps=1e-12 smoothing must not perturb a healthy ergodic fit's log-likelihood.

    We re-fit twice with and without the smoothing helper (by monkey-patching
    _smooth_startprob_ to a no-op) and assert the log-likelihoods agree to
    1e-6 — the eps is so small that any honest fit shouldn't notice.
    """
    from hmm_core.fit import _base

    topo = Topology(
        name="ergodic_g3",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=EmissionSpec(type="gaussian", n_features=2, covariance_type="full"),
        allowed_transitions=None,  # ergodic
        startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=20, tol=1e-4),
    )
    X = synthetic_gaussian_left_right["X"]

    # With smoothing (default).
    r_with = fit(topo, X)
    ll_with = r_with.log_likelihood

    # Without smoothing: monkey-patch the helper to a no-op for one call.
    original = _base._smooth_startprob_
    _base._smooth_startprob_ = lambda model, eps=1e-12: None
    # Also re-patch the import sites — each Constrained*HMM imported the
    # symbol by name into its own module namespace.
    from hmm_core.fit import gaussian as _g

    original_g = _g._smooth_startprob_
    _g._smooth_startprob_ = lambda model, eps=1e-12: None
    try:
        r_no = fit(topo, X)
    finally:
        _base._smooth_startprob_ = original
        _g._smooth_startprob_ = original_g

    assert abs(ll_with - r_no.log_likelihood) < 1e-6


def test_strict_left_right_v1_cross_check_unaffected(synthetic_gaussian_left_right):
    """V.1-style cross-check : with mask=None, smoothing is invisible vs vanilla.

    The Fix #6 eps is small enough that even a model with mask=None (i.e.
    unconstrained) gives the same log-likelihood as vanilla hmmlearn within
    a few units of 1e-9. Guards against accidentally shifting the V.1 suite.
    """
    from hmmlearn.hmm import GaussianHMM

    X = synthetic_gaussian_left_right["X"]
    vanilla = GaussianHMM(
        n_components=3, covariance_type="full", n_iter=20, random_state=42
    )
    vanilla.fit(X)

    constrained = ConstrainedGaussianHMM(
        n_components=3,
        covariance_type="full",
        n_iter=20,
        random_state=42,
        transmat_mask=None,
    )
    constrained.fit(X)
    # Smoothing is so tiny that startprob agrees to better than 1e-9.
    np.testing.assert_allclose(constrained.startprob_, vanilla.startprob_, atol=1e-9)
    # Transmat unaffected.
    np.testing.assert_allclose(constrained.transmat_, vanilla.transmat_, atol=1e-10)
    # And so is the log-likelihood.
    assert abs(constrained.score(X) - vanilla.score(X)) < 1e-6
