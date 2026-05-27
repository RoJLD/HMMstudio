"""Fix #7: FitSpec.freeze_startprob / freeze_transmat clamp matrices through EM.

When set to True on the topology's ``fit:`` block, the corresponding parameter
is not re-fit by the backend's M-step ; whatever initial value the init
strategy produced (or a hand-crafted prior wired in via topology YAML) is
preserved across every EM iteration. Emission parameters are always re-fit.

These tests also cover the YAML loader extension and confirm the backend's
``params`` translation.
"""

from __future__ import annotations

import numpy as np

from hmm_core.fit import fit
from hmm_core.io import load_topology
from hmm_core.topology import (
    EmissionSpec,
    FitSpec,
    InitSpec,
    Topology,
)


def _gaussian_topo(
    *,
    startprob="first_state",
    freeze_startprob=False,
    freeze_transmat=False,
):
    return Topology(
        name="lr3_freeze",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=EmissionSpec(type="gaussian", n_features=2, covariance_type="diag"),
        allowed_transitions=[
            ("a", "a"),
            ("a", "b"),
            ("b", "b"),
            ("b", "c"),
            ("c", "c"),
        ],
        startprob=startprob,
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(
            algorithm="baum_welch",
            n_iter=20,
            tol=1e-4,
            freeze_startprob=freeze_startprob,
            freeze_transmat=freeze_transmat,
        ),
    )


def test_fitspec_freeze_defaults_false():
    """Default FitSpec must keep both freeze flags False."""
    fs = FitSpec(algorithm="baum_welch", n_iter=10, tol=1e-4)
    assert fs.freeze_startprob is False
    assert fs.freeze_transmat is False


def test_fitspec_freeze_from_yaml(tmp_path):
    """YAML loader: ``freeze_startprob: true`` lands on the FitSpec field."""
    yml = tmp_path / "freeze.yaml"
    yml.write_text(
        """
name: freeze_test
n_states: 3
state_names: [a, b, c]
emission:
  type: gaussian
  n_features: 2
  covariance_type: diag
allowed_transitions: null
startprob: uniform
init:
  strategy: uniform
  seed: 0
fit:
  algorithm: baum_welch
  n_iter: 10
  tol: 1.0e-4
  freeze_startprob: true
  freeze_transmat: true
""",
        encoding="utf-8",
    )
    topo = load_topology(yml)
    assert topo.fit.freeze_startprob is True
    assert topo.fit.freeze_transmat is True


def test_fitspec_freeze_yaml_defaults(tmp_path):
    """YAML omitting freeze keys must default to False (backward compat)."""
    yml = tmp_path / "default.yaml"
    yml.write_text(
        """
name: default_test
n_states: 2
state_names: [a, b]
emission:
  type: gaussian
  n_features: 1
  covariance_type: diag
allowed_transitions: null
startprob: uniform
init:
  strategy: uniform
  seed: 0
fit:
  algorithm: baum_welch
  n_iter: 10
  tol: 1.0e-4
""",
        encoding="utf-8",
    )
    topo = load_topology(yml)
    assert topo.fit.freeze_startprob is False
    assert topo.fit.freeze_transmat is False


def test_fit_with_freeze_startprob_preserves_initial_value(
    synthetic_gaussian_left_right,
):
    """startprob is set explicitly ; with freeze_startprob it must not move."""
    topo = Topology(
        name="freeze_sp",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=EmissionSpec(type="gaussian", n_features=2, covariance_type="diag"),
        allowed_transitions=None,
        startprob=[0.7, 0.2, 0.1],
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(
            algorithm="baum_welch",
            n_iter=20,
            tol=1e-4,
            freeze_startprob=True,
        ),
    )
    X = synthetic_gaussian_left_right["X"]
    result = fit(topo, X)
    np.testing.assert_allclose(
        result.model.startprob_, np.array([0.7, 0.2, 0.1]), atol=1e-12
    )


def test_fit_with_freeze_transmat_preserves_initial_mask_pattern(
    synthetic_gaussian_left_right,
):
    """transmat seeded by init is preserved exactly with freeze_transmat."""
    from hmm_core import init as init_mod

    topo = _gaussian_topo(freeze_transmat=True)
    X = synthetic_gaussian_left_right["X"]
    initial_A = init_mod.transmat(topo, seed=42, X=X)

    result = fit(topo, X)
    np.testing.assert_allclose(result.model.transmat_, initial_A, atol=1e-12)


def test_fit_with_freeze_both_still_updates_emissions(
    synthetic_gaussian_left_right,
):
    """Even with both transmat & startprob frozen, emissions must be updated."""
    from hmm_core import init as init_mod

    topo = _gaussian_topo(
        startprob=[0.7, 0.2, 0.1],
        freeze_startprob=True,
        freeze_transmat=True,
    )
    X = synthetic_gaussian_left_right["X"]
    initial_means = init_mod.emission_params(topo, X=X, seed=42)["means_"]

    result = fit(topo, X)
    # Startprob frozen exactly.
    np.testing.assert_allclose(
        result.model.startprob_, np.array([0.7, 0.2, 0.1]), atol=1e-12
    )
    # Means MUST have moved away from the kmeans init through EM.
    assert not np.allclose(result.model.means_, initial_means, atol=1e-4), (
        "means_ did not move through EM despite emission params not being frozen"
    )


def test_fit_without_freeze_startprob_does_move(synthetic_gaussian_left_right):
    """Sanity check: when not frozen, startprob CAN move during fit."""
    topo = Topology(
        name="no_freeze",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=EmissionSpec(type="gaussian", n_features=2, covariance_type="diag"),
        allowed_transitions=None,
        startprob=[0.7, 0.2, 0.1],
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(
            algorithm="baum_welch",
            n_iter=20,
            tol=1e-4,
            freeze_startprob=False,
        ),
    )
    X = synthetic_gaussian_left_right["X"]
    result = fit(topo, X)
    # Either it moved away from 0.7/0.2/0.1, or the fit was trivially short ;
    # for this fixture (1000 samples, 20 iters) it moves substantially.
    assert not np.allclose(
        result.model.startprob_, np.array([0.7, 0.2, 0.1]), atol=1e-3
    )


def test_fit_freeze_transmat_uses_hmmlearn_params_translation(
    synthetic_gaussian_left_right,
):
    """The fitted model's ``params`` attribute should not contain 't' when frozen."""
    topo = _gaussian_topo(freeze_transmat=True)
    X = synthetic_gaussian_left_right["X"]
    result = fit(topo, X)
    assert "t" not in result.model.params


def test_fit_freeze_startprob_uses_hmmlearn_params_translation(
    synthetic_gaussian_left_right,
):
    """The fitted model's ``params`` attribute should not contain 's' when frozen."""
    topo = _gaussian_topo(freeze_startprob=True)
    X = synthetic_gaussian_left_right["X"]
    result = fit(topo, X)
    assert "s" not in result.model.params
