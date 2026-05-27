# tests/test_selection.py
from __future__ import annotations

import numpy as np

from hmm_core.selection import (
    TopologyCandidate,
    NHMMCandidate,
    FactorialCandidate,
    CandidateResult,
    ModelComparison,
)
from hmm_core.topology import EmissionSpec, FitSpec, InitSpec, Topology


def _gaussian_topo(name: str, k: int) -> Topology:
    return Topology(
        name=name,
        n_states=k,
        state_names=[f"s{i}" for i in range(k)],
        emission=EmissionSpec(type="gaussian", covariance_type="diag", n_features=1),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=0),
        fit=FitSpec(algorithm="baum_welch", n_iter=30, tol=1e-3),
    )


def test_candidate_dataclasses_construct():
    c = TopologyCandidate(topology=_gaussian_topo("g2", 2))
    assert c.topology.n_states == 2
    # CandidateResult is a plain record; comparable defaults are explicit
    r = CandidateResult(
        label="gaussian K=2",
        kind="gaussian",
        fitted=None,
        log_likelihood=-10.0,
        bic=30.0,
        aic=25.0,
        hqic=27.0,
        n_params=5,
        comparable=True,
        note=None,
        error=None,
    )
    assert r.comparable is True
    mc = ModelComparison(candidates=[r], best_by_bic="gaussian K=2", best_by_aic="gaussian K=2", best_by_hqic="gaussian K=2")
    assert mc.candidates[0].label == "gaussian K=2"
