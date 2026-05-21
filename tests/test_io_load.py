"""Tests for IO: loading topology YAML files."""

from __future__ import annotations

from pathlib import Path

import pytest

from hmm_core.io import load_topology
from hmm_core.topology import TopologyError

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_valid_left_right():
    topo = load_topology(FIXTURES / "topology_valid_gaussian.yaml")
    assert topo.name == "test_left_right_3"
    assert topo.n_states == 3
    assert topo.state_names == ["a", "b", "c"]
    assert topo.emission.type == "gaussian"
    assert topo.emission.n_features == 2
    assert topo.allowed_transitions == [
        ("a", "a"),
        ("a", "b"),
        ("b", "b"),
        ("b", "c"),
        ("c", "c"),
    ]
    assert topo.startprob == "first_state"
    assert topo.init.strategy == "uniform"
    assert topo.init.seed == 42
    assert topo.fit.n_iter == 50


def test_load_ergodic_omits_allowed_transitions():
    topo = load_topology(FIXTURES / "topology_ergodic.yaml")
    assert topo.allowed_transitions is None
    assert topo.transition_mask().all()


def test_load_runs_validate(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        """
name: bad
n_states: 3
state_names: [a, b]
emission:
  type: gaussian
  covariance_type: full
  n_features: 1
startprob: uniform
init: {strategy: uniform, seed: 0}
fit: {algorithm: baum_welch, n_iter: 10, tol: 1.0e-4}
""",
        encoding="utf-8",
    )
    with pytest.raises(TopologyError):
        load_topology(bad)


def test_load_missing_file_raises_filenotfound(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_topology(tmp_path / "nope.yaml")


def test_load_empty_file_raises_topology_error(tmp_path):
    empty = tmp_path / "empty.yaml"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(TopologyError, match="empty or not a YAML mapping"):
        load_topology(empty)


def test_load_missing_required_key_raises_topology_error(tmp_path):
    bad = tmp_path / "missing_emission.yaml"
    bad.write_text(
        """
name: bad
n_states: 2
state_names: [a, b]
startprob: uniform
init: {strategy: uniform, seed: 0}
fit: {algorithm: baum_welch, n_iter: 10, tol: 1.0e-4}
""",
        encoding="utf-8",
    )
    with pytest.raises(TopologyError, match="missing required field"):
        load_topology(bad)


def test_load_parses_tol_as_float():
    topo = load_topology(FIXTURES / "topology_valid_gaussian.yaml")
    assert topo.fit.tol == pytest.approx(1e-4)
