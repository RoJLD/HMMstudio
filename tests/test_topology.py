"""Tests for Topology dataclass, validation, and transition_mask."""

from __future__ import annotations

import numpy as np
import pytest

from hmm_core.topology import (
    EmissionSpec,
    FitSpec,
    InitSpec,
    Topology,
    TopologyError,
)


def _gaussian_emission():
    return EmissionSpec(type="gaussian", n_features=2, covariance_type="full")


def _basic_init():
    return InitSpec(strategy="uniform", seed=42)


def _basic_fit():
    return FitSpec(algorithm="baum_welch", n_iter=50, tol=1e-4)


def test_ergodic_topology_has_all_true_mask():
    topo = Topology(
        name="test",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=_gaussian_emission(),
        allowed_transitions=None,
        startprob="uniform",
        init=_basic_init(),
        fit=_basic_fit(),
    )
    topo.validate()
    mask = topo.transition_mask()
    assert mask.shape == (3, 3)
    assert mask.all()


def test_explicit_allowed_transitions_mask():
    topo = Topology(
        name="left_right",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=_gaussian_emission(),
        allowed_transitions=[("a", "a"), ("a", "b"), ("b", "b"), ("b", "c"), ("c", "c")],
        startprob="first_state",
        init=_basic_init(),
        fit=_basic_fit(),
    )
    topo.validate()
    mask = topo.transition_mask()
    expected = np.array([[True, True, False], [False, True, True], [False, False, True]])
    np.testing.assert_array_equal(mask, expected)


def test_validation_rejects_mismatched_state_count():
    topo = Topology(
        name="bad",
        n_states=3,
        state_names=["a", "b"],
        emission=_gaussian_emission(),
        allowed_transitions=None,
        startprob="uniform",
        init=_basic_init(),
        fit=_basic_fit(),
    )
    with pytest.raises(TopologyError, match="state_names"):
        topo.validate()


def test_validation_rejects_unknown_state_in_transitions():
    topo = Topology(
        name="bad",
        n_states=2,
        state_names=["a", "b"],
        emission=_gaussian_emission(),
        allowed_transitions=[("a", "ghost")],
        startprob="uniform",
        init=_basic_init(),
        fit=_basic_fit(),
    )
    with pytest.raises(TopologyError, match="unknown state 'ghost'"):
        topo.validate()


def test_validation_rejects_gaussian_without_n_features():
    topo = Topology(
        name="bad",
        n_states=2,
        state_names=["a", "b"],
        emission=EmissionSpec(type="gaussian", n_features=None, covariance_type="full"),
        allowed_transitions=None,
        startprob="uniform",
        init=_basic_init(),
        fit=_basic_fit(),
    )
    with pytest.raises(TopologyError, match="n_features"):
        topo.validate()


def test_validation_rejects_multinomial_without_n_symbols():
    topo = Topology(
        name="bad",
        n_states=2,
        state_names=["a", "b"],
        emission=EmissionSpec(type="multinomial", n_symbols=None),
        allowed_transitions=None,
        startprob="uniform",
        init=_basic_init(),
        fit=_basic_fit(),
    )
    with pytest.raises(TopologyError, match="n_symbols"):
        topo.validate()


def test_startprob_list_must_match_n_states():
    topo = Topology(
        name="bad",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=_gaussian_emission(),
        allowed_transitions=None,
        startprob=[0.5, 0.5],  # length 2, should be 3
        init=_basic_init(),
        fit=_basic_fit(),
    )
    with pytest.raises(TopologyError, match="startprob"):
        topo.validate()
