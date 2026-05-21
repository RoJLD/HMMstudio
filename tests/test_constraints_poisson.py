"""Tests for ConstrainedPoissonHMM."""

from __future__ import annotations

import numpy as np

from hmm_core.fit import fit
from hmm_core.fit.poisson import ConstrainedPoissonHMM
from hmm_core.topology import (
    EmissionSpec,
    FitSpec,
    InitSpec,
    Topology,
)


def test_mask_zeros_preserved_after_fit(synthetic_poisson_3state):
    topo = Topology(
        name="pois_lr",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=EmissionSpec(type="poisson", n_features=2),
        allowed_transitions=[("a", "a"), ("a", "b"), ("b", "b"), ("b", "c"), ("c", "c")],
        startprob="first_state",
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=20, tol=1e-4),
    )
    result = fit(topo, synthetic_poisson_3state["X"])
    mask = topo.transition_mask()
    violation = (result.model.transmat_ * (~mask)).sum()
    assert violation < 1e-10
    np.testing.assert_allclose(result.model.transmat_.sum(axis=1), 1.0, atol=1e-10)


def test_mask_none_matches_vanilla(synthetic_poisson_3state):
    from hmmlearn.hmm import PoissonHMM

    X = synthetic_poisson_3state["X"]
    vanilla = PoissonHMM(n_components=3, n_iter=20, random_state=42)
    vanilla.fit(X)
    constrained = ConstrainedPoissonHMM(
        n_components=3, n_iter=20, random_state=42, transmat_mask=None,
    )
    constrained.fit(X)
    np.testing.assert_allclose(constrained.transmat_, vanilla.transmat_, atol=1e-10)
