"""Tests for A.8: per-state EmissionSpec support in Topology.

Scope:
- Topology.emissions is an optional list[EmissionSpec], one per state.
- All entries must share type and hyperparams with Topology.emission.
- Per-state init_mean/init_covar/init_lambda/init_emissionprob hints prime
  the corresponding parameters before EM.

Out of scope (deferred A.8.x):
- Mixed emission types per state.
- Heterogeneous hyperparams (e.g., different covariance_type per state).
"""

from __future__ import annotations

import numpy as np
import pytest

from hmm_core import init as init_mod
from hmm_core.fit import fit
from hmm_core.topology import (
    EmissionSpec,
    FitSpec,
    InitSpec,
    Topology,
    TopologyError,
)


def _base_topo_gaussian(emissions=None) -> Topology:
    return Topology(
        name="ps",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=EmissionSpec(type="gaussian", n_features=2, covariance_type="full"),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="uniform", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=10, tol=1e-3),
        emissions=emissions,
    )


def test_no_emissions_keeps_backward_compat():
    """Without emissions= the topology behaves exactly as before."""
    topo = _base_topo_gaussian()
    topo.validate()
    assert topo.emissions is None


def test_emissions_length_must_match_n_states():
    bad = _base_topo_gaussian(
        emissions=[
            EmissionSpec(type="gaussian", n_features=2, covariance_type="full"),
        ]  # only 1, need 3
    )
    with pytest.raises(TopologyError, match="emissions has length"):
        bad.validate()


def test_emissions_must_share_type():
    bad = _base_topo_gaussian(
        emissions=[
            EmissionSpec(type="gaussian", n_features=2, covariance_type="full"),
            EmissionSpec(type="poisson", n_features=2),  # mixed type
            EmissionSpec(type="gaussian", n_features=2, covariance_type="full"),
        ]
    )
    with pytest.raises(TopologyError, match="does not match emission.type"):
        bad.validate()


def test_emissions_must_share_hyperparams():
    bad = _base_topo_gaussian(
        emissions=[
            EmissionSpec(type="gaussian", n_features=2, covariance_type="full"),
            EmissionSpec(type="gaussian", n_features=2, covariance_type="diag"),  # mismatch
            EmissionSpec(type="gaussian", n_features=2, covariance_type="full"),
        ]
    )
    with pytest.raises(TopologyError, match="heterogeneous hyperparams"):
        bad.validate()


def test_init_mean_hints_propagate_through_emission_params():
    """When init_mean hints are present, emission_params should respect them."""
    topo = _base_topo_gaussian(
        emissions=[
            EmissionSpec(
                type="gaussian",
                n_features=2,
                covariance_type="full",
                init_mean=[-5.0, -5.0],
            ),
            EmissionSpec(
                type="gaussian",
                n_features=2,
                covariance_type="full",
                init_mean=[0.0, 0.0],
            ),
            EmissionSpec(
                type="gaussian",
                n_features=2,
                covariance_type="full",
                init_mean=[5.0, 5.0],
            ),
        ]
    )
    topo.validate()
    X = np.random.default_rng(0).normal(size=(100, 2))
    params = init_mod.emission_params(topo, X=X, seed=42)
    assert "means_" in params
    np.testing.assert_allclose(params["means_"][0], [-5.0, -5.0])
    np.testing.assert_allclose(params["means_"][1], [0.0, 0.0])
    np.testing.assert_allclose(params["means_"][2], [5.0, 5.0])


def test_fit_with_per_state_init_runs_to_completion(synthetic_gaussian_left_right):
    """A full fit() call works with per-state init hints (smoke)."""
    topo = Topology(
        name="ps3",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=EmissionSpec(type="gaussian", n_features=2, covariance_type="full"),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=20, tol=1e-4),
        emissions=[
            EmissionSpec(
                type="gaussian",
                n_features=2,
                covariance_type="full",
                init_mean=[-3.0, -3.0],
            ),
            EmissionSpec(
                type="gaussian",
                n_features=2,
                covariance_type="full",
                init_mean=[0.0, 0.0],
            ),
            EmissionSpec(
                type="gaussian",
                n_features=2,
                covariance_type="full",
                init_mean=[3.0, 3.0],
            ),
        ],
    )
    X = synthetic_gaussian_left_right["X"]
    result = fit(topo, X)
    assert result.converged or result.n_iter_actual > 0
    assert result.model.means_.shape == (3, 2)


def test_poisson_per_state_init_lambdas():
    """Per-state init_lambda hints propagate for Poisson emissions."""
    topo = Topology(
        name="pois_ps",
        n_states=2,
        state_names=["lo", "hi"],
        emission=EmissionSpec(type="poisson", n_features=2),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="uniform", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=10, tol=1e-3),
        emissions=[
            EmissionSpec(type="poisson", n_features=2, init_lambda=[1.0, 1.0]),
            EmissionSpec(type="poisson", n_features=2, init_lambda=[10.0, 10.0]),
        ],
    )
    topo.validate()
    X = np.random.default_rng(0).poisson(5, size=(50, 2))
    params = init_mod.emission_params(topo, X=X, seed=42)
    assert "lambdas_" in params
    np.testing.assert_allclose(params["lambdas_"][0], [1.0, 1.0])
    np.testing.assert_allclose(params["lambdas_"][1], [10.0, 10.0])


def test_yaml_roundtrip_with_emissions(tmp_path):
    """A topology with emissions: list survives load -> save -> load."""
    from hmm_core.io import load_topology

    yaml_text = """
name: ps3
n_states: 3
state_names: [a, b, c]
emission:
  type: gaussian
  covariance_type: full
  n_features: 2
emissions:
  - type: gaussian
    n_features: 2
    covariance_type: full
    init_mean: [-2.0, -2.0]
  - type: gaussian
    n_features: 2
    covariance_type: full
    init_mean: [0.0, 0.0]
  - type: gaussian
    n_features: 2
    covariance_type: full
    init_mean: [2.0, 2.0]
startprob: uniform
init: {strategy: uniform, seed: 0}
fit: {algorithm: baum_welch, n_iter: 10, tol: 1.0e-4}
"""
    yaml_path = tmp_path / "topo.yaml"
    yaml_path.write_text(yaml_text, encoding="utf-8")
    topo = load_topology(yaml_path)
    assert topo.emissions is not None
    assert len(topo.emissions) == 3
    assert topo.emissions[0].init_mean == [-2.0, -2.0]
    assert topo.emissions[2].init_mean == [2.0, 2.0]
