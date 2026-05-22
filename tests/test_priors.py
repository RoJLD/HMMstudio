"""Tests for A.9: Dirichlet priors on transitions (MAP smoothing)."""

from __future__ import annotations

import numpy as np
import pytest

from hmm_core.fit import fit
from hmm_core.fit._base import _map_update
from hmm_core.topology import (
    EmissionSpec,
    FitSpec,
    InitSpec,
    Topology,
    TopologyError,
)


def _topo_with_prior(alpha=None, matrix=None, allowed=None):
    return Topology(
        name="prior",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=EmissionSpec(type="gaussian", n_features=2, covariance_type="full"),
        allowed_transitions=allowed,
        startprob="uniform",
        init=InitSpec(strategy="uniform", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=10, tol=1e-4),
        transmat_prior_alpha=alpha,
        transmat_prior_matrix=matrix,
    )


def test_no_prior_keeps_backward_compat():
    topo = _topo_with_prior()
    topo.validate()
    assert topo.transmat_prior() is None


def test_prior_alpha_uniform_on_allowed_edges():
    topo = _topo_with_prior(alpha=2.0)
    topo.validate()
    prior = topo.transmat_prior()
    assert prior.shape == (3, 3)
    np.testing.assert_allclose(prior, 2.0 * np.ones((3, 3)))


def test_prior_alpha_zeros_forbidden_edges():
    topo = _topo_with_prior(alpha=2.0, allowed=[("a", "a"), ("b", "b"), ("c", "c")])
    topo.validate()
    prior = topo.transmat_prior()
    expected = 2.0 * np.eye(3)
    np.testing.assert_allclose(prior, expected)


def test_prior_matrix_overrides_alpha():
    matrix = [[1.0, 5.0, 0.0], [0.0, 1.0, 5.0], [5.0, 0.0, 1.0]]
    topo = _topo_with_prior(alpha=2.0, matrix=matrix)
    topo.validate()
    prior = topo.transmat_prior()
    np.testing.assert_allclose(prior, np.array(matrix))


def test_prior_matrix_must_be_correct_shape():
    bad = _topo_with_prior(matrix=[[1.0, 1.0]])  # 1x2, should be 3x3
    with pytest.raises(TopologyError, match="must be 3"):
        bad.validate()


def test_prior_matrix_must_be_non_negative():
    bad = _topo_with_prior(matrix=[[1.0, 1.0, 1.0], [-1.0, 1.0, 1.0], [1.0, 1.0, 1.0]])
    with pytest.raises(TopologyError, match=">= 0"):
        bad.validate()


def test_prior_alpha_must_be_non_negative():
    bad = _topo_with_prior(alpha=-0.5)
    with pytest.raises(TopologyError, match=">= 0"):
        bad.validate()


def test_map_update_no_prior_is_identity():
    A = np.array([[0.5, 0.5], [0.3, 0.7]])
    mask = np.ones((2, 2), dtype=bool)
    out = _map_update(A, None, mask)
    np.testing.assert_allclose(out, A)


def test_map_update_uniform_prior_smoothes_toward_uniform():
    """Strong uniform prior (alpha=100) should pull a peaked row toward uniform."""
    A = np.array([[0.99, 0.01], [0.5, 0.5]])
    mask = np.ones((2, 2), dtype=bool)
    prior = 100.0 * np.ones((2, 2))
    out = _map_update(A, prior, mask)
    # Row 0 should be much less peaked
    assert out[0, 0] < 0.99
    assert out[0, 1] > 0.01
    # Row 1 already uniform, stays roughly uniform
    np.testing.assert_allclose(out[1], [0.5, 0.5], atol=0.05)
    # Rows still sum to 1
    np.testing.assert_allclose(out.sum(axis=1), 1.0)


def test_map_update_respects_mask():
    A = np.array([[0.5, 0.5], [0.5, 0.5]])
    mask = np.array([[True, False], [True, True]])
    prior = np.array([[2.0, 2.0], [2.0, 2.0]])  # prior says edge (0,1) allowed but mask forbids
    out = _map_update(A, prior, mask)
    assert out[0, 1] == 0.0  # forbidden by mask, must stay zero
    np.testing.assert_allclose(out.sum(axis=1), 1.0)


def test_fit_with_prior_alpha_runs(synthetic_gaussian_left_right):
    topo = _topo_with_prior(alpha=1.5)
    X = synthetic_gaussian_left_right["X"]
    result = fit(topo, X)
    # Smoke: fit completes
    assert result.log_likelihood is not None
    # Result still respects mask (trivial here since topo is ergodic)
    assert result.model.transmat_.shape == (3, 3)


def test_yaml_roundtrip_with_prior(tmp_path):
    from hmm_core.io import load_topology

    yaml_text = """
name: prior_test
n_states: 3
state_names: [a, b, c]
emission:
  type: gaussian
  covariance_type: full
  n_features: 2
startprob: uniform
init: {strategy: uniform, seed: 0}
fit: {algorithm: baum_welch, n_iter: 10, tol: 1.0e-4}
transmat_prior_alpha: 2.5
"""
    yaml_path = tmp_path / "topo.yaml"
    yaml_path.write_text(yaml_text, encoding="utf-8")
    topo = load_topology(yaml_path)
    assert topo.transmat_prior_alpha == 2.5
    assert topo.transmat_prior_matrix is None
    prior = topo.transmat_prior()
    np.testing.assert_allclose(prior, 2.5 * np.ones((3, 3)))
