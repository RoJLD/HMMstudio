"""Tests for the model-graph export surface (export_model_graph / export_activations)."""

from __future__ import annotations

import json
import re

import pytest

from hmm_core.export_graph import (
    export_activations,
    export_model_graph,
    save_model_graph,
)
from hmm_core.fit import fit
from hmm_core.topology import (
    EmissionSpec,
    FitSpec,
    InitSpec,
    Topology,
)


def _gaussian_topo() -> Topology:
    """K=3 left-right Gaussian topology (mirrors test_io_model._topo)."""
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


def _multinomial_topo() -> Topology:
    """K=3 left-right multinomial topology, 5 symbols."""
    return Topology(
        name="mn3",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=EmissionSpec(type="multinomial", n_symbols=5),
        allowed_transitions=[("a", "a"), ("a", "b"), ("b", "b"), ("b", "c"), ("c", "c")],
        startprob="first_state",
        init=InitSpec(strategy="uniform", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=30, tol=1e-4),
    )


def test_export_model_graph_gaussian(synthetic_gaussian_left_right):
    fitted = fit(_gaussian_topo(), synthetic_gaussian_left_right["X"])
    graph = export_model_graph(fitted, name="t")

    assert graph["model"]["name"] == "t"
    assert graph["model"]["framework"] == "hmm"

    state_nodes = [n for n in graph["nodes"] if n["type"] == "state"]
    assert len(state_nodes) == 3
    assert {n["id"] for n in state_nodes} == {"a", "b", "c"}

    # Continuous emission => no observation nodes.
    assert all(n["type"] != "observation" for n in graph["nodes"])

    transition_edges = [e for e in graph["edges"] if e["kind"] == "transition"]
    assert len(transition_edges) > 0
    for e in transition_edges:
        assert 0.0 < e["weight"] <= 1.0
        assert e["from"] in {"a", "b", "c"}
        assert e["to"] in {"a", "b", "c"}

    # No emission edges for continuous.
    assert all(e["kind"] != "emission" for e in graph["edges"])


def test_export_model_graph_multinomial(synthetic_multinomial_3state):
    fitted = fit(_multinomial_topo(), synthetic_multinomial_3state["X"])
    graph = export_model_graph(fitted)

    assert graph["model"]["name"] == "mn3"
    assert graph["model"]["framework"] == "hmm"

    obs_nodes = [n for n in graph["nodes"] if n["type"] == "observation"]
    assert len(obs_nodes) == 5
    assert {n["id"] for n in obs_nodes} == {f"obs_{k}" for k in range(5)}

    emission_edges = [e for e in graph["edges"] if e["kind"] == "emission"]
    assert len(emission_edges) > 0
    for e in emission_edges:
        assert 0.0 < e["weight"] <= 1.0
        assert e["from"] in {"a", "b", "c"}
        assert e["to"].startswith("obs_")


def test_export_activations(synthetic_gaussian_left_right):
    X = synthetic_gaussian_left_right["X"]
    fitted = fit(_gaussian_topo(), X)
    acts = export_activations(fitted, X)

    assert set(acts["nodes"].keys()) == {"a", "b", "c"}
    assert sum(acts["nodes"].values()) == pytest.approx(1.0, rel=1e-6)
    assert acts["run"]["n_samples"] == len(X)

    pattern = re.compile(r"^.+->transition->.+$")
    assert len(acts["edges"]) > 0
    for key, val in acts["edges"].items():
        assert pattern.match(key)
        assert isinstance(val, int)
        assert val > 0

    # Single sequence: total transitions == T - 1.
    assert sum(acts["edges"].values()) == len(X) - 1


def test_export_is_json_serializable(synthetic_gaussian_left_right):
    X = synthetic_gaussian_left_right["X"]
    fitted = fit(_gaussian_topo(), X)
    # Should not raise.
    json.dumps(export_model_graph(fitted))
    json.dumps(export_activations(fitted, X))


def test_export_rejects_non_fitted():
    with pytest.raises(TypeError):
        export_model_graph(object())


def test_save_model_graph_writes_files(tmp_path, synthetic_gaussian_left_right):
    X = synthetic_gaussian_left_right["X"]
    fitted = fit(_gaussian_topo(), X)
    save_model_graph(fitted, tmp_path, X=X)
    assert (tmp_path / "model-graph.json").exists()
    assert (tmp_path / "model-activations.json").exists()
    # Files are valid JSON.
    json.loads((tmp_path / "model-graph.json").read_text(encoding="utf-8"))
    json.loads((tmp_path / "model-activations.json").read_text(encoding="utf-8"))
