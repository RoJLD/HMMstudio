"""Tests for ConstrainedMultinomialHMM."""

from __future__ import annotations

import numpy as np

from hmm_core.fit import fit
from hmm_core.fit.multinomial import ConstrainedMultinomialHMM
from hmm_core.topology import (
    EmissionSpec,
    FitSpec,
    InitSpec,
    Topology,
)


def test_mask_zeros_preserved_after_fit(synthetic_multinomial_3state):
    topo = Topology(
        name="mn_lr",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=EmissionSpec(type="multinomial", n_symbols=5),
        allowed_transitions=[("a", "a"), ("a", "b"), ("b", "b"), ("b", "c"), ("c", "c")],
        startprob="first_state",
        init=InitSpec(strategy="uniform", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=30, tol=1e-4),
    )
    result = fit(topo, synthetic_multinomial_3state["X"])
    mask = topo.transition_mask()
    violation = (result.model.transmat_ * (~mask)).sum()
    assert violation < 1e-10
    np.testing.assert_allclose(result.model.transmat_.sum(axis=1), 1.0, atol=1e-10)


def test_mask_none_matches_vanilla(synthetic_multinomial_3state):
    from hmmlearn.hmm import CategoricalHMM

    X = synthetic_multinomial_3state["X"]
    vanilla = CategoricalHMM(n_components=3, n_features=5, n_iter=30, random_state=42)
    vanilla.fit(X)
    constrained = ConstrainedMultinomialHMM(
        n_components=3,
        n_features=5,
        n_iter=30,
        random_state=42,
        transmat_mask=None,
    )
    constrained.fit(X)
    np.testing.assert_allclose(constrained.transmat_, vanilla.transmat_, atol=1e-10)
