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


def test_fit_progress_callback_receives_intermediate_history(synthetic_gaussian_left_right):
    """progress_callback receives the monitor_.history list mid-fit."""
    topo = _gaussian_left_right_topo()
    X = synthetic_gaussian_left_right["X"]
    received = []

    def callback(history):
        received.append(list(history))

    fit(topo, X, progress_callback=callback)
    # We should have at least one mid-flight callback invocation, and the
    # final history should contain multiple log-likelihoods.
    assert len(received) >= 1
    last = received[-1]
    assert len(last) > 0


# ---------------------------------------------------------------------------
# Fix #3 : FittedModel.to_summary_dict / .to_summary_json
# ---------------------------------------------------------------------------


def test_fitted_model_to_summary_dict_basic_gaussian(synthetic_gaussian_left_right):
    """to_summary_dict() returns the expected keys / types for a Gaussian fit."""
    topo = _gaussian_left_right_topo()
    X = synthetic_gaussian_left_right["X"]
    result = fit(topo, X)

    d = result.to_summary_dict()
    expected_keys = {
        "topology_name",
        "n_states",
        "emission_type",
        "n_features",
        "n_mix",
        "covariance_type",
        "log_likelihood",
        "bic",
        "aic",
        "hqic",
        "n_obs",
        "n_iter_actual",
        "converged",
        "n_params",
        "seed",
        "duration_seconds",
    }
    assert set(d.keys()) == expected_keys

    assert isinstance(d["topology_name"], str)
    assert d["topology_name"] == "lr3"
    assert isinstance(d["n_states"], int)
    assert d["n_states"] == 3
    assert d["emission_type"] == "gaussian"
    assert d["n_features"] == 2
    assert d["n_mix"] is None
    assert d["covariance_type"] == "full"
    assert isinstance(d["log_likelihood"], float)
    assert isinstance(d["bic"], float)
    assert isinstance(d["aic"], float)
    assert isinstance(d["hqic"], float)
    assert isinstance(d["n_obs"], int)
    assert d["n_obs"] == len(X)
    assert isinstance(d["n_iter_actual"], int)
    assert isinstance(d["converged"], bool)
    assert isinstance(d["n_params"], int)
    assert d["n_params"] > 0
    assert isinstance(d["seed"], int)
    assert isinstance(d["duration_seconds"], float)


def test_hqic_ordering_between_aic_and_bic(synthetic_gaussian_left_right):
    """HQIC penalty sits between AIC and BIC for any n_obs >= 16.

    AIC penalty = 2k ; HQIC = 2k·ln(ln n) ; BIC = k·ln n. For ln(ln n) in
    (1, ln n / 2) — i.e. roughly 16 <= n — the HQIC penalty is strictly
    between the AIC and BIC penalties, so the same ordering holds on the
    scores (all share the -2·LL term).
    """
    topo = _gaussian_left_right_topo()
    X = synthetic_gaussian_left_right["X"]  # n = 1000 >> 16
    result = fit(topo, X)
    assert result.n_obs == len(X)
    # All three are -2LL + penalty ; penalty_aic < penalty_hqic < penalty_bic
    assert result.aic < result.hqic < result.bic
    # And HQIC is finite
    assert np.isfinite(result.hqic)


def test_fitted_model_to_summary_dict_converged_flag_matches_real_fit(
    synthetic_gaussian_left_right,
):
    """The converged + n_iter_actual fields must mirror the monitor_'s state.

    We compare the dict's flags against the FittedModel's own attributes (which
    in turn are sourced from hmmlearn's monitor_), so the dict is the single
    source of truth for downstream consumers.
    """
    topo = Topology(
        name="short",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=EmissionSpec(type="gaussian", n_features=2, covariance_type="full"),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=2, tol=1e-12),
    )
    X = synthetic_gaussian_left_right["X"]
    result = fit(topo, X)
    d = result.to_summary_dict()
    assert d["converged"] == result.converged
    assert d["n_iter_actual"] == result.n_iter_actual
    assert isinstance(d["n_iter_actual"], int)
    assert isinstance(d["converged"], bool)


def test_to_summary_json_round_trips_through_loads(synthetic_gaussian_left_right):
    """to_summary_json() output parses back into the same dict via json.loads."""
    import json

    topo = _gaussian_left_right_topo()
    X = synthetic_gaussian_left_right["X"]
    result = fit(topo, X)

    js = result.to_summary_json()
    parsed = json.loads(js)
    direct = result.to_summary_dict()
    # JSON doesn't preserve None vs absent ; check that every key matches.
    assert set(parsed.keys()) == set(direct.keys())
    for k, v in direct.items():
        if isinstance(v, float):
            assert parsed[k] == pytest.approx(v)
        else:
            assert parsed[k] == v


def test_nhmm_to_summary_dict_includes_covariates(synthetic_nhmm_data):
    """Fix #3 (NHMM): summary dict adds covariate_names + n_covariates on top."""
    from hmm_core.nhmm import fit_nhmm

    topo = Topology(
        name="nhmm_summary",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=EmissionSpec(type="gaussian", n_features=2, covariance_type="full"),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=15, tol=1e-4),
    )
    result = fit_nhmm(
        topo,
        synthetic_nhmm_data["X"],
        synthetic_nhmm_data["Z"],
        covariate_names=["z"],
        seed=42,
    )
    d = result.to_summary_dict()
    # Base fields all present.
    assert "log_likelihood" in d
    assert "bic" in d
    assert d["topology_name"] == "nhmm_summary"
    # NHMM-specific.
    assert d["covariate_names"] == ["z"]
    assert d["n_covariates"] == 1
    assert d["T"] == len(synthetic_nhmm_data["X"])
    assert "n_classifiers" in d
    assert "n_fallback_rows" in d


def test_gmm_nhmm_to_summary_dict_includes_n_mix_and_covariates(
    synthetic_gmm_nhmm_data,
):
    """Fix #3 (GMM-NHMM): summary adds covariate_names + n_mix."""
    from hmm_core.gmm_nhmm import fit_gmm_nhmm

    topo = Topology(
        name="gmm_nhmm_summary",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=EmissionSpec(type="gmm", n_features=2, covariance_type="diag", n_mix=2),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=15, tol=1e-4),
    )
    result = fit_gmm_nhmm(
        topo,
        synthetic_gmm_nhmm_data["X"],
        synthetic_gmm_nhmm_data["Z"],
        covariate_names=["z"],
        seed=42,
    )
    d = result.to_summary_dict()
    assert d["covariate_names"] == ["z"]
    assert d["n_covariates"] == 1
    assert d["n_mix"] == 2
    assert d["emission_type"] == "gmm"


def test_factorial_nhmm_to_summary_dict_includes_chains(synthetic_gaussian_left_right):
    """Fix #3 (Factorial NHMM): summary adds chain_names / K_per_chain / K_joint."""
    from hmm_core.factorial_nhmm import (
        FactorialChainSpec,
        fit_factorial_nhmm,
    )

    rng = np.random.default_rng(0)
    T = 600
    X = rng.normal(size=(T, 2))
    chains = [
        FactorialChainSpec(name="trend", n_states=2),
        FactorialChainSpec(name="vol", n_states=2),
    ]
    covariates = {
        "trend": rng.normal(size=(T, 1)),
        "vol": rng.normal(size=(T, 1)),
    }
    emission = EmissionSpec(type="gaussian", n_features=2, covariance_type="diag")
    result = fit_factorial_nhmm(
        chains,
        X,
        covariates,
        emission=emission,
        covariate_names_per_chain={"trend": ["zt"], "vol": ["zv"]},
        seed=42,
    )
    d = result.to_summary_dict()
    assert d["chain_names"] == ["trend", "vol"]
    assert d["K_per_chain"] == [2, 2]
    assert d["K_joint"] == 4
    assert d["n_chains"] == 2
    assert d["T"] == T
    assert "chain_covariate_names" in d
    assert d["chain_covariate_names"]["trend"] == ["zt"]


def test_to_summary_json_factorial_nhmm_round_trips(synthetic_gaussian_left_right):
    """JSON wrapper on FactorialNHMM round-trips correctly (covers nested dict serialisation)."""
    import json

    from hmm_core.factorial_nhmm import (
        FactorialChainSpec,
        fit_factorial_nhmm,
    )

    rng = np.random.default_rng(0)
    T = 400
    X = rng.normal(size=(T, 2))
    chains = [FactorialChainSpec(name="c1", n_states=2)]
    covariates = {"c1": rng.normal(size=(T, 1))}
    emission = EmissionSpec(type="gaussian", n_features=2, covariance_type="diag")
    result = fit_factorial_nhmm(
        chains,
        X,
        covariates,
        emission=emission,
        covariate_names_per_chain={"c1": ["z"]},
        seed=42,
    )
    js = result.to_summary_json()
    parsed = json.loads(js)
    assert parsed["chain_names"] == ["c1"]
    assert parsed["K_per_chain"] == [2]
    assert parsed["K_joint"] == 2
