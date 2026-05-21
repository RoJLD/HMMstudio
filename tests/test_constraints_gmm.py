"""Tests for ConstrainedGMMHMM."""

from __future__ import annotations

import numpy as np

from hmm_core.fit import fit
from hmm_core.fit.gmm import ConstrainedGMMHMM
from hmm_core.topology import (
    EmissionSpec,
    FitSpec,
    InitSpec,
    Topology,
)


def test_mask_zeros_preserved_after_fit(synthetic_gmm_3state):
    topo = Topology(
        name="gmm_lr",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=EmissionSpec(type="gmm", n_features=2, covariance_type="diag", n_mix=2),
        allowed_transitions=[("a", "a"), ("a", "b"), ("b", "b"), ("b", "c"), ("c", "c")],
        startprob="first_state",
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=20, tol=1e-3),
    )
    result = fit(topo, synthetic_gmm_3state["X"])
    mask = topo.transition_mask()
    violation = (result.model.transmat_ * (~mask)).sum()
    assert violation < 1e-10
    np.testing.assert_allclose(result.model.transmat_.sum(axis=1), 1.0, atol=1e-10)


def test_mask_none_matches_vanilla(synthetic_gmm_3state):
    from hmmlearn.hmm import GMMHMM

    X = synthetic_gmm_3state["X"]
    vanilla = GMMHMM(n_components=3, n_mix=2, covariance_type="diag",
                     n_iter=10, random_state=42)
    vanilla.fit(X)
    constrained = ConstrainedGMMHMM(n_components=3, n_mix=2, covariance_type="diag",
                                     n_iter=10, random_state=42, transmat_mask=None)
    constrained.fit(X)
    np.testing.assert_allclose(constrained.transmat_, vanilla.transmat_, atol=1e-10)
