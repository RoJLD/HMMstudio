"""Tests for the public fit() dispatcher."""

from __future__ import annotations

import numpy as np
import pytest

from hmm_core.fit import FittedModel, fit
from hmm_core.fit.gaussian import ConstrainedGaussianHMM
from hmm_core.topology import (
    EmissionSpec,
    FitSpec,
    InitSpec,
    Topology,
)


def _gaussian_left_right_topo():
    return Topology(
        name="lr3",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=EmissionSpec(type="gaussian", n_features=2, covariance_type="full"),
        allowed_transitions=[("a", "a"), ("a", "b"), ("b", "b"), ("b", "c"), ("c", "c")],
        startprob="first_state",
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=30, tol=1e-4),
    )


def test_fit_returns_fittedmodel(synthetic_gaussian_left_right):
    topo = _gaussian_left_right_topo()
    X = synthetic_gaussian_left_right["X"]
    result = fit(topo, X)
    assert isinstance(result, FittedModel)
    assert isinstance(result.model, ConstrainedGaussianHMM)
    assert result.topology is topo
    assert np.isfinite(result.log_likelihood)
    assert np.isfinite(result.bic)
    assert np.isfinite(result.aic)


def test_fit_mask_violation_below_threshold(synthetic_gaussian_left_right):
    topo = _gaussian_left_right_topo()
    X = synthetic_gaussian_left_right["X"]
    result = fit(topo, X)
    mask = topo.transition_mask()
    violation = (result.model.transmat_ * (~mask)).sum()
    assert violation < 1e-10, f"violation = {violation}"


def test_fit_seed_override():
    """seed=N must override topology.init.seed for the actual fit."""
    topo = _gaussian_left_right_topo()
    rng = np.random.default_rng(0)
    X = rng.normal(size=(500, 2))
    r1 = fit(topo, X, seed=1)
    r2 = fit(topo, X, seed=999)
    # Different seeds with kmeans init -> different starting clusters ->
    # different fitted means.
    assert not np.allclose(r1.model.means_, r2.model.means_)
    assert r1.seed == 1
    assert r2.seed == 999


def test_fit_seed_override_propagates_to_hmmlearn_random_state():
    """seed= overrides topology.init.seed for the underlying hmmlearn model's random_state.

    Even when the kmeans path masks all init_params, the hmmlearn model's
    random_state attribute should reflect the override, not the topology seed.
    """
    topo = _gaussian_left_right_topo()
    rng = np.random.default_rng(0)
    X = rng.normal(size=(500, 2))
    result = fit(topo, X, seed=777)
    assert result.model.random_state == 777
    assert topo.init.seed == 42  # topology unchanged
