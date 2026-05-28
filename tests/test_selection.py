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
    mc = ModelComparison(
        candidates=[r],
        best_by_bic="gaussian K=2",
        best_by_aic="gaussian K=2",
        best_by_hqic="gaussian K=2",
    )
    assert mc.candidates[0].label == "gaussian K=2"


import warnings  # noqa: E402 — local test imports kept beside their consumers
from hmm_core.selection import compare_models  # noqa: E402


def _three_regime_data(seed=0):
    rng = np.random.default_rng(seed)
    return np.vstack(
        [
            rng.normal(-3.0, 0.4, (80, 1)),
            rng.normal(0.0, 0.4, (80, 1)),
            rng.normal(3.0, 0.4, (80, 1)),
        ]
    )


def test_compare_ranks_comparable_by_bic():
    X = _three_regime_data()
    cands = [TopologyCandidate(_gaussian_topo(f"g{k}", k)) for k in (2, 3, 4)]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cmp = compare_models(X, cands, seed=0)
    # all three are comparable Gaussian fits
    assert all(c.comparable for c in cmp.candidates)
    # best_by_bic is the label of the minimum-BIC candidate
    comparable = [c for c in cmp.candidates if c.error is None]
    expected = min(comparable, key=lambda c: c.bic).label
    assert cmp.best_by_bic == expected


def test_failed_candidate_excluded_not_fatal():
    X = _three_regime_data()
    # A multinomial spec on continuous (negative) float data -> the backend's
    # discrete-emission fit raises ("'list' argument must have no negative
    # elements"). A genuine fit failure, captured not fatal. (The plan's
    # original n_features mismatch did NOT raise against the hmmlearn backend.)
    bad = Topology(
        name="bad",
        n_states=2,
        state_names=["a", "b"],
        emission=EmissionSpec(type="multinomial", n_symbols=3),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=0),
        fit=FitSpec(algorithm="baum_welch", n_iter=10, tol=1e-3),
    )
    cands = [TopologyCandidate(_gaussian_topo("g2", 2)), TopologyCandidate(bad)]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cmp = compare_models(X, cands, seed=0)
    # the good one ranks; the bad one has an error and is excluded from best
    assert cmp.best_by_bic == "gaussian K=2"
    bad_result = [c for c in cmp.candidates if c.error is not None]
    assert len(bad_result) == 1
    assert np.isnan(bad_result[0].bic)


def test_nhmm_flagged_and_never_best():
    rng = np.random.default_rng(1)
    X = _three_regime_data(1)
    Z = rng.normal(0, 1, (len(X), 1))
    cands = [
        TopologyCandidate(_gaussian_topo("g3", 3)),
        NHMMCandidate(_gaussian_topo("nhmm3", 3), Z=Z, covariate_names=["z"]),
    ]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cmp = compare_models(X, cands, seed=0)
    nhmm = [c for c in cmp.candidates if c.kind == "nhmm"][0]
    assert nhmm.comparable is False
    assert nhmm.note and "P(X|Z)" in nhmm.note
    # best is always the comparable Gaussian, never the NHMM
    assert cmp.best_by_bic == "gaussian K=3"
    assert cmp.best_by_aic == "gaussian K=3"
    assert cmp.best_by_hqic == "gaussian K=3"


def test_factorial_flagged_not_comparable():
    from hmm_core.factorial_nhmm import FactorialChainSpec

    rng = np.random.default_rng(2)
    X = rng.normal(0, 1, (300, 2))
    chains = [FactorialChainSpec(name="a", n_states=2), FactorialChainSpec(name="b", n_states=2)]
    fc = FactorialCandidate(
        chains=chains,
        covariates_per_chain={"a": rng.normal(0, 1, (300, 1)), "b": rng.normal(0, 1, (300, 1))},
        emission=EmissionSpec(type="gaussian", covariance_type="diag", n_features=2),
    )
    cands = [TopologyCandidate(_gaussian_topo("g2", 2)), fc]
    # NOTE: g2 topo is 1-feature; make a 2-feature one to match X
    cands[0] = TopologyCandidate(
        Topology(
            name="g2d",
            n_states=2,
            state_names=["a", "b"],
            emission=EmissionSpec(type="gaussian", covariance_type="diag", n_features=2),
            allowed_transitions=None,
            startprob="uniform",
            init=InitSpec(strategy="kmeans", seed=0),
            fit=FitSpec(algorithm="baum_welch", n_iter=20, tol=1e-3),
        )
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cmp = compare_models(X, cands, seed=0)
    fac = [c for c in cmp.candidates if c.kind == "factorial"]
    assert len(fac) == 1
    assert fac[0].comparable is False
    assert fac[0].note and "joint" in fac[0].note.lower()


from hmm_core.selection import auto_grid  # noqa: E402 — local import kept beside its consumers


def test_auto_grid_generates_emission_x_k():
    base = _gaussian_topo("base", 3)
    grid = auto_grid(base, k_range=range(2, 5), emission_types=["gaussian", "gmm"], n_mix=2)
    # 3 K values x 2 emission types = 6 candidates
    assert len(grid) == 6
    assert all(isinstance(c, TopologyCandidate) for c in grid)
    ks = sorted({c.topology.n_states for c in grid})
    assert ks == [2, 3, 4]
    types = {c.topology.emission.type for c in grid}
    assert types == {"gaussian", "gmm"}
    # gmm candidates carry n_mix
    gmm = [c for c in grid if c.topology.emission.type == "gmm"]
    assert all(c.topology.emission.n_mix == 2 for c in gmm)


import json  # noqa: E402 — local import kept beside its consumers


def test_to_summary_dict_is_json_serialisable():
    X = _three_regime_data()
    cands = auto_grid(_gaussian_topo("base", 3), range(2, 4), ["gaussian"])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cmp = compare_models(X, cands, seed=0)
    d = cmp.to_summary_dict()
    assert "candidates" in d and "best_by_bic" in d
    assert len(d["candidates"]) == 2
    # round-trips through json
    json.loads(json.dumps(d))


def test_repr_html_marks_noncomparable():
    rng = np.random.default_rng(3)
    X = _three_regime_data(3)
    Z = rng.normal(0, 1, (len(X), 1))
    cands = [
        TopologyCandidate(_gaussian_topo("g3", 3)),
        NHMMCandidate(_gaussian_topo("nhmm3", 3), Z=Z, covariate_names=["z"]),
    ]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cmp = compare_models(X, cands, seed=0)
    html = cmp._repr_html_()
    assert isinstance(html, str) and len(html) > 50
    assert "<table" in html
    # the non-comparable row carries a visible marker
    assert "not directly comparable" in html or "⚠" in html


def test_top_level_exports():
    import hmm_core

    assert hasattr(hmm_core, "compare_models")
    assert hasattr(hmm_core, "auto_grid")
    assert hasattr(hmm_core, "ModelComparison")
    assert hasattr(hmm_core, "TopologyCandidate")
